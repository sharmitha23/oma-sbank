"""Deterministic financial engine. Every number OMA shows or says comes from here.

The LLM never calculates; it calls these methods (see coach.py) and explains the results.
`advice()` is the vetted catalogue of recommendations: the coach may not invent others.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import rules
from i18n import (GROUP_LABELS, MONTHS, MONTHS_SHORT, WEEKDAYS, basket_meta, cap, date_long, date_short,
                  group_label, merchant_label, money, month_year, pct, t)
from rules import BASKET_IDS, EVERYDAY, FIXED, OCCASIONAL, UNCERTAIN

r2 = lambda x: round(float(x), 2) + 0.0


# ---------------------------------------------------------------- classification
def classify(df: pd.DataFrame, overrides: dict | None = None) -> pd.DataFrame:
    df = df.copy()
    if "mcc" in df.columns:  # S-Pankki dataset: transaction type + MCC code + bank category
        g, b, k, why = rules.classify_sbank(df)
        df["group"], df["basket"], df["kind"] = g, b, k
        df["reason"] = [(w, None if pd.isna(m) else int(m)) for w, m in zip(why, df["mcc"])]
    else:  # generic data: keyword rules on merchant/category/description text
        text = (df["merchant"] + " " + df["category"] + " " + df["description"]).str.lower()
        out = {x: rules.match_group(x) for x in text.unique()}
        df["group"] = [out[x][0] for x in text]
        df["basket"] = [out[x][1] for x in text]
        df["reason"] = [out[x][2] for x in text]
        df["kind"] = np.where(df["basket"] == "transfer", "saving", np.where(df["amount"] > 0, "income", "expense"))
        inc = df["kind"] == "income"
        df.loc[inc, "group"] = [rules.match_income(x) for x in text[inc]]
        df.loc[inc, "basket"] = "income"
        df.loc[df["kind"] == "saving", "basket"] = "saving"
    df["spend"] = np.where(df["kind"] == "expense", -df["amount"], 0.0)
    df["month"] = df["date"].dt.to_period("M").astype(str)

    # Recurring per merchant: most months, ~once a month, stable amount (bills may vary in amount;
    # subscriptions are near-identical). Bill types without a merchant (rent, utilities) count if they come most months.
    exp = df[df["kind"] == "expense"]
    n_months = max(exp["month"].nunique(), 1)
    stats = exp.groupby("merchant").agg(months=("month", "nunique"), n=("amount", "size"), mean=("spend", "mean"), std=("spend", "std"))
    stats["cv"] = (stats["std"].fillna(0) / stats["mean"]).fillna(0)
    bill = exp.groupby("merchant")["basket"].first().isin([FIXED, "fixed_if_recurring"])
    stats["max_cv"] = np.where(bill.reindex(stats.index).fillna(False), 0.4, 0.1)
    often = (stats["months"] >= min(3, n_months)) & (stats["months"] >= 0.6 * n_months)
    typed_bill = stats.index.to_series().str.startswith("TYPE:") & bill.reindex(stats.index).fillna(False)
    rec = stats[often & (((stats["n"] <= stats["months"] * 1.3) & (stats["cv"] < stats["max_cv"])) | typed_bill)]
    df["recurring"] = df["merchant"].isin(rec.index) & (df["kind"] == "expense")
    pt = df["basket"] == "fixed_if_recurring"
    df.loc[pt & df["recurring"], "basket"] = FIXED
    df.loc[pt & ~df["recurring"], "basket"] = EVERYDAY
    for merchant, basket in (overrides or {}).items():
        sel = (df["merchant"] == merchant) & (df["kind"] == "expense")
        df.loc[sel, "basket"] = basket
        df.loc[sel, "reason"] = [("user", None)] * int(sel.sum())
    return df


# ---------------------------------------------------------------- periods
@dataclass
class Period:
    start: pd.Timestamp
    end: pd.Timestamp  # inclusive
    label: str
    partial: bool = False


def resolve_period(spec: str | None, as_of: pd.Timestamp, lang="fi") -> Period:
    s = (spec or "this_month").strip().lower().replace(" ", "_")
    m0 = as_of.replace(day=1)
    if s in ("this_month", "current_month"):
        if as_of.is_month_end:
            return Period(m0, as_of, month_year(as_of, lang))
        return Period(m0, as_of, t("p_this_month", lang, month=cap(MONTHS[lang][as_of.month - 1]), d=as_of.day, m=as_of.month, mon=MONTHS_SHORT["en"][as_of.month - 1]), True)
    if s in ("last_month", "previous_month"):
        st = m0 - pd.DateOffset(months=1)
        return Period(st, m0 - pd.Timedelta(days=1), month_year(st, lang))
    if s == "this_week":
        return Period(as_of - pd.Timedelta(days=as_of.weekday()), as_of, t("p_this_week", lang), True)
    if s == "last_week":
        st = as_of - pd.Timedelta(days=as_of.weekday() + 7)
        return Period(st, st + pd.Timedelta(days=6), t("p_last_week", lang))
    if mm := re.fullmatch(r"last_(\d+)_(day|days|month|months)", s):
        n, unit = int(mm.group(1)), mm.group(2)
        if unit.startswith("day"):
            return Period(as_of - pd.Timedelta(days=n - 1), as_of, t("p_last_days", lang, n=n))
        me = m0 + pd.DateOffset(months=1) if as_of.is_month_end else m0
        return Period(me - pd.DateOffset(months=n), me - pd.Timedelta(days=1), t("p_last_months", lang, n=n))
    if s in ("ytd", "this_year"):
        return Period(as_of.replace(month=1, day=1), as_of, t("p_ytd", lang, y=as_of.year), True)
    if s in ("all", "all_time", "last_12_months", "year"):
        me = m0 + pd.DateOffset(months=1) if as_of.is_month_end else m0
        return Period(me - pd.DateOffset(months=12), me - pd.Timedelta(days=1), t("p_last_months", lang, n=12))
    if re.fullmatch(r"\d{4}-\d{2}", s):
        st = pd.Timestamp(s + "-01")
        en = st + pd.offsets.MonthEnd(0)
        return Period(st, min(en, as_of), month_year(st, lang), en > as_of)
    return resolve_period("this_month", as_of, lang)


def _in(df, p: Period):
    return df[(df["date"] >= p.start) & (df["date"] <= p.end)]


def full_months(df, as_of, n):
    m0 = as_of.replace(day=1)
    if as_of.is_month_end:  # data runs to the last day of the month: that month is complete too
        m0 = m0 + pd.DateOffset(months=1)
    months = [str((m0 - pd.DateOffset(months=i)).to_period("M")) for i in range(n, 0, -1)]
    have = set(df["month"])
    return [m for m in months if m in have]


def groups_matching(term: str):
    """Group ids whose id or any translated label contains the term (any language)."""
    q = term.lower().strip()
    return [g for g, labels in GROUP_LABELS.items() if q in g.lower() or any(q in x.lower() for x in labels)
            or any(x.lower() in q for x in (g, *labels) if len(x) > 3)]


# ---------------------------------------------------------------- the engine
@dataclass
class Customer:
    df: pd.DataFrame
    name: str = "you"
    savings_rate: float = 0.10
    overrides: dict = field(default_factory=dict)
    lang: str = "fi"
    age: int | None = None
    as_of_date: pd.Timestamp | None = None   # dataset-wide "today", so every customer shares one date
    peers: dict | None = None                # age-band medians from peers.py

    def __post_init__(self):
        self.raw = self.df
        self.refresh()

    def refresh(self):
        self.df = classify(self.raw, self.overrides)
        self.as_of = self.as_of_date if self.as_of_date is not None else self.df["date"].max()
        self.exp = self.df[self.df["kind"] == "expense"]
        self.inc = self.df[self.df["kind"] == "income"]
        self.has_balance = "balance" in self.df and self.df["balance"].notna().any()
        self.mcc_of = self.df.dropna(subset=["mcc"]).groupby("merchant")["mcc"].first().to_dict() if "mcc" in self.df else {}

    def _ml(self, m):
        return merchant_label(m, self.lang, self.mcc_of.get(m))

    # helpers
    def _m(self, x):
        return money(x, self.lang)

    def _p(self, spec):
        return resolve_period(spec, self.as_of, self.lang)

    def _g(self, g):
        return group_label(g, self.lang)

    def _reason(self, r, recurring=False):
        code, kw = r
        if code == "mcc" and kw is not None:
            from i18n import MCC_LABELS, pick
            kw = f"{kw}" + (f" ({pick(MCC_LABELS[kw], self.lang)})" if kw in MCC_LABELS else "")
        s = t(f"reason_{code}", self.lang, kw=kw)
        return s + (t("reason_recurring", self.lang) if recurring else "")

    def _filter(self, d, basket=None, group=None, merchant=None):
        if basket:
            d = d[d["basket"] == basket]
        if group:
            ids = groups_matching(group)
            d = d[d["group"].isin(ids) | d["category"].str.lower().str.contains(re.escape(group.lower()))]
        if merchant:
            d = d[d["merchant"].str.lower().str.contains(re.escape(merchant.lower()))]
        return d

    def _month_short(self, m):
        return MONTHS_SHORT[self.lang][pd.Period(m).month - 1]

    # ---------- generic exploration (MyData: the customer slices their own data)
    def spending(self, group_by="group", period="this_month", basket=None, group=None, merchant=None, top_n=8):
        p = self._p(period)
        d = self._filter(_in(self.exp, p), basket, group, merchant)
        key = {"category": "group", "group": "group", "merchant": "merchant", "basket": "basket", "month": "month", "weekday": "weekday"}.get(group_by, "group")
        if key == "weekday":
            d = d.assign(weekday=d["date"].dt.weekday)
        g = d.groupby(key)["spend"].agg(["sum", "count"]).reset_index()
        if key == "weekday":
            g = g.set_index(key).reindex(range(7), fill_value=0).reset_index()
        elif key == "month":
            g = g.sort_values(key)
        else:
            g = g.sort_values("sum", ascending=False)

        def label(v):
            if key == "basket":
                return basket_meta(v, self.lang)["name"] if v in BASKET_IDS else str(v)
            if key == "group":
                return self._g(v)
            if key == "weekday":
                return WEEKDAYS[self.lang][int(v)]
            if key == "merchant":
                return self._ml(v)
            return str(v)
        rows = [{"label": label(r[key]), "key": str(r[key]), "amount": r2(r["sum"]), "count": int(r["count"])} for _, r in g.iterrows()]
        if key not in ("month", "weekday") and len(rows) > top_n:
            rest = rows[top_n:]
            rows = rows[:top_n] + [{"label": t("others", self.lang, n=len(rest)), "key": "_other", "amount": r2(sum(x["amount"] for x in rest)), "count": sum(x["count"] for x in rest)}]
        names = [basket and basket_meta(basket, self.lang)["name"], group and (self._g(groups_matching(group)[0]) if groups_matching(group) else group), merchant]
        filt = ", ".join(x for x in names if x)
        return {"period": p.label, "partial_period": p.partial, "filter": filt or t("all_spending", self.lang), "group_by": key,
                "total": r2(d["spend"].sum()), "transactions": int(len(d)), "rows": rows,
                "chart": {"type": "line" if key == "month" else ("columns" if key == "weekday" else "bars"),
                          "title": f"{cap(filt) if filt else t('spending', self.lang)} · {p.label}"}}

    def transactions(self, period="this_month", basket=None, group=None, merchant=None, limit=12, sort="date"):
        p = self._p(period)
        base = self.df if merchant else self.df[self.df["kind"] != "income"]
        d = self._filter(_in(base, p), basket, group, merchant)
        d = d.sort_values("spend", ascending=False) if sort == "amount" else d.sort_values("date", ascending=False)
        return {"period": p.label, "count": int(len(d)), "total_spent": r2(d["spend"].sum()),
                "items": [{"date": date_short(r.date, self.lang), "merchant": self._ml(r.merchant), "amount": r2(r.amount), "group": self._g(r.group), "basket": r.basket}
                          for r in d.head(limit).itertuples()]}

    def compare(self, period_a="last_month", period_b="this_month", group_by="group"):
        key = {"category": "group", "group": "group", "basket": "basket", "merchant": "merchant"}.get(group_by, "group")
        pa, pb = self._p(period_a), self._p(period_b)
        note = None
        if pb.partial and not pa.partial:  # like-for-like: same number of days
            days = (pb.end - pb.start).days + 1
            pa = Period(pa.start, pa.start + pd.Timedelta(days=days - 1), t("p_first_days", self.lang, n=days, month=MONTHS[self.lang][pa.start.month - 1]))
            note = t("compare_note", self.lang, a=pa.label, b=pb.label)
        da, db = _in(self.exp, pa), _in(self.exp, pb)
        ga, gb = da.groupby(key)["spend"].sum(), db.groupby(key)["spend"].sum()
        lab = (lambda v: self._g(v)) if key == "group" else ((lambda v: basket_meta(v, self.lang)["name"] if v in BASKET_IDS else v) if key == "basket" else self._ml)
        rows = []
        for k in set(ga.index) | set(gb.index):
            va, vb = ga.get(k, 0), gb.get(k, 0)
            rows.append({"label": lab(k), "key": k, "a": r2(va), "b": r2(vb), "change": r2(vb - va), "change_pct": None if va == 0 else round((vb - va) / va * 100)})
        rows.sort(key=lambda x: -abs(x["change"]))
        return {"period_a": pa.label, "period_b": pb.label, "total_a": r2(da["spend"].sum()), "total_b": r2(db["spend"].sum()),
                "total_change": r2(db["spend"].sum() - da["spend"].sum()), "rows": rows[:8], "note": note,
                "chart": {"type": "compare", "title": f"{pa.label} vs {pb.label}"}}

    # ---------- monthly picture & baskets
    def month_summary(self, period="this_month"):
        p = self._p(period)
        d = _in(self.df, p)
        income = d.loc[d["kind"] == "income", "amount"].sum()
        spend = d["spend"].sum()
        saved = -d.loc[d["kind"] == "saving", "amount"].sum()
        return {"period": p.label, "partial_period": p.partial, "income": r2(income), "spending": r2(spend),
                "moved_to_savings": r2(saved), "left_over": r2(income - spend - saved),
                "baskets": {b: r2(d.loc[d["basket"] == b, "spend"].sum()) for b in BASKET_IDS}}

    def baskets(self, months=3):
        ms = full_months(self.df, self.as_of, months)
        ms6 = full_months(self.df, self.as_of, 6)
        d = self.df[self.df["month"].isin(ms)]
        n = max(len(ms), 1)
        income = d.loc[d["kind"] == "income", "amount"].sum() / n
        out = []
        for b in BASKET_IDS:
            bd = d[d["basket"] == b]
            monthly = bd["spend"].sum() / n
            groups = bd.groupby("group")["spend"].agg(["sum", "count"]).sort_values("sum", ascending=False)
            trend = [r2(self.exp[(self.exp["month"] == m) & (self.exp["basket"] == b)]["spend"].sum()) for m in ms6]
            out.append({"id": b, **basket_meta(b, self.lang), "monthly_avg": r2(monthly),
                        "share_of_income": None if income <= 0 else round(monthly / income * 100),
                        "transactions_per_month": round(len(bd) / n, 1), "trend_6m": trend,
                        "groups": [{"id": g, "label": self._g(g), "monthly_avg": r2(v["sum"] / n), "count": int(v["count"])} for g, v in groups.iterrows()]})
        return {"months": ms, "avg_monthly_income": r2(income), "baskets": out, "months_labels": [self._month_short(m) for m in ms6]}

    def uncertain(self, limit=20):
        d = self.exp[self.exp["basket"] == UNCERTAIN]
        g = d.groupby("merchant").agg(total=("spend", "sum"), count=("spend", "size"), reason=("reason", "first"), group=("group", "first"))
        g = g.sort_values("total", ascending=False).head(limit)
        return [{"merchant": m, "label": self._ml(m), "total": r2(r.total), "count": int(r["count"]), "reason": self._reason(r.reason), "group": self._g(r.group)} for m, r in g.iterrows()]

    # ---------- payday & safe-to-spend
    def payday(self):
        if self.inc.empty:
            return None
        src = self.inc.groupby("merchant")["amount"].sum().sort_values(ascending=False)
        main = src.index[0]
        rows = self.inc[self.inc["merchant"] == main]
        return {"source": main, "day": int(rows["date"].dt.day.median()), "typical_amount": r2(rows["amount"].median())}

    @staticmethod
    def _on(year, month, day):
        return pd.Timestamp(year=year, month=month, day=min(day, calendar.monthrange(year, month)[1]))

    def _next_on_day(self, day, a):
        cand = self._on(a.year, a.month, day)
        if cand <= a:
            nm = a + pd.DateOffset(months=1)
            cand = self._on(nm.year, nm.month, day)
        return cand

    def _cycle(self):
        pay = self.payday()
        a = self.as_of
        if not pay:
            start = a.replace(day=1)
            return start, start + pd.DateOffset(months=1), None
        this = self._on(a.year, a.month, pay["day"])
        if a >= this:
            nm = a + pd.DateOffset(months=1)
            return this, self._on(nm.year, nm.month, pay["day"]), pay
        pm = a - pd.DateOffset(months=1)
        return self._on(pm.year, pm.month, pay["day"]), this, pay

    def safe_to_spend(self):
        L = self.lang
        start, nxt, pay = self._cycle()
        a = self.as_of
        days_left = max((nxt - a).days, 1)
        cyc_days = (nxt - start).days
        d = self.df[(self.df["date"] >= start) & (self.df["date"] <= a)]
        income = d.loc[d["kind"] == "income", "amount"].sum()
        got = set(d.loc[d["kind"] == "income", "merchant"])

        upcoming_income = []
        for m, g in self.inc.groupby("merchant"):
            if g["month"].nunique() >= 3 and (pay is None or m != pay["source"]):
                when = self._next_on_day(int(g["date"].dt.day.median()), a)
                if when < nxt and m not in got:
                    upcoming_income.append({"name": self._ml(m), "amount": r2(g["amount"].median()), "date": date_short(when, L)})

        # Bills still due: each repeating fixed bill's usual monthly total, minus what this cycle already paid.
        ms = full_months(self.df, a, 3)
        rec = self.exp[self.exp["recurring"] & (self.exp["basket"] == FIXED)]
        upcoming = []
        for m, g in rec.groupby("merchant"):
            monthly = g[g["month"].isin(ms)].groupby("month")["spend"].sum()
            expected = monthly.median() if len(monthly) else 0
            paid_now = d.loc[d["merchant"] == m, "spend"].sum()
            due = expected - paid_now
            when = self._next_on_day(int(g["date"].dt.day.median()), a)
            if due > 1 and when < nxt + pd.Timedelta(days=3):
                upcoming.append({"name": self._ml(m), "amount": r2(due), "date": date_short(when, L)})

        base = self.exp[self.exp["month"].isin(ms)]
        groceries_daily = base[(base["basket"] == FIXED) & ~base["recurring"]]["spend"].sum() / (max(len(ms), 1) * 30.4)
        grocery_reserve = groceries_daily * days_left
        ms12 = full_months(self.df, a, 12)
        occ_monthly = self.exp[self.exp["month"].isin(ms12) & (self.exp["basket"] == OCCASIONAL)]["spend"].sum() / max(len(ms12), 1)
        occ_spent = d.loc[d["basket"] == OCCASIONAL, "spend"].sum()
        occ_reserve = max(occ_monthly * cyc_days / 30.4 - occ_spent, 0)
        income_coming = sum(x["amount"] for x in upcoming_income)
        total_income = income + income_coming
        saved = -d.loc[d["kind"] == "saving", "amount"].sum()
        savings_left = max(self.savings_rate * total_income - saved, 0)
        fixed_spent = d.loc[d["basket"] == FIXED, "spend"].sum()
        flex_spent = d.loc[d["basket"].isin([EVERYDAY, UNCERTAIN]), "spend"].sum()
        up_total = sum(x["amount"] for x in upcoming)
        sts = total_income - fixed_spent - occ_spent - flex_spent - saved - up_total - grocery_reserve - occ_reserve - savings_left
        cap_step, bal = [], None
        if self.has_balance:  # never suggest spending money the account doesn't have
            bal = float(self.df["balance"].dropna().iloc[-1])
            limit = bal - up_total - grocery_reserve - occ_reserve - savings_left
            if limit < sts and sts > 0:
                cap_step = [{"label": t("sts_balance_cap", L, bal=self._m(bal)), "amount": -r2(sts - limit), "kind": "cap"}]
                sts = limit
        steps = [
            {"label": t("sts_income", L, date=date_short(start, L)), "amount": r2(income), "kind": "in"},
            *([{"label": t("sts_income_coming", L, names=", ".join(x["name"] for x in upcoming_income)), "amount": r2(income_coming), "kind": "in"}] if upcoming_income else []),
            {"label": t("sts_fixed_paid", L), "amount": -r2(fixed_spent), "kind": "out"},
            {"label": t("sts_bills_due", L), "amount": -r2(up_total), "kind": "out", "detail": upcoming},
            {"label": t("sts_groceries", L, n=days_left), "amount": -r2(grocery_reserve), "kind": "reserve"},
            {"label": t("sts_occasional", L), "amount": -r2(occ_spent + occ_reserve), "kind": "reserve", "detail_text": t("sts_occasional_detail", L, amount=self._m(occ_monthly))},
            {"label": t("sts_savings", L, pct=pct(int(self.savings_rate * 100), L)), "amount": -r2(saved + savings_left), "kind": "save"},
            {"label": t("sts_everyday", L), "amount": -r2(flex_spent), "kind": "out"},
            *cap_step,
        ]
        res = {"as_of": date_long(a, L), "next_payday": date_short(nxt, L), "days_left": days_left, "payday": pay,
               "safe_to_spend": r2(sts), "per_day": r2(max(sts, 0) / days_left), "per_week": r2(min(max(sts, 0), max(sts, 0) / days_left * 7)),
               "status": "comfortable" if sts > 15 * days_left else ("tight" if sts > 0 else "over"),
               "steps": steps, "upcoming_bills": upcoming, "savings_rate": self.savings_rate,
               "method": t("sts_method", L), "limits": [t("sts_limit_data", L, date=date_long(a, L)), t("sts_limit_bills", L)]}
        if bal is not None:
            res["balance"] = r2(bal)
        return res

    def can_afford(self, amount: float):
        s = self.safe_to_spend()
        left = s["safe_to_spend"] - amount
        return {"amount": r2(amount), "safe_to_spend": s["safe_to_spend"], "left_after": r2(left), "days_left": s["days_left"],
                "per_day_after": r2(max(left, 0) / s["days_left"]), "per_day_now": s["per_day"],
                "verdict": "yes" if left > 10 * s["days_left"] else ("tight" if left >= 0 else "no"), "next_payday": s["next_payday"]}

    # ---------- what-if & saving
    def what_if(self, target: str, reduce_pct: float = 20, goal_amount: float | None = None):
        ms = full_months(self.df, self.as_of, 3)
        base = self.exp[self.exp["month"].isin(ms)]
        reduce_pct = float(min(max(reduce_pct, 0), 100))
        if target in BASKET_IDS:
            sel, label = base[base["basket"] == target], basket_meta(target, self.lang)["name"]
        else:
            sel = self._filter(base, group=target)
            ids = groups_matching(target)
            label = self._g(ids[0]) if ids else target
            if sel.empty:
                sel = self._filter(base, merchant=target)
        n = max(len(ms), 1)
        monthly = sel["spend"].sum() / n
        save_m = monthly * reduce_pct / 100
        res = {"target": label, "target_id": target, "reduce_pct": reduce_pct, "baseline_months": ms, "current_monthly": r2(monthly),
               "purchases_per_month": round(len(sel) / n, 1), "monthly_saving": r2(save_m), "yearly_saving": r2(save_m * 12),
               "five_year_saving": r2(save_m * 60), "new_monthly": r2(monthly - save_m)}
        if len(sel):
            res["avg_purchase"] = r2(sel["spend"].mean())
            res["fewer_purchases_per_month"] = round(len(sel) / n * reduce_pct / 100, 1)
        if goal_amount:
            res["goal_amount"] = r2(goal_amount)
            res["months_to_goal"] = None if save_m <= 0 else int(np.ceil(float(goal_amount) / save_m))
        if monthly == 0:
            res["note"] = t("what_if_none", self.lang, target=target, n=len(ms))
        return res

    def safe_to_save(self):
        ms = full_months(self.df, self.as_of, 6)
        d = self.df[self.df["month"].isin(ms)]
        left = np.array([d[(d["month"] == m) & (d["kind"] == "income")]["amount"].sum() - d[d["month"] == m]["spend"].sum() for m in ms] or [0.0])
        saved = -d.loc[d["kind"] == "saving", "amount"].sum() / max(len(ms), 1)
        safe = max(np.percentile(left, 25), 0)
        return {"months": ms, "avg_leftover_before_savings": r2(left.mean()), "weak_month_leftover": r2(np.percentile(left, 25)),
                "already_saving_monthly": r2(saved), "suggested_monthly_saving": r2(np.floor(safe / 10) * 10), "method": t("save_method", self.lang)}

    # ---------- behaviour & pedagogy
    def payday_cycle(self):
        pay = self.payday()
        if not pay:
            return {"available": False, "note": t("payday_none", self.lang)}
        ms = full_months(self.df, self.as_of, 3)
        flex = self.exp[self.exp["month"].isin(ms) & self.exp["basket"].isin([EVERYDAY, UNCERTAIN])]
        week = (((flex["date"].dt.day - pay["day"]) % 30) // 7).clip(upper=3)
        weeks = flex.groupby(week)["spend"].sum()
        tot = weeks.sum() or 1
        share = [round(weeks.get(i, 0) / tot * 100) for i in range(4)]
        months = []
        for m in ms:
            x = self.df[self.df["month"] == m]
            inc = x.loc[x["kind"] == "income", "amount"].sum()
            out = x["spend"].sum() - x.loc[x["kind"] == "saving", "amount"].sum()
            months.append({"month": MONTHS[self.lang][pd.Period(m).month - 1], "income": r2(inc), "out": r2(out), "gap": r2(inc - out)})
        small = self.exp[self.exp["month"].isin(ms) & (self.exp["basket"] == EVERYDAY) & (self.exp["spend"] < 15)]
        n = max(len(ms), 1)
        return {"available": True, "payday": pay, "everyday_share_by_week": share, "first_week_share": share[0], "even_pace_share": 25,
                "months": months, "small_purchases_per_month": round(len(small) / n), "small_purchases_monthly_total": r2(small["spend"].sum() / n)}

    def _subs(self):
        s = self.exp[self.exp["recurring"] & (self.exp["basket"] == EVERYDAY)].groupby("merchant")["spend"].median()
        s.index = [self._ml(m) for m in s.index]
        return s

    def spender_profile(self):
        L = self.lang
        ms = full_months(self.df, self.as_of, 3)
        n = max(len(ms), 1)
        d = self.df[self.df["month"].isin(ms)]
        flex = d[d["basket"] == EVERYDAY]
        income = d.loc[d["kind"] == "income", "amount"].sum() / n
        weekend = flex[flex["date"].dt.weekday >= 4]["spend"].sum() / max(flex["spend"].sum(), 1)
        small = flex[flex["spend"] < 15]
        subs = self._subs()
        pc = self.payday_cycle()
        fw = pc.get("first_week_share", 25)
        saved = -d.loc[d["kind"] == "saving", "amount"].sum() / n
        mk = lambda tid, key, score, **kw: {"id": tid, "name": t(f"tr_{key}", L), "score": score, "evidence": t(f"tr_{key}_ev", L, **kw), "tip": t(f"tr_{key}_tip", L)}
        traits = [
            mk("sprinter", "sprinter", (fw - 25) / 10, p=pct(fw, L)),
            mk("sipper", "sipper", (len(small) / n - 25) / 20, n=round(len(small) / n), amount=self._m(small["spend"].sum() / n)),
            mk("social", "social", (weekend - 0.43) / 0.15, p=pct(round(weekend * 100), L)),
            mk("collector", "collector", (len(subs) - 2.5) / 1.5, n=len(subs), names=", ".join(subs.index[:5]), amount=self._m(subs.sum())),
            mk("planner", "planner", (saved / income - 0.05) / 0.05 if income > 0 else -1, amount=self._m(saved), p=pct(round(saved / income * 100) if income else 0, L)),
        ]
        flex_share = flex["spend"].sum() / n / income if income > 0 else 0
        for tr in traits:
            if tr["id"] in ("sprinter", "sipper", "social") and flex_share < 0.15:
                tr["score"] *= 0.3  # a pattern only matters if the money involved does
            tr["score"] = round(float(np.clip(tr["score"], -1, 3)), 2)
        traits.sort(key=lambda x: -x["score"])
        primary = traits[0] if traits[0]["score"] > 0 else mk("balanced", "balanced", 0)
        return {"primary": primary, "traits": [x for x in traits if x["score"] > 0][:3], "months": ms,
                "everyday_share_of_income": None if income <= 0 else round(flex["spend"].sum() / n / income * 100), "note": t("profile_note", L)}

    def benchmark(self):
        """Spending structure vs Statistics Finland Household Budget Survey 2022."""
        L = self.lang
        ms = full_months(self.df, self.as_of, 3)
        d = self.exp[self.exp["month"].isin(ms)]
        tot = d["spend"].sum() or 1
        food = d[d["group"] == "Groceries"]["spend"].sum() / tot * 100
        housing = d[d["group"].isin(["Housing", "Energy & water"])]["spend"].sum() / tot * 100
        return {"source": t("bm_source", L), "url": "https://stat.fi/en/publication/clmyi6vct7jjp0cutgh4ngdsb",
                "rows": [{"label": t("bm_food", L), "you": round(food), "low_income_households": 18, "high_income_households": 12},
                         {"label": t("bm_housing", L), "you": round(housing), "low_income_households": 39, "high_income_households": None}],
                "caveat": t("bm_caveat", L)}

    def peer_benchmark(self):
        """You vs. S-Bank customers your age (medians from peers.py over the same 3 months)."""
        import peers as P
        L = self.lang
        band = P.band_of(self.age)
        ref = (self.peers or {}).get("bands", {}).get(band) if band else None
        if not ref:
            return {"available": False}
        me = P.metrics(self.df.assign(customer_id="me"), self.peers["months"]).iloc[0]
        rows = [{"id": k, "label": t(f"peer_{k}", L), "you": None if pd.isna(me[k]) else round(float(me[k])), "peers": round(ref[k]), "unit": "%"}
                for k in ("everyday_share", "fixed_share", "saving_rate")]
        for g in ("Restaurants & takeaway", "Coffee & snacks", "Bars & nightlife", "Entertainment", "Shopping", "Taxis"):
            if ref.get(g, 0) > 0 or me[g] > 0:
                rows.append({"id": g, "label": self._g(g), "you": r2(me[g]), "peers": r2(ref[g]), "unit": "€"})
        return {"available": True, "band": band, "title": t("peer_band", L, band=band), "n": ref["n"],
                "note": t("peer_n", L, n=ref["n"]), "rows": rows}

    def insights(self):
        L = self.lang
        out = []
        coffee = self.what_if("Coffee & snacks", 50)
        if coffee["current_monthly"] > 20:
            out.append({"id": "coffee", "tone": "learn", "title": t("in_coffee_t", L, amount=money(coffee["current_monthly"], L, 0)),
                        "body": t("in_coffee_b", L, n=round(coffee["purchases_per_month"]), yearly=money(coffee["yearly_saving"], L, 0)), "ask": t("in_coffee_q", L)})
        pc = self.payday_cycle()
        if pc.get("available") and pc["first_week_share"] >= 35:
            out.append({"id": "payday", "tone": "pattern", "title": t("in_payday_t", L), "body": t("in_payday_b", L, p=pct(pc["first_week_share"], L)), "ask": t("in_payday_q", L)})
        ms = full_months(self.df, self.as_of, 2)
        if len(ms) == 2:
            c = self.compare(ms[0], ms[1])
            up = [r for r in c["rows"] if r["change"] > 25 and r["a"] >= 30 and r["change_pct"] and r["change_pct"] >= 20]
            if up:
                r = up[0]
                out.append({"id": "up", "tone": "change", "title": t("in_up_t", L, label=r["label"], p=pct(r["change_pct"], L)),
                            "body": t("in_up_b", L, a=money(r["a"], L, 0), b=money(r["b"], L, 0), pa=cap(c["period_a"]), pb=cap(c["period_b"])), "ask": t("in_up_q", L)})
        prof = self.spender_profile()
        col = next((x for x in prof["traits"] if x["id"] == "collector"), None)
        if col:
            out.append({"id": "subs", "tone": "learn", "title": t("in_subs_t", L), "body": col["evidence"], "ask": t("in_subs_q", L)})
        u = self.uncertain()
        if u:
            out.append({"id": "uncertain", "tone": "action", "title": t("in_unc_t1", L) if len(u) == 1 else t("in_unc_t", L, n=len(u)),
                        "body": t("in_unc_b", L), "ask": None, "goto": "spending"})
        return out

    def advice(self):
        """Vetted, rule-based recommendations ranked by priority. The coach may only recommend these."""
        L = self.lang
        out = []
        pc = self.payday_cycle()
        b = self.baskets()
        sts = self.safe_to_spend()
        save = self.safe_to_save()
        everyday = next(x for x in b["baskets"] if x["id"] == EVERYDAY)
        fixed = next(x for x in b["baskets"] if x["id"] == FIXED)
        add = lambda key, prio, w=None, a=None: out.append({"id": key, "priority": prio, "title": t(f"ad_{key}_t", L), "why": t(f"ad_{key}_w", L, **(w or {})), "action": t(f"ad_{key}_a", L, **(a or {}))})

        short = [m for m in pc.get("months", []) if m["gap"] < 0]
        if len(short) >= 2 and everyday["groups"]:
            g = everyday["groups"][0]
            add("overspend", 1, {"months": ", ".join(m["month"] for m in short)}, {"group": g["label"], "amount": self._m(g["monthly_avg"])})
        if save["already_saving_monthly"] <= 0:
            add("buffer", 2, a={"amount": self._m(save["suggested_monthly_saving"] if save["suggested_monthly_saving"] > 0 else 10)})
        if pc.get("available") and pc["first_week_share"] >= 35 and sts["safe_to_spend"] > 0:
            add("weekly", 3, {"p": pct(pc["first_week_share"], L)}, {"amount": self._m(sts["per_week"])})
        ms12 = full_months(self.df, self.as_of, 12)
        occ = self.exp[self.exp["month"].isin(ms12) & (self.exp["basket"] == OCCASIONAL)]["spend"].sum() / max(len(ms12), 1)
        if occ >= 10:
            add("irregular", 4, {"amount": self._m(occ)}, {"amount": self._m(np.ceil(occ / 5) * 5)})
        subs = self._subs()
        if len(subs) >= 3:
            add("subs", 5, {"names": ", ".join(subs.index[:5]), "amount": self._m(subs.sum())})
        small = [g for g in everyday["groups"] if g["id"] in ("Coffee & snacks", "Restaurants & takeaway", "Bars & nightlife", "Taxis")]
        if small and small[0]["monthly_avg"] >= 30:
            g = small[0]
            w = self.what_if(g["id"], 50)
            add("habit", 6, {"group": g["label"], "n": round(w["purchases_per_month"]), "amount": self._m(g["monthly_avg"])}, {"yearly": self._m(w["yearly_saving"])})
        if save["already_saving_monthly"] > 0:
            add("target", 7, {"amount": self._m(save["already_saving_monthly"])}, {"amount": self._m(np.ceil(fixed["monthly_avg"] / 50) * 50)})
        out.sort(key=lambda x: x["priority"])
        return {"items": out[:4]}
