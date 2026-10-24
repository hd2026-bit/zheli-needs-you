# 這里需要你（村里高齡風險儀表板）

用五大領域（人口、安全、健康、社會參與、數位）看見每個里的高齡風險，讓里長、局處與在地團體知道「哪個里、哪個問題最急、先做什麼」。

- 指標架構：對齊國發會「超高齡社會五大領域風險評估指標」草案（36 項指標，A／B／C 三級資料）
- 頁面：`public/index.html`（單檔，可直接開啟）
- 線上版：走這條！網站網址加 `/zheli/`（同一組帳號密碼）。更新時把本專案的 `public/index.html` 複製到 silver-safe-walk 的 `public/zheli/index.html`
- 目前為示範資料；「匯入資料」頁可貼上一里一列的 CSV 替換

## 與其他專案的關係

這里需要你是**母體**：每一個看見都可以長出解方。

| 解方 | 對應看見 | 專案 |
|---|---|---|
| 走這條！求最大陰影面積 | 安全＋健康：長輩出門的高溫與事故 | [hd2026-bit/silver-safe-walk](https://github.com/hd2026-bit/silver-safe-walk) |

## 資料（臺北市開放資料）

`analysis/build_taipei.py` 產生 `analysis/output/taipei_li.json`，嵌入頁面。

| 欄位 | 來源 | 類型 |
|---|---|---|
| 總人口、各年齡層、65+、80+ | 臺北市各里年齡人口 115 年 9 月（趨勢用 110–115 年） | 計算 |
| 長者行人事故 | 2023–2025 三年（臺北市警察局 112、113 年＋警政署 114 年），只算行人、一件算一次 | 計算 |
| 危險路口 | 2023–2025 三年 76 m 內長者行人事故 ≥ 5 件＝危險、3–4 件＝觀察，落在哪個里 | 計算 |
| 人行道缺樹蔭比例 | 行道樹＋公園樹木＋人行道；樹冠寬推估 8 m | 計算＋推估 |
| 500 m 內公車站與捷運出入口 | 臺北市公車站牌位置圖＋捷運出入口座標 × 里代表點 | 計算 |
| 社區照顧關懷據點 | 社會局（data.taipei），依地址里名對到里（510 處中 496 處） | 計算 |
| Taipei Free 熱點 | 資訊局（data.taipei），座標落在哪個里 | 計算 |
| 其他（獨居、低收、健檢、志工…） | 機關資料 | 待提供，頁面顯示「待提供」、不計分 |

## 部署（Cloudflare Workers）
- 獨立網址：`https://zheli-needs-you.<子網域>.workers.dev`，頁尾「走這條！」自動連到同一子網域的 `silver-safe-walk`
- Cloudflare：Workers & Pages → Create → Import a repository → 選本 repo → Deploy
- 帳密：Settings → Variables and Secrets 新增 Secret `DEMO_USER`、`DEMO_PASS`（未設定時一律拒絕）
