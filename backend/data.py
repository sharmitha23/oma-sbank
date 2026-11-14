"""Load the S-Bank challenge dataset into one canonical table, whatever its column names.

Canonical columns: customer_id, date, amount (negative = money out), merchant, category,
description, balance (optional).

Set OMA_DATA=/path/to/file.csv|.parquet|.xlsx (or a folder) to use the real dataset.
Run `python scripts/inspect_dataset.py <file>` first to see how columns get mapped; fix
anything wrong in COLUMN_OVERRIDES below rather than guessing.
If no dataset is configured, OMA generates a clearly labelled demo dataset.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

# Force a mapping once you've seen the real columns, e.g. {"amount": "Summa", "date": "Kirjauspäivä"}
COLUMN_OVERRIDES: dict[str, str] = {}

SYNONYMS = {
    "customer_id": ["customer_id", "customer", "client_id", "user_id", "account_id", "asiakas", "asiakasnumero", "account", "tili", "person_id", "id_customer"],
    "date": ["date", "booking_date", "transaction_date", "value_date", "timestamp", "datetime", "time", "kirjauspäivä", "kirjauspaiva", "päivämäärä", "paivamaara", "pvm", "arvopäivä"],
    "amount": ["amount", "amount_eur", "sum", "value", "summa", "määrä", "maara", "eur", "transaction_amount"],
    "merchant": ["merchant", "merchant_name", "counterparty", "payee", "receiver", "recipient", "saaja", "maksaja", "saaja/maksaja", "name", "vastapuoli", "description_short"],
    "category": ["category", "merchant_category", "mcc_description", "mcc", "kategoria", "luokka", "category_name", "subcategory"],
    "description": ["description", "message", "text", "details", "viesti", "selite", "memo", "reference", "transaction_type"],
    "balance": ["balance", "saldo", "account_balance", "balance_after"],
    "direction": ["direction", "credit_debit", "debit_credit", "type", "sign", "cd", "in_out"],
}


def _norm(s: str) -> str:
    return str(s).strip().lower().replace(" ", "_")


def map_columns(cols) -> dict:
    normed = {_norm(c): c for c in cols}
    mapping = {}
    for canon, syns in SYNONYMS.items():
        if canon in COLUMN_OVERRIDES:
            mapping[canon] = COLUMN_OVERRIDES[canon]
            continue
        for s in syns:
            if _norm(s) in normed and normed[_norm(s)] not in mapping.values():
                mapping[canon] = normed[_norm(s)]
                break
    return mapping


def _to_number(series: pd.Series) -> pd.Series:
    if series.dtype.kind in "if":
        return series.astype(float)
    s = series.astype(str).str.replace("−", "-").str.replace(r"[€\s\xa0]", "", regex=True)
    # Finnish style 1.234,56 -> 1234.56
    s = s.where(~s.str.contains(","), s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False))
    return pd.to_numeric(s, errors="coerce")


def _read_any(path: Path) -> pd.DataFrame:
    if path.is_dir():
        files = sorted([p for p in path.iterdir() if p.suffix.lower() in (".csv", ".parquet", ".xlsx", ".json")])
        return pd.concat([_read_any(p) for p in files], ignore_index=True)
    suf = path.suffix.lower()
    if suf == ".parquet":
        return pd.read_parquet(path)
    if suf == ".xlsx":
        return pd.read_excel(path)
    if suf == ".json":
        return pd.read_json(path)
    return pd.read_csv(path, sep=None, engine="python")  # sniff , or ;


def normalise(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    m = map_columns(raw.columns)
    report = {"mapped": m, "unmapped_columns": [c for c in raw.columns if c not in m.values()], "warnings": []}
    for req in ("date", "amount"):
        if req not in m:
            raise ValueError(f"Could not find a '{req}' column. Columns: {list(raw.columns)}. Set COLUMN_OVERRIDES in backend/data.py.")
    df = pd.DataFrame()
    df["customer_id"] = raw[m["customer_id"]].astype(str) if "customer_id" in m else "customer-1"
    df["date"] = pd.to_datetime(raw[m["date"]], errors="coerce", dayfirst=raw[m["date"]].astype(str).str.match(r"^\d{1,2}\.").any())
    df["amount"] = _to_number(raw[m["amount"]])
    for c in ("merchant", "category", "description"):
        df[c] = raw[m[c]].fillna("").astype(str) if c in m else ""
    if "balance" in m:
        df["balance"] = _to_number(raw[m["balance"]])
    if "direction" in m and (df["amount"] >= 0).all():
        d = raw[m["direction"]].astype(str).str.lower()
        out = d.str.contains("debit|out|expense|d$|-|veloitus|meno", regex=True)
        df.loc[out.values, "amount"] *= -1
        report["warnings"].append(f"Amounts were all positive; used '{m['direction']}' to sign them.")
    elif (df["amount"] >= 0).all():
        report["warnings"].append("All amounts are positive and no direction column was found: money in/out cannot be told apart. Check the dataset docs and set COLUMN_OVERRIDES.")
    if not m.get("merchant"):
        report["warnings"].append("No merchant column found; classification relies on category/description only.")
    bad = df["date"].isna() | df["amount"].isna()
    if bad.any():
        report["warnings"].append(f"Dropped {int(bad.sum())} rows with unreadable date/amount.")
    df = df[~bad].sort_values(["customer_id", "date"]).reset_index(drop=True)
    df["date"] = df["date"].dt.tz_localize(None) if df["date"].dt.tz is not None else df["date"]
    df["date"] = df["date"].dt.normalize()
    report["rows"] = len(df)
    report["customers"] = int(df["customer_id"].nunique())
    report["date_range"] = [str(df["date"].min().date()), str(df["date"].max().date())]
    return df, report


# ----------------------------------------------------------------------------------------
# Demo data: used only when no real dataset is configured. Clearly labelled in the UI.
# ----------------------------------------------------------------------------------------
DEMO_PERSONAS = {
    "demo-aino": {"name": "Aino", "about": "22, student in Helsinki, part-time job", "seed": 6},
    "demo-mikko": {"name": "Mikko", "about": "28, junior developer in Espoo", "seed": 2},
    "demo-laura": {"name": "Laura", "about": "34, nurse in Tampere, one child", "seed": 3},
}


def generate_demo(end=pd.Timestamp("2026-11-08"), months=12) -> pd.DataFrame:
    rows = []
    start = (end - pd.DateOffset(months=months)).replace(day=1)
    days = pd.date_range(start, end, freq="D")

    def add(cid, d, amt, merchant, cat, desc=""):
        rows.append((cid, d, round(float(amt), 2), merchant, cat, desc))

    for cid, p in DEMO_PERSONAS.items():
        r = np.random.default_rng(p["seed"])
        for d in days:
            dom, wd = d.day, d.weekday()
            weekend = wd >= 4
            if cid == "demo-aino":
                if dom == 1: add(cid, d, -575, "HOAS", "Housing", "Vuokra / rent")
                if dom == 1: add(cid, d, 279.8, "Kela", "Benefits", "Opintoraha")
                if dom == 15: add(cid, d, r.normal(1110, 40), "Palkka - Kahvila Oy", "Salary", "Palkka")
                if dom == 3: add(cid, d, -19.9, "Elisa", "Phone", "")
                if dom == 5: add(cid, d, -35.7, "HSL", "Public transport", "HSL kausilippu")
                if dom == 9: add(cid, d, -11.99, "Spotify", "Entertainment", "")
                if dom == 12: add(cid, d, -13.99, "Netflix", "Entertainment", "")
                if dom == 20: add(cid, d, -8.5 if d.month in (6, 7, 8) else -24.0, "Helen", "Electricity", "Sähkö")
                post_pay = 15 <= dom <= 21
                if r.random() < (0.6 if wd < 5 else 0.3): add(cid, d, -r.uniform(3.6, 5.9), r.choice(["Robert's Coffee", "Espresso House", "R-kioski"]), "Cafe", "")
                if r.random() < 0.42: add(cid, d, -r.uniform(6, 28), r.choice(["Alepa", "S-market", "Lidl"]), "Groceries", "")
                if r.random() < (0.36 if post_pay else 0.1) + (0.1 if weekend else 0): add(cid, d, -r.uniform(14, 32), r.choice(["Wolt", "Foodora", "Hesburger"]), "Restaurants", "")
                if weekend and r.random() < (0.45 if post_pay else 0.15): add(cid, d, -r.uniform(12, 40), "Kallio Bar", "Bars", "")
                if weekend and r.random() < (0.3 if post_pay else 0.06): add(cid, d, -r.uniform(14, 28), "Bolt", "Taxi", "")
                if r.random() < (0.12 if post_pay else 0.03): add(cid, d, -r.uniform(19, 70), r.choice(["Zalando", "H&M", "Lindex"]), "Shopping", "")
                if r.random() < 0.012: add(cid, d, -r.uniform(8, 35), "Yliopiston Apteekki", "Pharmacy", "")
                if r.random() < 0.01: add(cid, d, -40, "Otto.", "Cash", "Käteisnosto")
                if dom == 2 and d.month == 3: add(cid, d, -189, "Hammaslääkäri Hymy", "Dentist", "")
                if dom == 18 and d.month == 9: add(cid, d, -129, "Finnair", "Travel", "")
            elif cid == "demo-mikko":
                if dom == 15: add(cid, d, r.normal(3080, 25), "Palkka - Koodi Oy", "Salary", "Palkka")
                if dom == 1: add(cid, d, -1090, "SATO", "Housing", "Vuokra")
                if dom == 4: add(cid, d, -29.9, "DNA", "Internet", "")
                if dom == 6: add(cid, d, -39.9, "Elixia", "Gym", "")
                if dom == 10: add(cid, d, -13.99, "Netflix", "Entertainment", "")
                if dom == 10: add(cid, d, -11.99, "Spotify", "Entertainment", "")
                if dom == 11: add(cid, d, -9.99, "Max", "Entertainment", "max.com")
                if dom == 14: add(cid, d, -12.99, "Disney+", "Entertainment", "")
                if dom == 22: add(cid, d, -r.uniform(30, 75), "Helen", "Electricity", "")
                if dom == 16: add(cid, d, -150, "Oma säästötili", "Transfer", "Siirto omalle tilille")
                if dom == 1 and d.month in (1, 4, 7, 10): add(cid, d, -96, "LähiTapiola", "Insurance", "Kotivakuutus")
                if r.random() < 0.5: add(cid, d, -r.uniform(3.9, 6.5), r.choice(["Espresso House", "Starbucks"]), "Cafe", "")
                if r.random() < 0.38: add(cid, d, -r.uniform(12, 55), r.choice(["Prisma", "K-Supermarket", "S-market"]), "Groceries", "")
                if r.random() < (0.32 if weekend else 0.22): add(cid, d, -r.uniform(18, 38), r.choice(["Wolt", "Wolt", "Foodora", "Ravintola Savu"]), "Restaurants", "")
                if wd in (4, 5) and r.random() < 0.7: add(cid, d, -r.uniform(25, 90), r.choice(["Bar Loose", "Kallio Bar", "Pub Old Irish"]), "Bars", "")
                if wd in (4, 5) and r.random() < 0.45: add(cid, d, -r.uniform(16, 38), r.choice(["Uber", "Bolt", "Taksi Helsinki"]), "Taxi", "")
                if r.random() < 0.05: add(cid, d, -r.uniform(25, 160), r.choice(["Verkkokauppa.com", "Zalando", "Amazon"]), "Shopping", "")
                if r.random() < 0.03: add(cid, d, -r.uniform(15, 35), "Steam", "Games", "")
                if dom == 3 and d.month == 6: add(cid, d, -412, "Autokorjaamo Virtanen", "Car repair", "Huolto")
                if dom == 20 and d.month == 2: add(cid, d, -264, "Finnair", "Travel", "")
            else:  # Laura
                if dom == 15: add(cid, d, r.normal(2610, 20), "Palkka - Hyvinvointialue", "Salary", "Palkka")
                if dom == 20: add(cid, d, 94.9, "Kela", "Benefits", "Lapsilisä")
                if dom == 1: add(cid, d, -980, "Lumo", "Housing", "Vuokra")
                if dom == 2: add(cid, d, -288, "Tampereen varhaiskasvatus", "Childcare", "")
                if dom == 5: add(cid, d, -19.9, "Telia", "Phone", "")
                if dom == 8: add(cid, d, -55, "Nysse", "Public transport", "Kausilippu")
                if dom == 21: add(cid, d, -r.uniform(40, 85), "Elenia", "Electricity", "Sähkö")
                if dom == 16: add(cid, d, -250, "Oma säästötili", "Transfer", "Siirto omalle tilille")
                if dom == 1 and d.month in (2, 8): add(cid, d, -142, "Pohjola Vakuutus", "Insurance", "")
                if dom == 12: add(cid, d, -11.99, "Spotify", "Entertainment", "")
                if r.random() < 0.18: add(cid, d, -r.uniform(3.5, 5), "R-kioski", "Cafe", "")
                if r.random() < (0.55 if wd in (3, 5) else 0.25): add(cid, d, -r.uniform(25, 95), r.choice(["Prisma", "S-market", "Lidl"]), "Groceries", "")
                if weekend and r.random() < 0.18: add(cid, d, -r.uniform(25, 60), r.choice(["Ravintola Plevna", "Rax Buffet"]), "Restaurants", "")
                if r.random() < 0.04: add(cid, d, -r.uniform(15, 60), r.choice(["Lindex", "Kappahl", "Clas Ohlson"]), "Shopping", "")
                if r.random() < 0.015: add(cid, d, -r.uniform(12, 45), "Apteekki", "Pharmacy", "")
                if dom == 14 and d.month == 9: add(cid, d, -549, "Gigantti", "Electronics", "Pesukone / washing machine")
                if dom == 7 and d.month == 4: add(cid, d, -165, "Terveystalo", "Health", "")
                if dom == 23 and d.month == 12: add(cid, d, -210, "Tokmanni", "Shopping", "")
    return pd.DataFrame(rows, columns=["customer_id", "booking_date", "amount", "merchant_name", "category", "description"])


def load() -> tuple[pd.DataFrame, dict]:
    src = os.environ.get("OMA_DATA")
    if src and Path(src).exists():
        df, report = normalise(_read_any(Path(src)))
        report["source"] = Path(src).name
        report["demo"] = False
        return df, report
    demo_path = ROOT / "data" / "demo_transactions.csv"
    if not demo_path.exists():
        demo_path.parent.mkdir(exist_ok=True)
        generate_demo().to_csv(demo_path, index=False)
    df, report = normalise(pd.read_csv(demo_path))
    report["source"] = "OMA demo data (generated, not S-Bank data)"
    report["demo"] = True
    return df, report
