"""產生 public/index.html：把里級資料與地圖路徑內嵌進 analysis/page_template.html。
輸入：analysis/output/taipei_li_full.json（456 里）、analysis/output/map_paths.json（build_map.js 產出）
用法：python3 analysis/build_page.py
"""
import json
from pathlib import Path

A = Path(__file__).parent
li = json.loads((A / "output" / "taipei_li_full.json").read_text(encoding="utf-8"))
mp = json.loads((A / "output" / "map_paths.json").read_text(encoding="utf-8"))
assert len(li) == 456, len(li)
assert sum(len(v) for v in mp["villages"].values()) == 456
tpl = (A / "page_template.html").read_text(encoding="utf-8")
dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))
html = tpl.replace("/*__LI__*/null", dump(li), 1).replace("/*__MAP__*/null", dump(mp), 1)
assert "__LI__" not in html and "__MAP__" not in html
(A.parent / "public" / "index.html").write_text(html, encoding="utf-8")
print("public/index.html", len(html.encode()), "bytes")
