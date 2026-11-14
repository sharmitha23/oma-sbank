"""'People like you' benchmarks from S-Bank's own customers, by age band.

Computed once from the full dataset (all 5,100 customers) and saved to data/peers.json, so the
bundled 40-customer sample can still show real peer numbers. Everything is a median of
per-customer monthly averages over the same 3 full months.
"""
import json

import numpy as np
import pandas as pd

from rules import EVERYDAY, FIXED, OCCASIONAL

BANDS = [(18, 24), (25, 34), (35, 44), (45, 54), (55, 64), (65, 120)]
GROUPS = ["Restaurants & takeaway", "Coffee & snacks", "Bars & nightlife", "Taxis", "Entertainment", "Shopping", "Travel", "Groceries"]


def band_of(age):
    if age is None or pd.isna(age):
        return None
    for lo, hi in BANDS:
        if lo <= int(age) <= hi:
            return f"{lo}–{hi}" if hi < 120 else f"{lo}+"
    return None


def metrics(df: pd.DataFrame, months: list[str]) -> pd.DataFrame:
    """Per-customer monthly averages. df must be classified (kind, basket, group, spend, month)."""
    d = df[df["month"].isin(months)]
    n = max(len(months), 1)
    ids = pd.Index(d["customer_id"].unique())
    by = lambda sel, col: d[sel].groupby("customer_id", observed=True)[col].sum().reindex(ids, fill_value=0)
    out = pd.DataFrame({"income": by(d["kind"] == "income", "amount") / n, "saving": -by(d["kind"] == "saving", "amount") / n}, index=ids)
    for b in (FIXED, OCCASIONAL, EVERYDAY):
        out[b] = d[d["basket"] == b].groupby("customer_id", observed=True)["spend"].sum().reindex(out.index, fill_value=0) / n
    grp = d[d["kind"] == "expense"].pivot_table(index="customer_id", columns="group", values="spend", aggfunc="sum", observed=True).reindex(out.index).fillna(0) / n
    for gname in GROUPS:
        out[gname] = grp[gname] if gname in grp else 0.0
    inc = out["income"].where(out["income"] > 0)
    out["everyday_share"] = out[EVERYDAY] / inc * 100
    out["fixed_share"] = out[FIXED] / inc * 100
    out["saving_rate"] = out["saving"].clip(lower=0) / inc * 100
    return out


def build(df_classified: pd.DataFrame, customers: pd.DataFrame | None, months: list[str]) -> dict:
    m = metrics(df_classified, months)
    if customers is not None:
        m["band"] = customers["customer_age"].reindex(m.index).map(band_of)
    else:
        m["band"] = None
    res = {"months": months, "bands": {}}
    for band, x in m.dropna(subset=["band"]).groupby("band"):
        x = x[x["income"] > 0]
        if len(x) < 5:
            continue
        res["bands"][band] = {"n": int(len(x)), **{k: round(float(x[k].median()), 1) for k in
                                                   ["income", "everyday_share", "fixed_share", "saving_rate", EVERYDAY, *GROUPS]}}
    res["n_customers"] = int(len(m))
    return res, m


def save(res, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")


def featured(m: pd.DataFrame, customers: pd.DataFrame | None, k=8) -> list[str]:
    """Pick customers with clear, different stories for the demo picker."""
    m = m[m["income"] > 0].copy()
    if customers is not None:
        m["age"] = customers["customer_age"].reindex(m.index)
    picks = []

    def add(ids):
        for i in ids:
            if i not in picks:
                picks.append(i)
                return

    young = m[m.get("age", pd.Series(dtype=float)).between(18, 26)] if "age" in m else m
    add(young.sort_values("everyday_share", ascending=False).index)          # young, lots of everyday spending
    add(m.sort_values("everyday_share", ascending=False).index)              # biggest everyday share overall
    add(m.sort_values("saving_rate", ascending=False).index)                 # strong saver
    add(m.assign(gap=m["income"] - m[[FIXED, OCCASIONAL, EVERYDAY]].sum(axis=1)).sort_values("gap").index)  # spends more than earns
    add(m.sort_values("Restaurants & takeaway", ascending=False).index)      # restaurant lover
    if "age" in m:
        add(m[m["age"] >= 65].index)
        add((m["everyday_share"] - m["everyday_share"].median()).abs().sort_values().index)  # typical
    for i in m.index:
        if len(picks) >= k:
            break
        add([i])
    return picks[:k]
