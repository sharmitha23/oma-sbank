"""Loader for the S-Pankki Junction 2026 dataset (tx_junction_transactions.csv + tx_customers_junction.csv).

Where OMA looks, in order:
1. OMA_DATA (a folder or the transactions CSV)
2. oma/data/sbank/
3. a sibling folder ../Junction-2026-S-pankki (where `git clone` puts it next to oma)
4. oma/data/sbank_sample/ (40 real customers from the dataset, bundled so the app always runs)
The first load of the full 346 MB file takes a minute; it is then cached as Parquet.
"""
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TX = "tx_junction_transactions.csv"
CUST = "tx_customers_junction.csv"


def find():
    cands = []
    if os.environ.get("OMA_DATA"):
        p = Path(os.environ["OMA_DATA"])
        cands.append(p.parent if p.is_file() else p)
    cands += [ROOT / "data" / "sbank", ROOT.parent / "Junction-2026-S-pankki", ROOT / "data" / "sbank_sample"]
    for c in cands:
        f = c / TX
        if f.exists() and not f.read_bytes()[:40].startswith(b"version https://git-lfs"):
            return c
    return None


def _read(folder: Path):
    src = folder / TX
    cache = ROOT / "data" / "cache" / f"tx-{src.stat().st_size}.parquet"
    if cache.exists():
        try:
            return pd.read_parquet(cache)
        except Exception:
            pass
    raw = pd.read_csv(src, encoding="utf-8-sig", dtype={"customer_id": "category", "bank_account_id": "category", "category": "category",
                                                         "transaction_type": "category", "merchant_id": "category"})
    df = pd.DataFrame({
        "customer_id": raw["customer_id"],
        "date": pd.to_datetime(raw["tx_date"]),
        "amount": raw["tx_amount_eur"].astype("float64"),
        "balance": raw["balance_after_eur"].astype("float64"),
        "category": raw["category"],
        "ttype": raw["transaction_type"],
        "mcc": raw["mcc_code"].astype("Int64"),
        "merchant_id": raw["merchant_id"],
    })
    # merchant key: the merchant id, or the transaction type for bills/salary (they have no merchant)
    m = df["merchant_id"].astype("object")
    fallback = ("TYPE:" + df["ttype"].astype(str)).where(df["ttype"].astype(str) != "purchase", "CAT:" + df["category"].astype(str))
    df["merchant"] = m.where(m.notna(), fallback).astype("category")
    df = df.drop(columns="merchant_id")
    df = df.sort_values(["customer_id", "date"], kind="stable").reset_index(drop=True)
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache, index=False)
    except Exception:
        pass
    return df


def load():
    folder = find()
    if folder is None:
        return None
    df = _read(folder)
    cust = None
    if (folder / CUST).exists():
        c = pd.read_csv(folder / CUST, encoding="utf-8-sig", dtype={"customer_id": str, "customer_postal_code": str})
        cust = c.set_index("customer_id")
    report = {"source": "S-Pankki Junction 2026 (synthetic)", "folder": folder.name, "demo": False, "sbank": True,
              "sample": folder.name == "sbank_sample", "rows": int(len(df)), "customers": int(df["customer_id"].nunique()),
              "date_range": [str(df["date"].min().date()), str(df["date"].max().date())], "warnings": []}
    return df, cust, report


def customer_frame(df_slice: pd.DataFrame) -> pd.DataFrame:
    """Per-customer slice in the shape the engine expects (plain strings, description = transaction type)."""
    d = df_slice.copy()
    for col in ("customer_id", "category", "ttype", "merchant"):
        d[col] = d[col].astype(str)
    d["description"] = d["ttype"]
    return d.reset_index(drop=True)
