#!/usr/bin/env python3
"""Fetch daily institutional data from official TWSE/TPEx endpoints.
Writes data/institutional_data.json only when at least one market succeeds.
No synthetic stock records are generated.
"""
import json, os, re, sys, time
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
import requests

OUT=Path("data/institutional_data.json")
TWSE="https://www.twse.com.tw/rwd/zh/fund/T86"
TPEX="https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade"
HEADERS={"User-Agent":"Mozilla/5.0 (compatible; TWInstitutionalPages/1.0)","Accept":"application/json,text/plain,*/*"}
def norm(s): return re.sub(r"\s+","",str(s or ""))
def idx(fields,*names):
    fs=[norm(x) for x in fields]
    for n in names:
        for i,f in enumerate(fs):
            if norm(n) == f or norm(n) in f: return i
    return None
def val(row,fields,*names,default=0):
    i=idx(fields,*names)
    return default if i is None or i>=len(row) else row[i]
def integer(v):
    s=str(v if v is not None else "").strip().replace(",","").replace(" ","")
    if s in ("","--","-","－","N/A","nan"): return 0
    return int(float(s))
def twse(day):
    r=requests.get(TWSE,params={"response":"json","date":day.replace("-",""),"selectType":"ALL"},headers=HEADERS,timeout=35);r.raise_for_status()
    p=r.json(); fields=p.get("fields") or []; rows=p.get("data") or []
    if not fields or not rows: raise RuntimeError("TWSE 沒有資料或尚未發布："+str(p.get("stat","empty")))
    for n in ("證券代號","證券名稱","投信買進股數","投信賣出股數"):
        if idx(fields,n) is None: raise RuntimeError("TWSE 欄位缺失："+n)
    out=[]
    for row in rows:
        code=str(val(row,fields,"證券代號",default="")).strip()
        if not code: continue
        fb=integer(val(row,fields,"外陸資買進股數(不含外資自營商)","外陸資買進股數"))
        fs=integer(val(row,fields,"外陸資賣出股數(不含外資自營商)","外陸資賣出股數"))
        fnet=integer(val(row,fields,"外陸資買賣超股數(不含外資自營商)","外陸資買賣超股數",default=fb-fs))
        fdb=integer(val(row,fields,"外資自營商買進股數")); fds=integer(val(row,fields,"外資自營商賣出股數"))
        fdnet=integer(val(row,fields,"外資自營商買賣超股數",default=fdb-fds))
        tb=integer(val(row,fields,"投信買進股數")); ts=integer(val(row,fields,"投信賣出股數"))
        db=integer(val(row,fields,"自營商買進股數(自行買賣)"))+integer(val(row,fields,"自營商買進股數(避險)"))
        ds=integer(val(row,fields,"自營商賣出股數(自行買賣)"))+integer(val(row,fields,"自營商賣出股數(避險)"))
        dn=integer(val(row,fields,"自營商買賣超股數",default=db-ds))
        total=integer(val(row,fields,"三大法人買賣超股數",default=fnet+tb-ts+dn))
        out.append(dict(trade_date=day,market="上市",code=code,name=str(val(row,fields,"證券名稱",default="")).strip(),foreign_buy=fb,foreign_sell=fs,foreign_net=fnet,foreign_dealer_buy=fdb,foreign_dealer_sell=fds,foreign_dealer_net=fdnet,trust_buy=tb,trust_sell=ts,trust_net=tb-ts,dealer_buy=db,dealer_sell=ds,dealer_net=dn,total_net=total,source="TWSE"))
    return out
def tpex(day):
    r=requests.get(TPEX,params={"date":day.replace("-","/"),"id":"","response":"json"},headers=HEADERS,timeout=35);r.raise_for_status()
    p=r.json(); tables=p.get("tables") or []; fields=p.get("fields") or []; rows=p.get("data") or []
    if tables:
        t=next((t for t in tables if t.get("fields") and t.get("data")),None)
        if t: fields,rows=t["fields"],t["data"]
    if not fields or not rows: raise RuntimeError("TPEx 沒有資料或尚未發布："+str(p.get("message") or p.get("stat") or "empty"))
    for n in ("證券代號","證券名稱"):
        if idx(fields,n) is None: raise RuntimeError("TPEx 欄位缺失："+n)
    out=[]
    for row in rows:
        code=str(val(row,fields,"證券代號",default="")).strip()
        if not code: continue
        fb=integer(val(row,fields,"外資及陸資買進股數","外陸資買進股數(不含自營商)","外陸資買進股數"))
        fs=integer(val(row,fields,"外資及陸資賣出股數","外陸資賣出股數(不含自營商)","外陸資賣出股數"))
        fn=integer(val(row,fields,"外資及陸資買賣超股數","外陸資買賣超股數(不含自營商)","外陸資買賣超股數",default=fb-fs))
        fdb=integer(val(row,fields,"外資自營商買進股數")); fds=integer(val(row,fields,"外資自營商賣出股數"))
        fdn=integer(val(row,fields,"外資自營商買賣超股數",default=fdb-fds))
        tb=integer(val(row,fields,"投信買進股數")); ts=integer(val(row,fields,"投信賣出股數"))
        db=integer(val(row,fields,"自營商買進股數","自營商買進股數合計",default=0))
        ds=integer(val(row,fields,"自營商賣出股數","自營商賣出股數合計",default=0))
        dn=integer(val(row,fields,"自營商買賣超股數","自營商買賣超股數合計",default=db-ds))
        # A net-only field cannot reveal actual buy and sell volume. Keep both at zero rather than fabricate.
        if idx(fields,"自營商買進股數") is None: db=ds=0
        total=integer(val(row,fields,"三大法人買賣超股數合計","三大法人買賣超股數",default=fn+tb-ts+dn))
        out.append(dict(trade_date=day,market="上櫃",code=code,name=str(val(row,fields,"證券名稱",default="")).strip(),foreign_buy=fb,foreign_sell=fs,foreign_net=fn,foreign_dealer_buy=fdb,foreign_dealer_sell=fds,foreign_dealer_net=fdn,trust_buy=tb,trust_sell=ts,trust_net=tb-ts,dealer_buy=db,dealer_sell=ds,dealer_net=dn,total_net=total,source="TPEx"))
    return out
def main():
    requested=os.getenv("TRADE_DATE","").strip()
    days=[requested] if requested else [(date.today()-timedelta(days=i)).isoformat() for i in range(0,11)]
    errors=[]
    for day in days:
        records=[]; success=[]
        for market,fn in (("上市",twse),("上櫃",tpex)):
            try:
                got=fn(day)
                records.extend(got); success.append(market)
                print(f"{market} {day}: {len(got)} rows")
            except Exception as e:
                errors.append(f"{market} {day}: {e}"); print(errors[-1],file=sys.stderr)
        # On a regular scheduled run, use the most recent date with both markets.
        if len(success)==2 and records:
            OUT.parent.mkdir(parents=True,exist_ok=True)
            data={"updated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),"trade_date":day,"markets":success,"records":records,"message":"官方資料抓取成功"}
            OUT.write_text(json.dumps(data,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
            print(f"Saved {len(records)} records for {day} to {OUT}")
            return
        if requested: break
        time.sleep(1)
    if errors: print("\n".join(errors),file=sys.stderr)
    raise SystemExit("無法取得同一交易日的上市及上櫃資料；不更新資料檔，以免以不完整資料覆蓋。")
if __name__=="__main__": main()
