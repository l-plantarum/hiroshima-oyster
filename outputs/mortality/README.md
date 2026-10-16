# 広島湾養殖マガキへい死率データ

## 復元結果

- 広島市水産振興センターの公式業務報告書に掲載された「年度別 斃死率の推移」から、2001～2023年度の10月～翌5月を復元した（184行）。
- `season_year` は10月が属する年。たとえば `season_year=2015` は2015年10月～2016年5月を表す。
- `mortality_oct_dec_mean_pct` は同一年度の10・11・12月の公表値の単純平均。
- 日次マスターでは月次値を日次に複製せず、各月1日の行だけに結合した。完全な月次系列は別CSVを使用する。

## ファイル

- `oyster_mortality_monthly_2001_2023.csv`: 月別公式値。
- `oyster_mortality_annual_oct_dec_2001_2023.csv`: 10～12月平均。
- `oyster_mortality_event_detail_2025.csv`: 2025年の地域別聞き取りレンジ。長期系列とは非互換。
- `mortality_environment_features_2001_2023.csv`: 既存の6～10月環境特徴量との年次結合。
- `mortality_environment_correlations.csv`: 単変量の探索的相関。
- `mortality_environment_exploratory_model.csv`: 4変数探索的OLS。標本数が小さいため推論・因果解釈には使用しない。
- `mortality_validation_results.csv`: 検算。
- `mortality_provenance.csv`: URL、取得日時、保存先、SHA-256。
- `hiroshima_oyster_mortality_2001_2025.xlsx`: 閲覧用ワークブック。

## 重要な制約

- 累積表には年度別の調査業者数、分母、地点別値、深度が掲載されていない。これらを推測して補完していない。
- 2024年度について同一定義の広島市年報を確認できなかったため欠測。
- 2025年は水産庁資料の地域別聞き取りレンジであり、広島市の月別業者調査系列へ結合していない。
- 相関・OLSは特徴量生成工程の動作確認を兼ねた探索結果。水温観測は間欠的で、`obs_degree_days` は観測日の超過量合計であり連続日積算ではない。

## 再現

`work/build_mortality.py` を実行するとPDF取得、CSV生成、日次マスター結合、検算を再実行する。XLSXは `work/build_mortality_xlsx.mjs` で生成する。
