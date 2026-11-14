# OMA: Your money. Your understanding.

**Junction 2026 · S-Pankki challenge.** An AI financial coach for S-mobiili that lets customers talk with their own transaction data in **Finnish (default), Swedish or English**. It sorts every euro into the challenge's **three baskets**, explains a **safe-to-spend** amount step by step, simulates **what-if** savings, compares you with **S-Bank customers your age**, and gives only **vetted, data-triggered advice**.

```
S-Pankki transactions ──► Financial engine (pandas, deterministic) ──► AI coach (tool calls only) ──► Mobile web app
   MCC + type + balance        every number + vetted advice           explains, never calculates       FI / SV / EN
```

## Run it

**Windows:** double-click `start.bat`, or:
```cmd
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```
**macOS/Linux:** `./start.sh`

Open **http://localhost:8000**. On a phone on the same wifi, open `http://<laptop-ip>:8000` (allow Python through the firewall). The built web app is included in `frontend/dist`, so Node.js is only needed if you change the frontend (`cd frontend && npm install && npm run build`).

Open a specific customer with `http://localhost:8000/?customer=CUST01365`.

## Data

OMA uses the **S-Pankki Junction 2026 dataset** (`tx_junction_transactions.csv`, `tx_customers_junction.csv`) and finds it automatically:

1. `OMA_DATA=<folder>` if set
2. `oma/data/sbank/`
3. `../Junction-2026-S-pankki/`, i.e. the dataset repo cloned next to this folder
4. `oma/data/sbank_sample/`, a bundled sample: the full two-year histories of 40 real customers from the dataset, so the app always runs

On the first start with the full file (3.6M rows, 5,100 customers), OMA caches it as Parquet and builds `data/peers.json` (age-group medians from all customers). Later starts take seconds. Commit `peers.json` so the bundled sample also shows real age-group benchmarks.

**How the data is read:**
- **Baskets** come from `transaction_type` (rent, utilities, salary, investments), the **MCC code** (5411 groceries, 5814 cafés/fast food, 4121 taxis, 5912 pharmacy…), and the bank category when the MCC is missing.
- **Large electronics or furniture purchases (≥ €300)** go to "Needs your call": a broken fridge is a must-have, a new TV isn't. The customer decides.
- **`salary_sweep`** moves salary to another own account, so it's excluded from spending and saving. **`investment_deposit`** counts as saving.
- **`balance_after_eur`** caps safe-to-spend, so OMA never suggests spending money the account doesn't have.
- **Merchants are anonymised**, so they're shown as type + number ("Ruokakauppa #0010").

## Turn on the AI

```bash
set ANTHROPIC_API_KEY=...        # Windows (use export on macOS/Linux), or:
set OPENAI_API_KEY=...           # any OpenAI-compatible API; OPENAI_BASE_URL for others
set OMA_MODEL=claude-sonnet-5-5  # optional
```
Without a key, or if the network drops, the rule engine answers the core questions in all three languages. The UI shows which mode answered.

## How OMA avoids hallucinations and bad advice

1. **Topic guards run before any AI.** Investment, loan/credit, debt-trouble and tax questions get a vetted answer, never a product recommendation. Debt worries point to free help: the state's talous- ja velkaneuvonta and Takuusäätiö's Velkalinja 0800 9 8009.
2. **The AI never does arithmetic.** It can only call 17 engine tools. The engine computes, the AI explains.
3. **Advice comes from a vetted catalogue** (`engine.advice()`): start a buffer, weekly allowance, irregular-cost reserve, halve one habit, get back to balance… Each tip is triggered by the customer's real numbers. Essentials (rent, food, medicine, childcare) are never targeted.
4. **Every € figure is checked** against tool results. If one is unverified, the AI rewrites once, and if it still fails, the rule engine answers instead. The UI shows "✓ 3 figures checked" and **Show the math**.
5. **Lessons are written by the team** (10, in FI/SV/EN), not generated.

## Project layout

| | |
|---|---|
| `backend/sbank.py` | Dataset discovery, Parquet cache, per-customer frames |
| `backend/rules.py` | MCC / transaction-type / category → group → basket |
| `backend/engine.py` | Baskets, bills due, safe-to-spend (with balance cap), what-if, safe-to-save, pay cycle, spender profile, Statistics Finland + age-peer benchmarks, insights, vetted advice |
| `backend/peers.py` | Age-group medians from all customers; featured demo customers |
| `backend/coach.py` | Guards, AI tool loop with grounding check + retry, multilingual offline router |
| `backend/i18n.py`, `lessons.py` | All backend text in FI/SV/EN, MCC labels, verified help resources |
| `frontend/src` | React app: Home, Spending, Ask OMA, Goals |
| `data/featured.json` | Demo customers shown first in the picker |
