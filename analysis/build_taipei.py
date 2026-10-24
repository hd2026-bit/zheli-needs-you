"""把臺北市開放資料整理成「這里需要你」的里級資料（一里一列）。
輸入：各里年齡人口（110、112 年 12 月）、村里界圖、以及 silver-safe-walk/analysis 產出的
      樹蔭（li_metrics.gpkg）、長者行人事故路口（elder_hotspots.csv）、行人事故（ped_accidents.pkl）、捷運出入口。
輸出：output/taipei_li.json、output/taipei_li.csv
"""
import json, sys, pandas as pd, geopandas as gpd, numpy as np
from pathlib import Path
UP = Path(sys.argv[1]); SSW = Path(sys.argv[2]); OUT = Path(__file__).parent / "output"
DL = Path(__file__).parent / "data"   # data.taipei 下載：care.csv（社區照顧關懷據點）、wifi.csv（Taipei Free 熱點）、busstop/（公車站位）
POP110 = UP / "3c6cf200-110_________.csv"; POP111 = UP / "394fe257-111_________.csv"; POP112P = UP / "1e0b45e6-112___________.csv"  # 112年迄今（到 115 年 9 月）
MRT = UP / "3a8ea18a-____________1150804.csv"
DIST = {"63000010":"松山區","63000020":"信義區","63000030":"大安區","63000040":"中山區","63000050":"中正區","63000060":"大同區",
        "63000070":"萬華區","63000080":"文山區","63000090":"南港區","63000100":"內湖區","63000110":"士林區","63000120":"北投區"}

RAW = {}
def pop(path, year, month="12"):
    if path not in RAW: RAW[path] = pd.read_csv(path, encoding="cp950", dtype=str)
    d = RAW[path]
    d = d[(d["年份"] == str(year)) & (d["月份"] == month) & (d["性別"] == "計") & (d["區域代碼"].str.len() == 11)].drop_duplicates("區域代碼")
    ages = [c for c in d.columns if c.endswith("歲數量")] + ["100歲以上"]
    n = d[ages + ["總計"]].apply(lambda s: pd.to_numeric(s.str.replace(",", ""), errors="coerce"))
    a = lambda c: 100 if c == "100歲以上" else int(c.replace("歲數量", ""))
    S = lambda f: n[[c for c in ages if f(a(c))]].sum(axis=1)
    return pd.DataFrame({"code": d["區域代碼"], "d": d["區域代碼"].str[:8].map(DIST), "v": d["區域別"], "pop": n["總計"],
        "a014": S(lambda x: x <= 14), "a1564": S(lambda x: 15 <= x <= 64), "e65": S(lambda x: x >= 65),
        "e6574": S(lambda x: 65 <= x <= 74), "e80": S(lambda x: x >= 80)})

NOW = pop(POP112P, 115, "9")
p10 = pop(POP110, 110)
li = NOW.merge(p10[["d", "v", "pop", "e65"]].rename(columns={"pop": "pop20", "e65": "e65_20"}), on=["d", "v"], how="left")
# 65 歲以上趨勢：110–114 年 12 月＋115 年 9 月
SER = [(POP110, 110, "12"), (POP111, 111, "12"), (POP112P, 112, "12"), (POP112P, 113, "12"), (POP112P, 114, "12"), (POP112P, 115, "9")]
for f, y, mo in SER:
    li = li.merge(pop(f, y, mo)[["d", "v", "e65"]].rename(columns={"e65": f"t{y}"}), on=["d", "v"], how="left")

m = gpd.read_file(SSW / "li_metrics.gpkg")
m = m[["區", "里", "area_km2", "cover", "swL", "eld", "geometry"]].rename(columns={"區": "d", "里": "v"})
li = li.merge(m.drop(columns="geometry"), on=["d", "v"], how="left")
li["area"] = li.area_km2.round(3)
li["shade"] = np.where(li.swL >= 500, ((1 - li.cover) * 100).round(1), np.nan)  # 人行道 < 500 m 的里不計
# 2023–2025 三年長者行人事故（每里）
pa = pd.read_pickle(SSW / "ped_accidents.pkl")
pa = pa[pa.old & pa["發生年度"].isin(["2023", "2024", "2025"])]
pg = gpd.GeoDataFrame(pa[["old"]], geometry=gpd.points_from_xy(pa.lon, pa.lat), crs=4326).to_crs(3826)
mj0 = gpd.sjoin(pg, m.to_crs(3826)[["d", "v", "geometry"]].rename(columns={"d": "dd", "v": "vv"}), predicate="within").groupby(["dd", "vv"]).size()
li["acc"] = [int(mj0.get((a, b), 0)) for a, b in zip(li.d, li.v)]

# 危險路口（長者行人事故 76 m 內 ≥2 件）落在哪個里
mg = m.to_crs(3826)
h = pd.read_csv(SSW / "elder_hotspots.csv")
hg = gpd.GeoDataFrame(h, geometry=gpd.points_from_xy(h.lon, h.lat), crs=4326).to_crs(3826)
hj = gpd.sjoin(hg, mg[["d", "v", "geometry"]].rename(columns={"d": "dd", "v": "vv"}), predicate="within")
hot = hj.groupby(["dd", "vv"]).apply(lambda g: [[r.路口, "危險路口（三年 ≥5 件）" if r.n >= 5 else "觀察路口（三年 3–4 件）", int(r.n)] for r in g.sort_values("n", ascending=False).itertuples()])
li["hot"] = [hot.get((a, b), []) for a, b in zip(li.d, li.v)]

# 500 m 內捷運出入口（以里的代表點計）
t = pd.read_csv(MRT, dtype=str, encoding="cp950")
t["lon"], t["lat"] = pd.to_numeric(t["經度"], errors="coerce"), pd.to_numeric(t["緯度"], errors="coerce")
tg = gpd.GeoDataFrame(t.dropna(subset=["lon", "lat"]), geometry=gpd.points_from_xy(t.dropna(subset=["lon","lat"]).lon, t.dropna(subset=["lon","lat"]).lat), crs=4326).to_crs(3826)
c = mg.copy(); c["geometry"] = c.representative_point().buffer(500)
mj = gpd.sjoin(tg, c[["d", "v", "geometry"]].rename(columns={"d": "dd", "v": "vv"}), predicate="within").groupby(["dd", "vv"]).size()
li["bus"] = [int(mj.get((a, b), 0)) for a, b in zip(li.d, li.v)]

TC = [f"t{y}" for _, y, _ in SER]
# 關懷據點：地址含里名（510 處中 501 處），依區＋里計數
cr = pd.read_csv(DL / "care.csv", encoding="utf-8-sig")
cm = cr["地址"].str.extract(r"臺北市(..區)(.{1,3}?里)")
cc = cm.dropna().value_counts()
li["careN"] = [int(cc.get((a, b), 0)) for a, b in zip(li.d, li.v)]
# Taipei Free 熱點：落在里界內
wf = pd.read_csv(DL / "wifi.csv", encoding="utf-8-sig")
wf = wf.dropna(subset=["LATITUDE", "LONGITUDE"])
wg = gpd.GeoDataFrame(wf[["SITE_ID"]], geometry=gpd.points_from_xy(wf.LONGITUDE, wf.LATITUDE), crs=4326).to_crs(3826)
wj = gpd.sjoin(wg, mg[["d", "v", "geometry"]].rename(columns={"d": "dd", "v": "vv"}), predicate="within").groupby(["dd", "vv"]).size()
li["wifi"] = [int(wj.get((a, b), 0)) for a, b in zip(li.d, li.v)]
# 公車站位：里代表點 500 m 內，加上捷運出入口
bs = gpd.read_file(DL / "busstop" / "busstop.shp")
bs = bs.set_crs(4326, allow_override=True).to_crs(3826)
bj = gpd.sjoin(bs, c[["d", "v", "geometry"]].rename(columns={"d": "dd", "v": "vv"}), predicate="within").groupby(["dd", "vv"]).size()
li["busN"] = [int(bj.get((a, b), 0)) for a, b in zip(li.d, li.v)]
li["mrtN"] = li["bus"]
li["bus"] = li["busN"] + li["mrtN"]
li["t65"] = [None if r.isna().any() else [int(x) for x in r] for _, r in li[TC].iterrows()]
keep = ["d", "v", "pop", "a014", "a1564", "e65", "e6574", "e80", "pop20", "e65_20", "area", "acc", "bus", "busN", "mrtN", "careN", "wifi", "shade", "hot", "t65"]
out = li[keep]
rows = []
for r in out.to_dict("records"):
    rows.append({k: (None if (isinstance(v, float) and np.isnan(v)) else (int(v) if isinstance(v, (np.integer,)) or (isinstance(v, float) and k not in ("area", "shade") and float(v).is_integer()) else v)) for k, v in r.items()})
OUT.mkdir(exist_ok=True)
json.dump(rows, open(OUT / "taipei_li.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
out.drop(columns=["hot", "t65"]).to_csv(OUT / "taipei_li.csv", index=False, encoding="utf-8-sig")
print("里數", len(rows), "有樹蔭", out.shade.notna().sum(), "有面積", out.area.notna().sum(), "危險路口里", sum(1 for r in rows if r["hot"]),
      "長者行人事故合計（2023–2025）", out.acc.sum(), "關懷據點（對到里）", out.careN.sum(), "Wi-Fi 熱點", out.wifi.sum(), "公車站位（500m，含重複）", out.busN.sum(), "危險路口里", sum(1 for r in rows if any(h[2] >= 5 for h in r["hot"])), "65+", out.e65.sum(), "/", out["pop"].sum())
