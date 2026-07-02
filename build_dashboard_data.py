#!/usr/bin/env python3
"""
build_dashboard_data.py  ->  data.json  for the HELIX dashboard
---------------------------------------------------------------
Reads tickers.csv (symbol[,company][,region]) and writes data.json next to
index.html. Reload the page and HELIX switches from DEMO to your live snapshot:
prices, full history (for the charts), fundamentals, and news.

  pip install yfinance pandas
  python build_dashboard_data.py

Notes
  * History closes are converted to USD (so a global list is comparable);
    market cap / EV / cash / debt / revenue are USD-normalized via spot FX.
  * Re-run on a schedule (cron / Task Scheduler) to refresh the snapshot.
"""
import csv, json, os, datetime as dt
import pandas as pd, yfinance as yf

TICKERS = "tickers.csv"
OUT     = "data.json"
YEARS   = "6y"        # history depth (covers 5Y / MAX buttons)

def load():
    rows=[]
    with open(TICKERS) as f:
        for r in csv.DictReader(f):
            s=(r.get("symbol") or "").strip()
            if s: rows.append((s, (r.get("company") or s).strip(), (r.get("region") or "US").strip()))
    return rows

def fx_rates(curs):
    rates={"USD":1.0,"":1.0,None:1.0}
    for c in {x for x in curs if x and x!="USD"}:
        base="GBP" if c in ("GBp","GBX") else c
        try:
            r=yf.Ticker(f"{base}USD=X").fast_info.last_price
            rates[c]=(r/100.0) if c in ("GBp","GBX") else r
        except Exception:
            rates[c]=None
    return rates

def xbi_constituents():
    """Authoritative current XBI membership from State Street's daily holdings file."""
    import io, urllib.request
    url = "https://www.ssga.com/library-content/products/fund-data/etfs/us/holdings-daily-us-en-xbi.xlsx"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=30).read()
        head = pd.read_excel(io.BytesIO(raw), header=None, engine="openpyxl")
        hdr = None
        for i in range(min(25, len(head))):
            vals = [str(x).strip().lower() for x in head.iloc[i].tolist()]
            if "ticker" in vals:
                hdr = i; break
        if hdr is None:
            print("XBI: header row not found"); return set()
        df = pd.read_excel(io.BytesIO(raw), header=hdr, engine="openpyxl")
        col = [c for c in df.columns if str(c).strip().lower() == "ticker"][0]
        out = set()
        for t in df[col].dropna().tolist():
            t = str(t).strip().upper()
            if t and t.replace(".", "").replace("-", "").isalnum() and t not in ("CASH", "USD", "-"):
                out.add(t)
        print(f"XBI constituents fetched: {len(out)}")
        return out
    except Exception as e:
        print("XBI fetch failed (asterisks will be empty this run):", e)
        return set()

def rel(ts):
    try:
        d=dt.datetime.utcfromtimestamp(ts); s=(dt.datetime.utcnow()-d).total_seconds()
        if s<3600:   return f"{int(s//60)}m ago"
        if s<86400:  return f"{int(s//3600)}h ago"
        return f"{int(s//86400)}d ago"
    except Exception: return ""

def main():
    uni=load(); syms=[s for s,_,_ in uni]
    print(f"Downloading {YEARS} history for {len(syms)} symbols ...")
    data=yf.download(syms, period=YEARS, interval="1d", auto_adjust=True,
                     group_by="ticker", threads=True, progress=False)

    info={}; ccy={}
    print("Fetching fundamentals + news ...")
    for s in syms:
        try:
            t=yf.Ticker(s); fi=t.fast_info
            d={"mc":fi.get("market_cap") if hasattr(fi,"get") else fi.market_cap,
               "cur":fi.get("currency") if hasattr(fi,"get") else fi.currency}
            try:
                nfo=t.info
                d.update(ev=nfo.get("enterpriseValue"), cash=nfo.get("totalCash"),
                         debt=nfo.get("totalDebt"), shares=nfo.get("sharesOutstanding"),
                         rev=nfo.get("totalRevenue"), website=nfo.get("website"),
                         si_pf=nfo.get("shortPercentOfFloat"), si_ratio=nfo.get("shortRatio"),
                         si_shares=nfo.get("sharesShort"), si_prior=nfo.get("sharesShortPriorMonth"),
                         si_date=nfo.get("dateShortInterest"))
            except Exception: pass
            try:
                news=[]
                for n in (t.news or [])[:6]:
                    c=n.get("content",n)
                    news.append({"t":c.get("title") or n.get("title"),
                                 "src":(c.get("provider",{}) or {}).get("displayName") or n.get("publisher",""),
                                 "when":rel(n.get("providerPublishTime",0)),
                                 "url":(c.get("clickThroughUrl",{}) or {}).get("url") or n.get("link","#")})
                d["news"]=[x for x in news if x["t"]]
            except Exception: d["news"]=[]
            try:
                ih=getattr(t,"institutional_holders",None); hs=[]
                if ih is not None and len(ih):
                    for _,rr in ih.iterrows():
                        hs.append({"name":str(rr.get("Holder","")),
                                   "shares":int(rr.get("Shares",0) or 0),
                                   "value":float(rr.get("Value",0) or 0),
                                   "pctOut":float(rr.get("pctHeld", rr.get("% Out",0)) or 0),
                                   "chg":None})
                d["holders"]=hs
            except Exception: d["holders"]=[]
            info[s]=d; ccy[s]=d.get("cur")
        except Exception:
            info[s]={}; ccy[s]=None
    fx=fx_rates(set(ccy.values()))
    xbi=xbi_constituents()

    rows=[]
    for s,name,region in uni:
        d=info.get(s,{}); rate=fx.get(d.get("cur")) or 1.0
        try:
            close=data[s]["Close"].dropna(); vol=data[s]["Volume"].reindex(close.index).fillna(0)
        except Exception:
            close=pd.Series(dtype="float64"); vol=pd.Series(dtype="float64")
        h=[round(float(x)*rate,4) for x in close.tolist()]
        v=[int(x) for x in vol.tolist()]
        usd=lambda k: (d.get(k)*rate) if d.get(k) is not None else None
        hi52=round(max(h[-252:]),4) if h else None
        lo52=round(min(h[-252:]),4) if h else None
        rows.append({"t":s,"n":name,"r":region,
            "mc":usd("mc"),"ev":usd("ev"),"cash":usd("cash"),"debt":usd("debt"),
            "shares":d.get("shares"),"rev":usd("rev"),"website":d.get("website"),
            "xbi": s in xbi,
            "si":{"pf":d.get("si_pf"),"ratio":d.get("si_ratio"),"shares":d.get("si_shares"),
                  "prior":d.get("si_prior"),"date":d.get("si_date")},
            "hi52":hi52,"lo52":lo52,"news":d.get("news",[]),
            "holders":[{"name":hd["name"],"shares":hd["shares"],
                        "value":(hd["value"]*rate) if hd.get("value") else hd.get("value"),
                        "pctOut":hd.get("pctOut"),"chg":hd.get("chg")} for hd in d.get("holders",[])],
            "h":h,"v":v})

    asof=dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    json.dump({"asof":asof,"rows":rows}, open(OUT,"w"), separators=(",",":"))
    miss=sum(1 for r in rows if not r["h"])
    print(f"Wrote {OUT}: {len(rows)} names, {miss} with no history. as of {asof}")
    print("Reload index.html — the badge turns green.")

if __name__=="__main__":
    main()
