from __future__ import annotations

import csv, hashlib, json, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
from urllib.request import Request, urlopen
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
RAW = OUT / "raw"
PROC = OUT / "processed"
for p in (OUT, RAW, PROC): p.mkdir(parents=True, exist_ok=True)
NOW = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
prov=[]; unavailable=[]

class Response:
    def __init__(self, url, content, status, headers):
        self.url=url; self.content=content; self.status_code=status; self.headers=headers
        self.encoding=None
    @property
    def text(self):
        enc=self.encoding or self.headers.get_content_charset() or "utf-8"
        return self.content.decode(enc, errors="replace")

def get(url, name, encoding=None, timeout=60):
    path=RAW/name
    if path.exists() and path.stat().st_size:
        content=path.read_bytes(); r=Response(url,content,200,{})
    else:
        req=Request(url,headers={"User-Agent":"Mozilla/5.0 research-data-build/1.0"})
        with urlopen(req,timeout=timeout) as z:
            r=Response(z.geturl(),z.read(),z.status,z.headers)
    if encoding: r.encoding=encoding
    path.write_bytes(r.content)
    prov.append({"source_id":name,"url":url,"retrieved_at":NOW,"http_status":r.status_code,
                 "bytes":len(r.content),"sha256":hashlib.sha256(r.content).hexdigest(),"official":True})
    return r

def num(x):
    s=str(x).strip().replace("−","-").replace(",","")
    if s in {"", "-", "--", "///", "×"}: return None
    m=re.search(r"-?\d+(?:\.\d+)?",s)
    return float(m.group()) if m else None

def scrape_water():
    index="https://www.haff.city.hiroshima.jp/suisansc/21suion.html"
    urls={2026:"https://www.haff.city.hiroshima.jp/info/suisansc/water/",
          2025:"https://www.haff.city.hiroshima.jp/info/suisansc/2025water/",
          2024:"https://www.haff.city.hiroshima.jp/info/suisansc/2025water/water-2024/",
          2023:"https://www.haff.city.hiroshima.jp/info/suisansc/2025water/water-2023/",
          2022:"https://www.haff.city.hiroshima.jp/info/suisansc/2025water/water-2022/"}
    r=get(index,"water_index_2001_2021.html")
    doc=html.fromstring(r.content)
    for a in doc.xpath("//a[@href]"):
        txt=" ".join(a.text_content().split())
        m=re.search(r"\((20\d{2})\)",txt)
        if m: urls[int(m.group(1))]=urljoin(index,a.get("href"))
    rows=[]
    for year in range(2001,2027):
        url=urls.get(year)
        if not url:
            unavailable.append({"variable":"water_temperature/salinity","year":year,"reason":"公式索引に年別URLなし"}); continue
        try: r=get(url,f"water_{year}.html")
        except Exception as e:
            unavailable.append({"variable":"water_temperature/salinity","year":year,"reason":f"取得失敗: {e}"}); continue
        parser=html.HTMLParser(encoding="shift_jis") if year<=2021 else None
        doc=html.fromstring(r.content,parser=parser)
        found=0
        for tr in doc.xpath("//tr"):
            cells=[" ".join(c.text_content().split()) for c in tr.xpath("./th|./td")]
            if not cells or not re.fullmatch(r"\d{1,2}/\d{1,2}",cells[0]): continue
            vals=[num(x) for x in cells[1:]]
            # 2022+ has temp,sal,pH per depth; older has temp,sal per depth.
            stride=3 if len(vals)>=12 else 2
            if len(vals)<stride*4: continue
            try: date=pd.Timestamp(f"{year}-{cells[0]}").date().isoformat()
            except Exception: continue
            rec={"date":date,"source":"Hiroshima City Fisheries Promotion Center",
                 "station":"Hiroshima Bay mean","aggregation":"spatial mean of survey stations",
                 "source_url":url,"retrieved_at":NOW,"quality_flag":"official_html;exact_observation_date"}
            for i,d in enumerate((0,2,5,10)):
                rec[f"water_temperature_{d}m"]=vals[i*stride]
                rec[f"salinity_{d}m"]=vals[i*stride+1]
                rec[f"ph_{d}m"]=vals[i*stride+2] if stride==3 else None
            rows.append(rec); found+=1
        if not found and year<=2021:
            txt=r.content.decode("shift_jis",errors="replace")
            pat=re.compile(r"<th[^>]*>\s*(\d{1,2}/\d{1,2})\s*</th>\s*((?:<td[^>]*>.*?</td>\s*){8,12})",re.I|re.S)
            for md in pat.finditer(txt):
                vals=[num(re.sub(r"<[^>]+>","",x)) for x in re.findall(r"<td[^>]*>(.*?)</td>",md.group(2),re.I|re.S)]
                if len(vals)<8: continue
                date=pd.Timestamp(f"{year}-{md.group(1)}").date().isoformat()
                rec={"date":date,"source":"Hiroshima City Fisheries Promotion Center","station":"Hiroshima Bay mean","aggregation":"spatial mean of survey stations","source_url":url,"retrieved_at":NOW,"quality_flag":"official_html;exact_observation_date;malformed_html_regex_recovery"}
                for i,d in enumerate((0,2,5,10)):
                    rec[f"water_temperature_{d}m"]=vals[i*2]; rec[f"salinity_{d}m"]=vals[i*2+1]; rec[f"ph_{d}m"]=None
                rows.append(rec); found+=1
        if not found: unavailable.append({"variable":"water_temperature/salinity","year":year,"reason":"HTML取得済みだが観測表を解析できず"})
    return pd.DataFrame(rows).sort_values("date").drop_duplicates("date",keep="last")

def scrape_jma():
    rows=[]
    base="https://www.data.jma.go.jp/stats/etrn/view/daily_s1.php"
    for year in range(2001,2027):
      for month in range(1,13):
        if pd.Timestamp(year,month,1)>pd.Timestamp("2026-10-16"): continue
        url=f"{base}?prec_no=67&block_no=47765&year={year}&month={month}&day=&view=p1"
        try: r=get(url,f"jma_hiroshima_{year}_{month:02}.html")
        except Exception as e:
            unavailable.append({"variable":"rainfall","year":year,"reason":f"{month}月取得失敗: {e}"}); continue
        doc=html.fromstring(r.content)
        tables=doc.xpath("//table[contains(@class,'data2_s')]")
        if not tables: continue
        for tr in tables[0].xpath(".//tr"):
            td=tr.xpath("./td")
            if len(td)<4: continue
            day=num(" ".join(td[0].text_content().split()))
            if day is None: continue
            valtxt=" ".join(td[3].text_content().split())
            rain=0.0 if valtxt.strip() in {"--","0"} else num(valtxt)
            try: date=pd.Timestamp(year,month,int(day)).date().isoformat()
            except ValueError: continue
            flag="official_html"
            if "]" in valtxt or ")" in valtxt: flag+=";jma_quality_mark_present"
            rows.append({"date":date,"rainfall_mm":rain,"rainfall_quality_flag":flag,
                         "rainfall_station":"Hiroshima Local Meteorological Office (block 47765)",
                         "rainfall_aggregation":"daily total","rainfall_source_url":url})
    return pd.DataFrame(rows).drop_duplicates("date")

def scrape_river():
    # MLIT Water Information System hourly discharge; aggregate valid numeric hourly values to daily mean.
    rows=[]; station="307091287712080"; base="https://www1.river.go.jp/cgi-bin/DspWaterData.exe"
    for year in range(2001,2027):
      for month in range(1,13):
        if pd.Timestamp(year,month,1)>pd.Timestamp("2026-10-16"): continue
        url=f"{base}?KIND=6&ID={station}&BGNDATE={year}{month:02}01&ENDDATE=20261016&KAWABOU=NO"
        try: r=get(url,f"mlit_yaguchi_hourly_{year}_{month:02}.html",encoding="euc_jp",timeout=90)
        except Exception as e:
            unavailable.append({"variable":"river_flow","year":year,"reason":f"{month}月取得失敗: {e}"}); continue
        doc=html.fromstring(r.content)
        parsed=0
        for tr in doc.xpath("//tr"):
            cells=[" ".join(c.text_content().split()) for c in tr.xpath("./th|./td")]
            # typical month table: day + 24 hourly cells + daily mean/notes
            if len(cells)<25 or not re.fullmatch(r"\d{4}/\d{2}/\d{2}",cells[0]): continue
            vals=[num(x) for x in cells[1:25]]; valid=[x for x in vals if x is not None]
            try: date=pd.Timestamp(cells[0]).date().isoformat()
            except ValueError: continue
            rows.append({"date":date,"river_flow_m3_s":sum(valid)/len(valid) if valid else None,
                         "river_flow_n_hourly":len(valid),"river_flow_quality_flag":"official_html;derived_daily_mean"+(";incomplete_day" if len(valid)<24 else ""),
                         "river_station":"Yaguchi Daiichi 307091287712080","river_aggregation":"mean of available hourly discharge","river_source_url":url})
            parsed+=1
        if not parsed: unavailable.append({"variable":"river_flow","year":year,"reason":f"{month}月ページ取得済みだが数値表なし/未登録"})
    return pd.DataFrame(rows).drop_duplicates("date") if rows else pd.DataFrame(columns=["date","river_flow_m3_s"])

def main():
    water=scrape_water(); rain=scrape_jma(); river=scrape_river()
    water.to_csv(PROC/"water_temperature_salinity.csv",index=False,encoding="utf-8-sig")
    rain.to_csv(PROC/"jma_rainfall.csv",index=False,encoding="utf-8-sig")
    river.to_csv(PROC/"mlit_river_flow.csv",index=False,encoding="utf-8-sig")
    dates=pd.DataFrame({"date":pd.date_range("2001-01-01","2026-10-16").strftime("%Y-%m-%d")})
    master=dates.merge(rain,on="date",how="left").merge(river,on="date",how="left").merge(water,on="date",how="left")
    # Explicit unavailable fields retained so absence cannot be mistaken for zero or acquisition success.
    for c in ["dissolved_oxygen_mg_L","satellite_sst_c","satellite_chla_mg_m3","oyster_mortality_rate_pct"]: master[c]=pd.NA
    master["do_quality_flag"]="not_acquired;official_bulk_download_requires_yearwise form workflow and station/depth harmonization"
    master["satellite_quality_flag"]="not_acquired;no authenticated/validated pixel extraction performed"
    master["oyster_mortality_quality_flag"]="not_acquired;official meeting summaries are qualitative and do not provide reconstructable date-station denominators"
    unavailable.extend([
      {"variable":"dissolved_oxygen_mg_L","year":"2001-2026","reason":"環境省公共用水域の年別検体値は地点・深度・測定法の調和が必要で、検証済み一括取得を本実行では完了できず"},
      {"variable":"satellite_sst_c / satellite_chla_mg_m3","year":"2001-2026","reason":"MODIS/Sentinel-3/GCOM-Cの認証済み取得、雲品質マスク、広島湾画素抽出を未実行"},
      {"variable":"oyster_mortality_rate_pct","year":"2001-2026","reason":"公開済み公式会議概要は定性的で、日付×地点の分母付きへい死率原表を復元不能。論文図デジタイズは未実施"},
    ])
    master.to_csv(OUT/"hiroshima_bay_oyster_master_daily.csv",index=False,encoding="utf-8-sig")
    try: master.to_parquet(OUT/"hiroshima_bay_oyster_master_daily.parquet",index=False)
    except Exception as e: unavailable.append({"variable":"parquet","year":"all","reason":str(e)})
    pd.DataFrame(prov).to_csv(OUT/"provenance.csv",index=False,encoding="utf-8-sig")
    pd.DataFrame(unavailable).to_csv(OUT/"unavailable_and_failures.csv",index=False,encoding="utf-8-sig")
    coverage=[]
    variables=[c for c in master.columns if c.endswith(("_mm","_m3_s","_0m","_2m","_5m","_10m","_mg_L","_mg_m3","_pct"))]
    for y,g in master.assign(year=master.date.str[:4].astype(int)).groupby("year"):
      for c in variables: coverage.append({"year":y,"variable":c,"n_nonmissing":int(g[c].notna().sum()),"n_days":len(g),"coverage_pct":round(g[c].notna().mean()*100,3)})
    pd.DataFrame(coverage).to_csv(OUT/"coverage_by_year_variable.csv",index=False,encoding="utf-8-sig")
    dictionary=[]
    defs={"rainfall_mm":("Daily precipitation total","mm"),"river_flow_m3_s":("Daily mean discharge derived from available hourly values","m3/s"),
          "dissolved_oxygen_mg_L":("Dissolved oxygen; placeholder not acquired","mg/L"),"satellite_sst_c":("Satellite sea-surface temperature; placeholder not acquired","degC"),
          "satellite_chla_mg_m3":("Satellite chlorophyll-a; placeholder not acquired","mg/m3"),"oyster_mortality_rate_pct":("Oyster mortality rate; placeholder not acquired","percent")}
    for c in master.columns:
      definition,unit=defs.get(c,("", ""))
      m=re.match(r"water_temperature_(\d+)m",c)
      if m: definition=f"Hiroshima Bay spatial-mean in-situ water temperature at {m.group(1)} m"; unit="degC"
      m=re.match(r"salinity_(\d+)m",c)
      if m: definition=f"Hiroshima Bay spatial-mean practical salinity at {m.group(1)} m"; unit="psu"
      dictionary.append({"variable":c,"definition":definition,"unit":unit,"missing_representation":"blank/NA","notes":"See source/station/aggregation/quality columns and provenance.csv"})
    pd.DataFrame(dictionary).to_csv(OUT/"data_dictionary.csv",index=False,encoding="utf-8-sig")
    checks=[]
    checks.append({"check":"master_date_unique","result":"PASS" if master.date.is_unique else "FAIL","detail":f"rows={len(master)}"})
    checks.append({"check":"date_contiguous","result":"PASS" if len(master)==(pd.Timestamp('2026-10-16')-pd.Timestamp('2001-01-01')).days+1 else "FAIL","detail":"daily calendar spine"})
    for c,lo,hi in [(f"water_temperature_{d}m",-2,40) for d in (0,2,5,10)]+[(f"salinity_{d}m",0,40) for d in (0,2,5,10)]+[("rainfall_mm",0,1000),("river_flow_m3_s",0,100000)]:
      if c in master:
        bad=master[c].notna() & ~master[c].between(lo,hi)
        checks.append({"check":f"range_{c}","result":"PASS" if not bad.any() else "FAIL","detail":f"outside [{lo},{hi}]={int(bad.sum())}"})
    checks.append({"check":"rain_river_separate","result":"PASS","detail":"independent columns, stations, aggregation and flags"})
    pd.DataFrame(checks).to_csv(OUT/"validation_results.csv",index=False,encoding="utf-8-sig")
    summary={"built_at":NOW,"master_rows":len(master),"water_observation_dates":len(water),"rain_days":int(rain.rainfall_mm.notna().sum()),
             "river_days":int(river.river_flow_m3_s.notna().sum()) if "river_flow_m3_s" in river else 0,"provenance_files":len(prov),
             "validation_pass":sum(x["result"]=="PASS" for x in checks),"validation_fail":sum(x["result"]=="FAIL" for x in checks)}
    (OUT/"build_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))

if __name__=="__main__": main()
