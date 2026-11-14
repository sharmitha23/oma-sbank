"""Inspect the challenge dataset before trusting it.

Usage: python scripts/inspect_dataset.py path/to/transactions.csv
Prints raw columns, sample rows, how OMA maps them, and how transactions get classified.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
import pandas as pd  # noqa: E402

import data  # noqa: E402
import engine  # noqa: E402

path = Path(sys.argv[1])
raw = data._read_any(path)
print(f"\nRAW: {len(raw):,} rows x {len(raw.columns)} columns\n")
print(raw.dtypes.to_string(), "\n")
print(raw.head(8).to_string(), "\n")
df, rep = data.normalise(raw)
print("MAPPING:", rep["mapped"])
print("UNMAPPED:", rep["unmapped_columns"])
for w in rep["warnings"]:
    print("WARNING:", w)
print(f"\n{rep['customers']} customers, {rep['date_range'][0]} -> {rep['date_range'][1]}")
cid = df["customer_id"].value_counts().index[0]
c = engine.Customer(df[df["customer_id"] == cid])
print(f"\nClassification for busiest customer {cid}:")
print(c.df[c.df["kind"] == "expense"].groupby(["basket", "group"])["spend"].agg(["sum", "count"]).round(0).to_string())
print("\nTop uncertain merchants (add keywords to backend/rules.py):")
print(pd.DataFrame(c.uncertain(15)).to_string())
print("\nTop categories in the raw data:")
if "category" in rep["mapped"]:
    print(raw[rep["mapped"]["category"]].value_counts().head(30).to_string())
