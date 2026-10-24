// 產生「這里需要你」地圖路徑：臺北市 12 區、各區的里（共 456 里）
// 來源：taiwan-atlas 2021.9.20（內政部國土測繪中心村里界，1:10,000 簡化版）
// 用法：npm i taiwan-atlas@2021.9.20 topojson-client@3.1.0
//       node analysis/build_map.js <node_modules 所在資料夾> > analysis/output/map_paths.json
const path = require('path'), fs = require('fs');
const NM = path.resolve(process.argv[2] || '.');
const tj = require(path.join(NM, 'topojson-client'));
const topo = JSON.parse(fs.readFileSync(path.join(NM, 'taiwan-atlas', 'villages-10t.json')));
const TP = '63000';
const fix = s => s.replace(/^台/, '臺');

const vil = tj.feature(topo, topo.objects.villages).features.filter(f => f.properties.COUNTYCODE === TP);
const towns = tj.feature(topo, topo.objects.towns).features.filter(f => f.properties.COUNTYCODE === TP);

// 等距圓柱投影，依緯度修正經度比例，填滿 W×H
function fitter(feats, W, H, pad) {
  let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
  const each = (g, fn) => (g.type === 'Polygon' ? [g.coordinates] : g.coordinates).forEach(p => p.forEach(r => r.forEach(fn)));
  feats.forEach(f => each(f.geometry, ([x, y]) => { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }));
  const k = Math.cos(((y0 + y1) / 2) * Math.PI / 180);
  const s = Math.min((W - 2 * pad) / ((x1 - x0) * k), (H - 2 * pad) / (y1 - y0));
  const ox = (W - (x1 - x0) * k * s) / 2, oy = (H - (y1 - y0) * s) / 2;
  return ([x, y]) => [+(ox + (x - x0) * k * s).toFixed(1), +(oy + (y1 - y) * s).toFixed(1)];
}
function toPath(g, P) {
  return (g.type === 'Polygon' ? [g.coordinates] : g.coordinates).map(poly => poly.map(r => {
    const pts = r.map(P); let d = '', last = '';
    pts.forEach((p, i) => { const t = p[0] + ',' + p[1]; if (t !== last) { d += (i ? 'L' : 'M') + t; last = t; } });
    return d + 'Z';
  }).join('')).join('');
}
// 標籤位置：最大多邊形的面積加權重心
function label(g, P) {
  let best = null, ba = -1;
  (g.type === 'Polygon' ? [g.coordinates] : g.coordinates).forEach(poly => {
    const r = poly[0].map(P); let a = 0, cx = 0, cy = 0;
    for (let i = 0; i < r.length - 1; i++) { const c = r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1]; a += c; cx += (r[i][0] + r[i + 1][0]) * c; cy += (r[i][1] + r[i + 1][1]) * c; }
    if (Math.abs(a) > ba) { ba = Math.abs(a); best = [+(cx / (3 * a)).toFixed(1), +(cy / (3 * a)).toFixed(1), +(Math.abs(a) / 2).toFixed(0)]; }
  });
  return best;
}

const W = 460, H = 520;
const Pc = fitter(towns, W, H, 10);
const out = { districts: towns.map(f => { const [cx, cy] = label(f.geometry, Pc); return { key: f.properties.TOWNNAME, d: toPath(f.geometry, Pc), cx, cy }; }), villages: {} };
towns.forEach(t => {
  const name = t.properties.TOWNNAME, fs_ = vil.filter(v => v.properties.TOWNNAME === name);
  const P = fitter(fs_, 460, 560, 10);
  out.villages[name] = fs_.map(f => { const [cx, cy, a] = label(f.geometry, P); return { key: fix(f.properties.VILLNAME), code: f.properties.VILLCODE, d: toPath(f.geometry, P), cx, cy, a }; });
});
process.stdout.write(JSON.stringify(out));
