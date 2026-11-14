"""OMA API + web app. Run from backend/: python -m uvicorn app:app --host 0.0.0.0 --port 8000
Every endpoint takes ?lang=fi|sv|en (default fi).

Data: the S-Pankki Junction dataset is found automatically (see sbank.py). Without it, the bundled
40-customer sample from the same dataset is used.
"""
import json
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import coach
import data
import peers as P
import sbank
from engine import Customer, classify, full_months
from i18n import PERSONA_ABOUT, basket_meta, norm, pick, t
from lessons import lessons as get_lessons
from rules import BASKET_IDS

app = FastAPI(title="OMA API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATA_DIR = data.ROOT / "data"
loaded = sbank.load()
if loaded:
    DF, CUSTOMERS, REPORT = loaded
else:  # generic CSV via OMA_DATA, or generated demo personas
    DF, REPORT = data.load()
    CUSTOMERS = None
    REPORT["sbank"] = False
INDEX = DF.groupby("customer_id", observed=True).indices
AS_OF = DF["date"].max()

# Peer benchmarks + featured customers. Built from the full dataset when available and saved, so the
# small sample can reuse real medians from all 5,100 customers.
PEERS_FILE = DATA_DIR / "peers.json"
PEERS, FEATURED = None, []
if REPORT.get("sbank"):
    saved = json.loads(PEERS_FILE.read_text(encoding="utf-8")) if PEERS_FILE.exists() else None
    if saved and saved.get("source_rows") == REPORT["rows"]:
        PEERS = saved
    else:
        print(f"OMA: preparing benchmarks from {REPORT['customers']} customers (first run only)…")
        allc = classify(sbank.customer_frame(DF))
        built, metrics = P.build(allc, CUSTOMERS, full_months(allc, AS_OF, 3))
        built["source_rows"] = REPORT["rows"]
        built["featured"] = P.featured(metrics, CUSTOMERS)
        del allc
        if REPORT["customers"] >= 500 or not (saved and saved.get("n_customers", 0) >= 500):
            PEERS = built
            P.save(built, PEERS_FILE)
        else:  # small sample: keep the full-data medians already saved, but use this sample's featured picks
            PEERS = {**saved, "featured": built["featured"]}
    curated = DATA_DIR / "featured.json"
    picks = json.loads(curated.read_text(encoding="utf-8"))["featured"] if curated.exists() else []
    FEATURED = list(dict.fromkeys([c for c in picks + PEERS.get("featured", []) if c in INDEX]))[:8]

CACHE: dict[str, Customer] = {}
OVERRIDES_FILE = DATA_DIR / "overrides.json"
OVERRIDES = json.loads(OVERRIDES_FILE.read_text()) if OVERRIDES_FILE.exists() else {}


def age_of(cid):
    if CUSTOMERS is not None and cid in CUSTOMERS.index:
        return int(CUSTOMERS.loc[cid, "customer_age"])
    return None


def customers(lang):
    if not REPORT.get("sbank"):
        return [{"id": k, "name": v["name"], "about": pick(PERSONA_ABOUT[k], lang)} for k, v in data.DEMO_PERSONAS.items()]
    ids = FEATURED + [c for c in sorted(INDEX) if c not in FEATURED] if REPORT["customers"] <= 60 else FEATURED
    out = []
    for c in ids:
        age = age_of(c)
        postal = str(CUSTOMERS.loc[c, "customer_postal_code"]) if CUSTOMERS is not None and c in CUSTOMERS.index else ""
        out.append({"id": c, "name": c, "age": age, "about": " · ".join(x for x in [t("years", lang, n=age) if age else "", postal] if x),
                    "featured": c in FEATURED})
    return out


def get(cid: str, lang: str = "fi") -> Customer:
    if cid not in INDEX:
        raise HTTPException(404, "Unknown customer")
    if cid not in CACHE:
        rows = DF.iloc[INDEX[cid]]
        if REPORT.get("sbank"):
            CACHE[cid] = Customer(sbank.customer_frame(rows), name=None, overrides=OVERRIDES.get(cid, {}), age=age_of(cid),
                                  as_of_date=AS_OF, peers=PEERS)
        else:
            CACHE[cid] = Customer(rows.reset_index(drop=True), name=data.DEMO_PERSONAS.get(cid, {}).get("name", "you"), overrides=OVERRIDES.get(cid, {}))
    c = CACHE[cid]
    c.lang = norm(lang)  # one language per request is enough for a single-user demo server
    return c


@app.get("/api/meta")
def meta(lang: str = "fi"):
    return {"customers": customers(lang), "dataset": REPORT, "ai": coach.provider() or "offline",
            "baskets": {b: basket_meta(b, lang) for b in BASKET_IDS}}


@app.get("/api/customer/{cid}")
def customer(cid: str, lang: str = "fi"):
    c = get(cid, lang)
    return {"id": cid, "name": cid, "age": c.age}


@app.get("/api/{cid}/home")
def home(cid: str, lang: str = "fi"):
    c = get(cid, lang)
    return {"this_month": c.month_summary("this_month"), "safe_to_spend": c.safe_to_spend(), "insights": c.insights(),
            "profile": c.spender_profile(), "baskets": c.baskets()}


@app.get("/api/{cid}/spending")
def spending(cid: str, lang: str = "fi"):
    c = get(cid, lang)
    return {"baskets": c.baskets(), "uncertain": c.uncertain(), "benchmark": c.benchmark(), "payday": c.payday_cycle(),
            "peers": c.peer_benchmark()}


@app.get("/api/{cid}/explore")
def explore(cid: str, group_by: str = "category", period: str = "last_month", basket: str | None = None, category: str | None = None, lang: str = "fi"):
    return get(cid, lang).spending(group_by, period, basket, category)


class Classify(BaseModel):
    merchant: str
    basket: str


@app.post("/api/{cid}/classify")
def classify_merchant(cid: str, body: Classify):
    if body.basket not in BASKET_IDS:
        raise HTTPException(400, "Unknown basket")
    c = get(cid)
    c.overrides[body.merchant] = body.basket
    OVERRIDES[cid] = c.overrides
    OVERRIDES_FILE.write_text(json.dumps(OVERRIDES, indent=1))
    c.refresh()
    return {"ok": True}


class Settings(BaseModel):
    savings_rate: float


@app.post("/api/{cid}/settings")
def settings(cid: str, body: Settings, lang: str = "fi"):
    c = get(cid, lang)
    c.savings_rate = min(max(body.savings_rate, 0), 0.5)
    return c.safe_to_spend()


@app.get("/api/{cid}/goals")
def goals(cid: str, lang: str = "fi"):
    c = get(cid, lang)
    everyday = next(x for x in c.baskets()["baskets"] if x["id"] == "everyday")
    return {"options": [{"target": g["id"], "label": g["label"], "monthly_avg": g["monthly_avg"]} for g in everyday["groups"] if g["monthly_avg"] >= 5],
            "safe_to_save": c.safe_to_save(), "advice": c.advice()["items"]}


@app.get("/api/{cid}/whatif")
def whatif(cid: str, target: str, pct: float = 20, goal: float | None = None, lang: str = "fi"):
    return get(cid, lang).what_if(target, pct, goal)


class Ask(BaseModel):
    messages: list[dict]
    lang: str = "fi"


@app.post("/api/{cid}/ask")
def ask(cid: str, body: Ask):
    msgs = [{"role": m["role"], "content": str(m["content"])} for m in body.messages if m.get("role") in ("user", "assistant") and m.get("content")][-10:]
    if not msgs or msgs[-1]["role"] != "user":
        raise HTTPException(400, "Last message must be from the user")
    return coach.ask(get(cid, body.lang), msgs, REPORT.get("demo", False))


@app.get("/api/lessons")
def lessons(lang: str = "fi"):
    return get_lessons(lang)


DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
