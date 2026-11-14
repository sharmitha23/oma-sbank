"""Classification rules: transaction -> spending group -> basket.

Keywords (FI / SV / EN) are matched lower-case against merchant + category + description, so
the rules work whether the dataset has a category column, only merchant names, or both.
Group ids are English and stable; display names live in i18n.py.
"""

FIXED, OCCASIONAL, EVERYDAY, UNCERTAIN = "fixed", "occasional", "everyday", "uncertain"
BASKET_IDS = [FIXED, OCCASIONAL, EVERYDAY, UNCERTAIN]

# (group id, default basket, keywords). First match wins.
# "fixed_if_recurring": fixed when it repeats monthly (e.g. a travel pass), otherwise everyday.
GROUPS = [
    ("Savings & transfers", "transfer", ["oma tili", "own account", "säästö", "saasto", "savings", "nordnet", "rahasto", "sijoitus", "siirto omalle", "eget konto", "sparkonto", "överföring"]),
    ("Housing", FIXED, ["vuokra", "rent", "hoas", "sato", "lumo", "kojamo", "vastike", "asunto", "housing", "tyyni", "hyra", "bolag"]),
    ("Energy & water", FIXED, ["helen", "fortum", "oomi", "vattenfall", "elenia", "sähkö", "sahko", "electricity", "vesi", "water", "energy", "energia", "elräkning", "vatten"]),
    ("Phone & internet", FIXED, ["elisa", "dna", "telia", "moi mobiili", "internet", "puhelin", "mobile", "telefon"]),
    ("Insurance", FIXED, ["vakuutus", "insurance", "lähitapiola", "lahitapiola", "pohjola", "fennia", "turva", "if vahinko", "försäkring"]),
    ("Loans", FIXED, ["laina", "loan", "lyhennys", "opintolaina", "lån", "amortering"]),
    ("Childcare", FIXED, ["varhaiskasvatus", "päiväkoti", "paivakoti", "daycare", "childcare", "dagvård", "daghem"]),
    ("Public transport", "fixed_if_recurring", ["hsl", "nysse", "föli", "foli", "public transport", "joukkoliikenne", "kollektivtrafik"]),
    ("Coffee & snacks", EVERYDAY, ["robert's coffee", "roberts coffee", "espresso house", "starbucks", "café", "cafe", "kahvila", "coffee", "r-kioski", "fazer", "arabica", "kiosk", "kaffe"]),
    ("Restaurants & takeaway", EVERYDAY, ["wolt", "foodora", "ravintola", "restaurant", "mcdonald", "hesburger", "rax", "pizza", "sushi", "kebab", "burger", "subway", "takeaway", "lounas", "restaurang"]),
    ("Bars & nightlife", EVERYDAY, ["baari", " bar", "pub", "night", "olut", "yökerho", "nattklubb"]),
    ("Groceries", FIXED, ["s-market", "prisma", "alepa", "sale ", "k-market", "k-supermarket", "k-citymarket", "lidl", "grocer", "ruoka", "groceries", "food store", "market", "livsmedel", "matbutik"]),
    ("Health & pharmacy", OCCASIONAL, ["apteekki", "pharmacy", "terveystalo", "mehiläinen", "mehilainen", "pihlajalinna", "hammas", "dentist", "lääkäri", "laakari", "health", "terveys", "optikko", "specsavers", "apotek", "tandläkare", "läkare", "hälsa"]),
    ("Repairs & appliances", OCCASIONAL, ["pesukone", "washing machine", "jääkaappi", "jaakaappi", "fridge", "korjaus", "repair", "huolto", "autokorjaamo", "katsastus", "plumber", "putkimies", "tvättmaskin", "reparation", "kylskåp"]),
    ("Taxis", EVERYDAY, ["taxi", "taksi", "uber", "bolt", "yango", "kovanen"]),
    ("Sports & wellbeing", EVERYDAY, ["gym", "kuntosali", "elixia", "fressi", "unisport", "sats", "liikunta", " sport", "urheilu", "motion"]),
    ("Subscriptions & entertainment", EVERYDAY, ["netflix", "spotify", "hbo", "max.com", "disney", "viaplay", "youtube", "apple.com", "steam", "playstation", "finnkino", "kino", "entertainment", "viihde", "ruutu", "nöje"]),
    ("Travel", EVERYDAY, ["finnair", "vr ", "vr.fi", "matkahuolto", "booking", "airbnb", "tallink", "viking line", "norwegian", "ryanair", "hotel", "hotelli", "travel", "matka", "resa"]),
    ("Shopping", EVERYDAY, ["zalando", "h&m", "stockmann", "amazon", "clas ohlson", "verkkokauppa", "gigantti", "power", "ikea", "jysk", "lindex", "kappahl", "tokmanni", "shopping", "vaate", "clothing", "temu", "shein", "kläder"]),
    ("Cash withdrawals", UNCERTAIN, ["otto", "atm", "nosto", "cash", "uttag", "kontant"]),
]

# Stores that sell both essentials and extras: uncertain unless the description says otherwise
# (an appliance purchase is caught by "Repairs & appliances" first).
MIXED_MERCHANTS = ["gigantti", "power", "verkkokauppa", "tokmanni", "clas ohlson", "ikea"]

INCOME_GROUPS = [
    ("Salary", ["palkka", "salary", "wage", "payroll", "lön"]),
    ("Benefits (Kela)", ["kela", "benefit", "tuki", "etuus", "fpa", "förmån"]),
    ("Refunds", ["refund", "palautus", "hyvitys", "återbetalning"]),
]


def match_group(text: str):
    """-> (group id, basket, (reason code, keyword))"""
    t = f" {text.lower()} "
    for group, basket, kws in GROUPS:
        kw = next((k for k in kws if k in t), None)
        if kw:
            if group == "Shopping" and any(m in t for m in MIXED_MERCHANTS):
                return group, UNCERTAIN, ("mixed", None)
            return group, basket, ("match", kw.strip())
    return "Other", UNCERTAIN, ("none", None)


def match_income(text: str):
    t = text.lower()
    for group, kws in INCOME_GROUPS:
        if any(k in t for k in kws):
            return group
    return "Other income"


# ---------------------------------------------------------------------------------------------
# S-Pankki Junction dataset: no merchant names, so classify by transaction_type + MCC + category.
# Vectorised: 3.6M rows classify in seconds.
# ---------------------------------------------------------------------------------------------
TYPE_RULES = {  # transaction_type -> (group, basket, kind)
    "housing_payment": ("Housing", FIXED, "expense"),
    "utilities_payment": ("Utility bills", FIXED, "expense"),
    "salary": ("Salary", "income", "income"),
    "other_income": ("Other income", "income", "income"),
    "investment_deposit": ("Savings & investments", "saving", "saving"),
    "investment_withdrawal": ("Savings & investments", "saving", "saving"),
    "salary_sweep": ("Own transfers", "transfer", "transfer"),  # moves salary to another own account: not spending, not saving
}
MCC_GROUP = {
    5411: "Groceries", 5499: "Groceries", 5422: "Groceries", 5451: "Groceries",
    5812: "Restaurants & takeaway", 5814: "Coffee & snacks", 5813: "Bars & nightlife",
    4121: "Taxis", 4111: "Public transport", 5541: "Car: fuel & parking", 5542: "Car: fuel & parking", 7523: "Car: fuel & parking",
    7922: "Entertainment", 7999: "Entertainment", 7832: "Entertainment", 7991: "Entertainment", 7996: "Entertainment",
    5912: "Health & pharmacy", 8011: "Health & pharmacy", 8021: "Health & pharmacy", 8099: "Health & pharmacy",
    5200: "Home & hardware", 5251: "Home & hardware",
    5712: "Electronics & furniture", 5732: "Electronics & furniture", 5734: "Electronics & furniture",
    5941: "Shopping", 5651: "Shopping", 5691: "Shopping", 5999: "Shopping", 5942: "Shopping", 5945: "Shopping",
    4722: "Travel", 7011: "Travel", 4511: "Travel", 7512: "Travel",
}
CATEGORY_FALLBACK = {  # purchase without MCC
    "Groceries": "Groceries", "Restaurants": "Restaurants & takeaway", "Transportation": "Transport (other)",
    "Entertainment": "Entertainment", "Health": "Health & pharmacy", "Home & Tech": "Electronics & furniture",
    "Lifestyle": "Shopping", "Travel": "Travel", "Housing": "Housing", "Utilities": "Utility bills",
}
GROUP_BASKET = {
    "Groceries": FIXED, "Housing": FIXED, "Utility bills": FIXED, "Public transport": FIXED, "Car: fuel & parking": FIXED, "Transport (other)": FIXED,
    "Health & pharmacy": OCCASIONAL, "Home & hardware": OCCASIONAL,
}
BIG_PURCHASE = 300  # an electronics/furniture purchase this large could be a replacement (essential) or an extra: ask


def classify_sbank(df):
    """-> group, basket, kind, reason (tuples) as lists aligned with df."""
    import numpy as np
    import pandas as pd
    ttype = df["ttype"].astype(str)
    mcc = df["mcc"]
    by_mcc = mcc.map(MCC_GROUP)
    by_cat = df["category"].astype(str).map(CATEGORY_FALLBACK)
    group = by_mcc.fillna(by_cat).fillna("Other")
    basket = group.map(GROUP_BASKET).fillna(EVERYDAY)
    kind = pd.Series("expense", index=df.index)
    big = (group == "Electronics & furniture") & (-df["amount"] >= BIG_PURCHASE)
    basket = basket.where(~big, UNCERTAIN)
    for t_, (g, b, k) in TYPE_RULES.items():
        sel = ttype == t_
        group = group.where(~sel, g)
        basket = basket.where(~sel, b)
        kind = kind.where(~sel, k)
    kind = kind.where(~((kind == "expense") & (df["amount"] > 0)), "income")  # refunds
    basket = basket.where(kind != "income", "income")
    group = group.where(~((kind == "income") & ~ttype.isin(["salary", "other_income"])), "Refunds")
    reason = np.where(big, "big", np.where(ttype != "purchase", "type", np.where(mcc.notna(), "mcc", "category")))
    return group.tolist(), basket.tolist(), kind.tolist(), reason.tolist()
