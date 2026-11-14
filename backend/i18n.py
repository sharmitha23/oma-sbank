"""All user-facing backend text in Finnish (default), Swedish and English, plus number/date formats.

T[key] = (en, fi, sv). Templates avoid Finnish case endings on inserted words by using
"Label: value" patterns, so inserted names never need inflecting.
"""
import re

LANGS = ("fi", "sv", "en")
DEFAULT = "fi"
_IDX = {"en": 0, "fi": 1, "sv": 2}


def norm(lang):
    return lang if lang in LANGS else DEFAULT


def t(key, lang, **kw):
    return T[key][_IDX[norm(lang)]].format(**kw)


def pick(triple, lang):
    return triple[_IDX[norm(lang)]]


# ------------------------------------------------------------------ formats
def money(x, lang, decimals=None):
    x = float(x)
    a = abs(x)
    d = decimals if decimals is not None else (0 if a >= 100 else 2)
    s = f"{a:,.{d}f}"
    if d == 2 and s.endswith(".00"):
        s = s[:-3]
    sign = "−" if x < 0 else ""
    if norm(lang) == "en":
        return f"{sign}€{s}"
    s = s.replace(",", " ").replace(".", ",")
    return f"{sign}{s} €"


def pct(x, lang):
    return f"{x}%" if norm(lang) == "en" else f"{x} %"


MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    "fi": ["tammikuu", "helmikuu", "maaliskuu", "huhtikuu", "toukokuu", "kesäkuu", "heinäkuu", "elokuu", "syyskuu", "lokakuu", "marraskuu", "joulukuu"],
    "sv": ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"],
}
MONTHS_SHORT = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "fi": ["tammi", "helmi", "maalis", "huhti", "touko", "kesä", "heinä", "elo", "syys", "loka", "marras", "joulu"],
    "sv": ["jan", "feb", "mar", "apr", "maj", "jun", "jul", "aug", "sep", "okt", "nov", "dec"],
}
WEEKDAYS = {"en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "fi": ["ma", "ti", "ke", "to", "pe", "la", "su"],
            "sv": ["mån", "tis", "ons", "tors", "fre", "lör", "sön"]}


def month_year(ts, lang):
    return f"{MONTHS[norm(lang)][ts.month - 1]} {ts.year}"


def date_short(ts, lang):
    return f"{ts.day} {MONTHS_SHORT['en'][ts.month - 1]}" if norm(lang) == "en" else f"{ts.day}.{ts.month}."


def date_long(ts, lang):
    return f"{ts.day} {MONTHS_SHORT['en'][ts.month - 1]} {ts.year}" if norm(lang) == "en" else f"{ts.day}.{ts.month}.{ts.year}"


def cap(s):
    return s[:1].upper() + s[1:]


PLURALS = {"purchase": (("purchase", "purchases"), ("osto", "ostoa"), ("köp", "köp")),
           "month": (("month", "months"), ("kuukausi", "kuukautta"), ("månad", "månader")),
           "transaction": (("transaction", "transactions"), ("tapahtuma", "tapahtumaa"), ("transaktion", "transaktioner"))}


def plural(n, word, lang):
    n = round(n)
    forms = PLURALS[word][_IDX[norm(lang)]]
    return f"{n} {forms[0] if n == 1 else forms[1]}"


def parse_amounts(text, lang):
    """Every euro amount written in text, in either '€1,234.5' or '1 234,50 €' style."""
    out = []
    num = r"(\d{1,3}(?:[   ,.]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
    for m in re.finditer(rf"€\s?{num}|{num}\s?(?:€|eur\b|euroa|euro\b|euron)", text, re.I):
        out.append(_to_float(m.group(1) or m.group(2), lang))
    return [x for x in out if x is not None]


def _to_float(s, lang):
    s = re.sub(r"[   ]", "", s)
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
    elif "," in s:
        dec = "," if not re.search(r",\d{3}$", s) or norm(lang) != "en" else None
    elif "." in s:
        dec = "." if not re.search(r"\.\d{3}$", s) or norm(lang) == "en" else None
    else:
        dec = None
    if dec:
        th = "." if dec == "," else ","
        s = s.replace(th, "").replace(dec, ".")
    else:
        s = s.replace(",", "").replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


# ------------------------------------------------------------------ labels
GROUP_LABELS = {
    "Housing": ("Housing", "Asuminen", "Boende"),
    "Energy & water": ("Energy & water", "Sähkö ja vesi", "El och vatten"),
    "Phone & internet": ("Phone & internet", "Puhelin ja netti", "Telefon och internet"),
    "Insurance": ("Insurance", "Vakuutukset", "Försäkringar"),
    "Loans": ("Loans", "Lainat", "Lån"),
    "Childcare": ("Childcare", "Varhaiskasvatus", "Dagvård"),
    "Public transport": ("Public transport", "Joukkoliikenne", "Kollektivtrafik"),
    "Coffee & snacks": ("Cafés & fast food", "Kahvilat ja pikaruoka", "Kaféer och snabbmat"),
    "Restaurants & takeaway": ("Restaurants & takeaway", "Ravintolat ja noutoruoka", "Restauranger och hämtmat"),
    "Bars & nightlife": ("Bars & nightlife", "Baarit ja yöelämä", "Barer och nöjesliv"),
    "Groceries": ("Groceries", "Ruokaostokset", "Livsmedel"),
    "Health & pharmacy": ("Health & pharmacy", "Terveys ja apteekki", "Hälsa och apotek"),
    "Repairs & appliances": ("Repairs & appliances", "Korjaukset ja kodinkoneet", "Reparationer och hushållsapparater"),
    "Taxis": ("Taxis", "Taksit", "Taxi"),
    "Sports & wellbeing": ("Sports & wellbeing", "Liikunta ja hyvinvointi", "Motion och välmående"),
    "Subscriptions & entertainment": ("Subscriptions & entertainment", "Tilaukset ja viihde", "Prenumerationer och nöje"),
    "Travel": ("Travel", "Matkat", "Resor"),
    "Shopping": ("Shopping", "Ostokset", "Shopping"),
    "Cash withdrawals": ("Cash withdrawals", "Käteisnostot", "Kontantuttag"),
    "Other": ("Other", "Muut", "Övrigt"),
    "Savings & transfers": ("Savings & transfers", "Säästöt ja siirrot", "Sparande och överföringar"),
    "Salary": ("Salary", "Palkka", "Lön"),
    "Benefits (Kela)": ("Benefits (Kela)", "Kela-etuudet", "FPA-förmåner"),
    "Refunds": ("Refunds", "Palautukset", "Återbetalningar"),
    "Other income": ("Other income", "Muut tulot", "Övriga inkomster"),
    "Utility bills": ("Utility bills", "Kotitalouden laskut", "Hushållsräkningar"),
    "Car: fuel & parking": ("Fuel & parking", "Polttoaine ja pysäköinti", "Bränsle och parkering"),
    "Transport (other)": ("Other transport", "Muu liikkuminen", "Övriga resor"),
    "Entertainment": ("Entertainment & leisure", "Viihde ja vapaa-aika", "Nöje och fritid"),
    "Home & hardware": ("Home repairs & supplies", "Kodin korjaukset ja tarvikkeet", "Hemreparationer och förnödenheter"),
    "Electronics & furniture": ("Electronics & furniture", "Elektroniikka ja huonekalut", "Elektronik och möbler"),
    "Savings & investments": ("Savings & investments", "Säästöt ja sijoitukset", "Sparande och investeringar"),
    "Own transfers": ("Transfers to own accounts", "Siirrot omille tileille", "Överföringar till egna konton"),
}

MCC_LABELS = {
    5411: ("Grocery store", "Ruokakauppa", "Livsmedelsbutik"), 5499: ("Food store", "Elintarvikekauppa", "Matbutik"),
    5422: ("Meat shop", "Lihakauppa", "Köttbutik"), 5451: ("Dairy shop", "Maitokauppa", "Mejeributik"),
    5812: ("Restaurant", "Ravintola", "Restaurang"), 5814: ("Café / fast food", "Kahvila / pikaruoka", "Kafé / snabbmat"),
    5813: ("Bar", "Baari", "Bar"), 4121: ("Taxi", "Taksi", "Taxi"), 4111: ("Public transport", "Joukkoliikenne", "Kollektivtrafik"),
    5541: ("Fuel station", "Huoltoasema", "Bensinstation"), 5542: ("Fuel pump", "Polttoaineautomaatti", "Bränsleautomat"),
    7523: ("Parking", "Pysäköinti", "Parkering"), 7922: ("Theatre & events", "Teatteri ja tapahtumat", "Teater och evenemang"),
    7999: ("Recreation", "Vapaa-aika", "Fritid"), 7832: ("Cinema", "Elokuvateatteri", "Biograf"),
    7991: ("Attraction", "Nähtävyys", "Sevärdhet"), 7996: ("Amusement park", "Huvipuisto", "Nöjespark"),
    5912: ("Pharmacy", "Apteekki", "Apotek"), 8011: ("Doctor", "Lääkäri", "Läkare"), 8021: ("Dentist", "Hammaslääkäri", "Tandläkare"),
    8099: ("Health service", "Terveyspalvelu", "Hälsotjänst"), 5200: ("Home supply store", "Rautakauppa", "Byggvaruhus"),
    5251: ("Hardware store", "Työkalukauppa", "Järnhandel"), 5712: ("Furniture store", "Huonekalukauppa", "Möbelaffär"),
    5732: ("Electronics store", "Elektroniikkakauppa", "Elektronikbutik"), 5734: ("Software store", "Ohjelmistokauppa", "Mjukvarubutik"),
    5941: ("Sports shop", "Urheilukauppa", "Sportbutik"), 5651: ("Clothing store", "Vaatekauppa", "Klädbutik"),
    5691: ("Clothing store", "Vaatekauppa", "Klädbutik"), 5999: ("Specialty shop", "Erikoisliike", "Specialbutik"),
    5942: ("Bookshop", "Kirjakauppa", "Bokhandel"), 5945: ("Toy & game shop", "Lelukauppa", "Leksaksaffär"),
    4722: ("Travel agency", "Matkatoimisto", "Resebyrå"), 7011: ("Hotel", "Hotelli", "Hotell"),
    4511: ("Airline", "Lentoyhtiö", "Flygbolag"), 7512: ("Car rental", "Autovuokraamo", "Biluthyrning"),
}
TYPE_LABELS = {
    "housing_payment": ("Rent / housing payment", "Vuokra / asumismaksu", "Hyra / boendekostnad"),
    "utilities_payment": ("Utility bills", "Kotitalouden laskut", "Hushållsräkningar"),
    "salary": ("Salary", "Palkka", "Lön"), "other_income": ("Other income", "Muut tulot", "Övriga inkomster"),
    "investment_deposit": ("Investment deposit", "Sijoitustalletus", "Investeringsinsättning"),
    "investment_withdrawal": ("Investment withdrawal", "Sijoitusnosto", "Investeringsuttag"),
    "salary_sweep": ("Transfer to own account", "Siirto omalle tilille", "Överföring till eget konto"),
}
CATEGORY_LABELS = {
    "Groceries": ("Groceries", "Ruokaostokset", "Livsmedel"), "Restaurants": ("Restaurants", "Ravintolat", "Restauranger"),
    "Transportation": ("Transport", "Liikkuminen", "Transport"), "Entertainment": ("Entertainment", "Viihde", "Nöje"),
    "Health": ("Health", "Terveys", "Hälsa"), "Home & Tech": ("Home & tech", "Koti ja tekniikka", "Hem och teknik"),
    "Lifestyle": ("Lifestyle", "Elämäntyyli", "Livsstil"), "Travel": ("Travel", "Matkat", "Resor"),
}


def merchant_label(key, lang, mcc=None):
    """Readable name for a merchant key: 'MRC-GRO-0010' -> 'Ruokakauppa #0010', 'TYPE:salary' -> 'Palkka'."""
    key = str(key)
    if key.startswith("TYPE:"):
        t_ = key[5:]
        return pick(TYPE_LABELS[t_], lang) if t_ in TYPE_LABELS else t_
    if key.startswith("CAT:"):
        c_ = key[4:]
        return pick(CATEGORY_LABELS[c_], lang) if c_ in CATEGORY_LABELS else c_
    if key.startswith("MRC-"):
        base = pick(MCC_LABELS[int(mcc)], lang) if mcc is not None and int(mcc) in MCC_LABELS else key[4:7]
        return f"{base} #{key.rsplit('-', 1)[-1]}"
    return key


def group_label(g, lang):
    return pick(GROUP_LABELS[g], lang) if g in GROUP_LABELS else g


BASKET_TEXT = {
    "fixed": {
        "name": ("Fixed essentials", "Kiinteät pakolliset", "Fasta nödvändiga"),
        "short": ("Must-haves, every month", "Pakolliset, joka kuukausi", "Måsten, varje månad"),
        "explain": ("Bills you have to pay and that arrive like clockwork: rent, electricity, phone, insurance, groceries. They are predictable, so plan them first.",
                    "Menot, jotka on pakko maksaa ja jotka tulevat kuin kello: vuokra, sähkö, puhelin, vakuutukset, ruoka. Ne ovat ennustettavia, joten suunnittele ne ensin.",
                    "Räkningar som måste betalas och som kommer som på beställning: hyra, el, telefon, försäkringar, mat. De är förutsägbara, så planera dem först."),
    },
    "occasional": {
        "name": ("Occasional essentials", "Satunnaiset pakolliset", "Oregelbundna nödvändiga"),
        "short": ("Must-haves, now and then", "Pakolliset, silloin tällöin", "Måsten, då och då"),
        "explain": ("Necessary but irregular costs: a broken washing machine, the dentist, a car repair. Each one feels like a surprise, but over a year they're not. A small monthly reserve turns them from a crisis into a plan.",
                    "Välttämättömiä mutta epäsäännöllisiä menoja: rikkoutunut pesukone, hammaslääkäri, auton korjaus. Yksittäinen meno yllättää, mutta vuoden mittaan niitä tulee aina. Pieni kuukausittainen varaus tekee kriisistä suunnitelman.",
                    "Nödvändiga men oregelbundna kostnader: en trasig tvättmaskin, tandläkaren, en bilreparation. Var och en känns som en överraskning, men under ett år kommer de alltid. En liten månatlig reserv gör krisen till en plan."),
    },
    "everyday": {
        "name": ("Everyday spending", "Arjen kulutus", "Vardagsutgifter"),
        "short": ("Slips through your fingers", "Valuu sormien läpi", "Rinner mellan fingrarna"),
        "explain": ("Flexible, frequent purchases: coffees, takeaway, taxis, shopping, streaming. Each one is small; together they are often the biggest lever you control.",
                    "Joustavia, toistuvia ostoja: kahvit, noutoruoka, taksit, shoppailu, suoratoistopalvelut. Yksittäin pieniä, yhdessä usein suurin asia, johon voit itse vaikuttaa.",
                    "Flexibla, täta köp: kaffe, hämtmat, taxi, shopping, streaming. Vart och ett är litet, men tillsammans är de ofta det du själv kan påverka mest."),
    },
    "uncertain": {
        "name": ("Needs your call", "Luokittelematta", "Oklassificerat"),
        "short": ("OMA isn't sure", "OMA ei ole varma", "OMA är osäker"),
        "explain": ("OMA won't guess when it can't tell (cash withdrawals, mixed stores). Tell OMA where these belong and every number updates.",
                    "OMA ei arvaa, jos se ei ole varma (käteisnostot, sekakaupat). Kerro, mihin koriin nämä kuuluvat, niin kaikki luvut päivittyvät.",
                    "OMA gissar inte när den är osäker (kontantuttag, blandade butiker). Berätta var de hör hemma så uppdateras alla siffror."),
    },
}


def basket_meta(b, lang):
    return {k: pick(v, lang) for k, v in BASKET_TEXT[b].items()}


PERSONA_ABOUT = {
    "demo-aino": ("22, student in Helsinki, part-time job", "22, opiskelija Helsingissä, osa-aikatyö", "22, studerande i Helsingfors, deltidsjobb"),
    "demo-mikko": ("28, junior developer in Espoo", "28, juniorikehittäjä Espoossa", "28, juniorutvecklare i Esbo"),
    "demo-laura": ("34, nurse in Tampere, one child", "34, sairaanhoitaja Tampereella, yksi lapsi", "34, sjukskötare i Tammerfors, ett barn"),
}

# ------------------------------------------------------------------ text templates
T = {
    # periods
    "p_this_month": ("{month} so far (1–{d} {mon})", "{month} tähän mennessä (1.–{d}.{m}.)", "{month} hittills (1–{d}.{m}.)"),
    "p_this_week": ("this week so far", "tämä viikko tähän mennessä", "denna vecka hittills"),
    "p_last_week": ("last week", "viime viikko", "förra veckan"),
    "p_last_days": ("the last {n} days", "viimeiset {n} päivää", "de senaste {n} dagarna"),
    "p_last_months": ("the last {n} full months", "viimeiset {n} täyttä kuukautta", "de senaste {n} hela månaderna"),
    "p_ytd": ("{y} so far", "vuosi {y} tähän mennessä", "{y} hittills"),
    "p_first_days": ("first {n} days of {month}", "{month}, {n} ensimmäistä päivää", "första {n} dagarna i {month}"),
    "compare_note": ("Compared like-for-like: {a} vs {b}.", "Vertailtu samanpituisia jaksoja: {a} vs. {b}.", "Jämfört lika långa perioder: {a} mot {b}."),
    "all_spending": ("all spending", "kaikki menot", "alla utgifter"),
    "spending": ("Spending", "Menot", "Utgifter"),
    "others": ("{n} others", "{n} muuta", "{n} övriga"),
    # classification reasons
    "reason_match": ("Matched '{kw}'", "Tunnistettu: '{kw}'", "Identifierad: '{kw}'"),
    "reason_mixed": ("Store sells both essentials and extras", "Kauppa myy sekä välttämättömiä että muuta", "Butiken säljer både nödvändigt och annat"),
    "reason_none": ("No rule matched", "Ei tunnistettu", "Inte identifierad"),
    "reason_user": ("You classified this", "Sinä luokittelit tämän", "Du klassificerade detta"),
    "reason_recurring": (" · repeats monthly", " · toistuu kuukausittain", " · upprepas varje månad"),
    "reason_mcc": ("Merchant code {kw}", "Kauppiaskoodi {kw}", "Handlarkod {kw}"),
    "reason_type": ("Transaction type", "Tapahtumatyyppi", "Transaktionstyp"),
    "reason_category": ("Bank category", "Pankin kategoria", "Bankens kategori"),
    "reason_big": ("Large purchase: a replacement (must-have) or an extra?", "Iso ostos: välttämätön korvaava hankinta vai lisäostos?", "Stort köp: en nödvändig ersättning eller ett extraköp?"),
    "years": ("{n} y", "{n} v", "{n} år"),
    "sts_balance_cap": ("Limited by your balance ({bal}) after bills and reserves", "Rajattu tilisi saldon ({bal}) mukaan laskujen ja varausten jälkeen", "Begränsat av ditt saldo ({bal}) efter räkningar och reserver"),
    "peer_band": ("S-Bank customers aged {band}", "{band}-vuotiaat S-Pankin asiakkaat", "S-Bankens kunder i åldern {band}"),
    "peer_n": ("Median of {n} customers, last 3 full months.", "Mediaani {n} asiakkaasta, viimeiset 3 täyttä kuukautta.", "Median av {n} kunder, senaste 3 hela månaderna."),
    "peer_everyday_share": ("Everyday spending, % of income", "Arjen kulutus, % tuloista", "Vardagsutgifter, % av inkomsterna"),
    "peer_saving_rate": ("Saved or invested, % of income", "Säästetty tai sijoitettu, % tuloista", "Sparat eller investerat, % av inkomsterna"),
    "peer_fixed_share": ("Fixed essentials, % of income", "Kiinteät pakolliset, % tuloista", "Fasta nödvändiga, % av inkomsterna"),
    # safe to spend
    "sts_income": ("Income since payday ({date})", "Tulot palkkapäivästä alkaen ({date})", "Inkomster sedan lönedagen ({date})"),
    "sts_income_coming": ("Income still coming: {names}", "Vielä tulossa: {names}", "Inkomster som kommer: {names}"),
    "sts_fixed_paid": ("Fixed essentials already paid", "Jo maksetut kiinteät menot", "Redan betalda fasta utgifter"),
    "sts_bills_due": ("Bills still due before payday", "Laskut ennen palkkapäivää", "Räkningar före lönedagen"),
    "sts_groceries": ("Food & commuting for {n} days (your usual pace)", "Ruoka ja liikkuminen {n} päiväksi (tavallinen tahtisi)", "Mat och resor för {n} dagar (din vanliga takt)"),
    "sts_occasional": ("Occasional essentials (spent + reserve)", "Satunnaiset pakolliset (käytetty + varaus)", "Oregelbundna nödvändiga (använt + reserv)"),
    "sts_occasional_detail": ("You average {amount}/month on irregular must-haves (12 months).", "Satunnaisiin pakollisiin menee keskimäärin {amount}/kk (12 kk).", "Oregelbundna måsten kostar dig i snitt {amount}/mån (12 mån)."),
    "sts_savings": ("Savings: {pct} of income", "Säästöt: {pct} tuloista", "Sparande: {pct} av inkomsterna"),
    "sts_everyday": ("Everyday spending so far", "Arjen kulutus tähän mennessä", "Vardagsutgifter hittills"),
    "sts_method": ("Income in this pay cycle, minus bills paid and still due, a grocery and irregular-cost reserve based on your own history, your savings target and what you've already spent.",
                   "Tämän palkkajakson tulot, joista on vähennetty maksetut ja tulevat laskut, omaan historiaasi perustuva varaus ruokaan ja satunnaisiin menoihin, säästötavoitteesi sekä jo käytetty raha.",
                   "Inkomsterna denna löneperiod, minus betalda och kommande räkningar, en reserv för mat och oregelbundna kostnader baserad på din egen historik, ditt sparmål och det du redan har spenderat."),
    "sts_limit_data": ("Based on transactions up to {date}; not a live balance.", "Perustuu tapahtumiin {date} asti, ei reaaliaikaiseen saldoon.", "Baserat på transaktioner till och med {date}, inte ett realtidssaldo."),
    "sts_limit_bills": ("Upcoming bills are predicted from repeating payments; new or one-off bills aren't known.",
                        "Tulevat laskut ennustetaan toistuvista maksuista. Uusia tai kertaluonteisia laskuja OMA ei tiedä.",
                        "Kommande räkningar förutsägs utifrån återkommande betalningar. Nya eller engångsräkningar känner OMA inte till."),
    "what_if_none": ("No spending matched '{target}' in the last {n} months.", "Kohteelle '{target}' ei löytynyt menoja viimeisten {n} kuukauden ajalta.", "Inga utgifter hittades för '{target}' under de senaste {n} månaderna."),
    "save_method": ("Income minus spending for each recent full month; we suggest the amount you had left even in a weaker month (25th percentile).",
                    "Tulot miinus menot jokaiselta viime kuukaudelta. Ehdotus on summa, joka sinulle jäi heikompanakin kuukautena (25. persentiili).",
                    "Inkomster minus utgifter för varje hel månad nyligen. Förslaget är det belopp du hade kvar även en svagare månad (25:e percentilen)."),
    "payday_none": ("No regular income found, so pay cycles can't be analysed.", "Säännöllisiä tuloja ei löytynyt, joten palkkajaksoja ei voi analysoida.", "Inga regelbundna inkomster hittades, så löneperioder kan inte analyseras."),
    # spender profile
    "tr_sprinter": ("Payday Sprinter", "Palkkapäivän pikajuoksija", "Lönedagssprinter"),
    "tr_sprinter_ev": ("{p} of your everyday spending happens in the first week after payday (an even pace would be about 25%).",
                       "{p} arjen kulutuksestasi osuu palkkapäivää seuraavalle viikolle (tasaisella tahdilla noin 25 %).",
                       "{p} av dina vardagsutgifter sker veckan efter lönedagen (jämn takt vore ungefär 25 %)."),
    "tr_sprinter_tip": ("Try a weekly allowance: split your safe-to-spend into equal weeks.", "Kokeile viikkorahaa: jaa käytettävissä oleva raha tasan viikoille.", "Prova en veckopeng: dela upp dina fria pengar i lika stora veckor."),
    "tr_sipper": ("Small-Sips Spender", "Pienten ostosten kerääjä", "Småköpare"),
    "tr_sipper_ev": ("{n} purchases under 15 € a month, adding up to {amount}.", "{n} alle 15 euron ostoa kuukaudessa, yhteensä {amount}.", "{n} köp under 15 euro i månaden, totalt {amount}."),
    "tr_sipper_tip": ("Small buys are invisible one by one. Pick one habit to halve and watch the yearly number.", "Pienet ostot ovat yksitellen näkymättömiä. Valitse yksi tapa, jonka puolitat, ja katso vuosisummaa.", "Små köp syns inte ett och ett. Välj en vana att halvera och titta på årssumman."),
    "tr_social": ("Weekend Socialiser", "Viikonlopun seurustelija", "Helgsällskapare"),
    "tr_social_ev": ("{p} of everyday spending lands Friday–Sunday (3 of 7 days is 43%).", "{p} arjen kulutuksesta osuu perjantaista sunnuntaihin (3/7 päivää olisi 43 %).", "{p} av vardagsutgifterna sker fredag–söndag (3 av 7 dagar är 43 %)."),
    "tr_social_tip": ("Set a weekend budget on Friday morning, so Saturday-you doesn't decide alone.", "Päätä viikonlopun budjetti jo perjantaiaamuna, niin lauantai-sinun ei tarvitse päättää yksin.", "Bestäm helgbudgeten på fredagsmorgonen, så slipper lördags-du bestämma ensam."),
    "tr_collector": ("Subscription Collector", "Tilausten keräilijä", "Prenumerationssamlare"),
    "tr_collector_ev": ("{n} repeating extras ({names}) for {amount}/month.", "{n} toistuvaa lisämenoa ({names}), yhteensä {amount}/kk.", "{n} återkommande extrautgifter ({names}) för {amount}/mån."),
    "tr_collector_tip": ("Rotate: keep one streaming service at a time and switch monthly.", "Kierrätä: pidä yksi suoratoistopalvelu kerrallaan ja vaihda kuukausittain.", "Rotera: ha en streamingtjänst åt gången och byt varje månad."),
    "tr_planner": ("Steady Planner", "Vakaa suunnittelija", "Stabil planerare"),
    "tr_planner_ev": ("You move {amount}/month to savings ({p} of income).", "Siirrät säästöön {amount}/kk ({p} tuloistasi).", "Du för över {amount}/mån till sparande ({p} av inkomsterna)."),
    "tr_planner_tip": ("You've built the habit. Next step: give your savings a named goal.", "Tapa on jo olemassa. Seuraava askel: anna säästöillesi nimetty tavoite.", "Vanan har du redan. Nästa steg: ge ditt sparande ett namngivet mål."),
    "tr_balanced": ("Balanced Spender", "Tasapainoinen kuluttaja", "Balanserad spenderare"),
    "tr_balanced_ev": ("No single pattern dominates your spending.", "Mikään yksittäinen tapa ei hallitse kulutustasi.", "Inget enskilt mönster dominerar dina utgifter."),
    "tr_balanced_tip": ("Keep it up and set a goal for your surplus.", "Jatka samaan malliin ja aseta ylijäämälle tavoite.", "Fortsätt så och sätt ett mål för ditt överskott."),
    "profile_note": ("Based on your last 3 full months. Patterns, not judgements.", "Perustuu kolmeen viime täyteen kuukauteen. Tapoja, ei arvosteluja.", "Baserat på dina senaste 3 hela månader. Mönster, inte omdömen."),
    # benchmark
    "bm_food": ("Food & groceries", "Ruoka", "Mat och livsmedel"),
    "bm_housing": ("Housing & energy", "Asuminen ja energia", "Boende och energi"),
    "bm_source": ("Statistics Finland, Households' consumption 2022 (Household Budget Survey)", "Tilastokeskus, Kotitalouksien kulutus 2022 (kulutustutkimus)", "Statistikcentralen, Hushållens konsumtion 2022 (hushållsbudgetundersökningen)"),
    "bm_caveat": ("Household survey shares include costs that may not appear as card or account transactions. Use as a rough reference, not a target.",
                  "Kulutustutkimuksen osuudet sisältävät menoja, jotka eivät välttämättä näy tilitapahtumina. Käytä suuntaa antavana vertailuna, ei tavoitteena.",
                  "Undersökningens andelar innehåller kostnader som inte alltid syns som kontotransaktioner. Använd dem som en ungefärlig jämförelse, inte som ett mål."),
    # insights
    "in_coffee_t": ("Cafés & fast food: {amount} a month", "Kahvilat ja pikaruoka: {amount} kuukaudessa", "Kaféer och snabbmat: {amount} i månaden"),
    "in_coffee_b": ("About {n} small purchases a month. Halving them would free {yearly} a year.", "Noin {n} pientä ostoa kuukaudessa. Puolittamalla ne säästäisit {yearly} vuodessa.", "Cirka {n} små köp i månaden. Att halvera dem skulle frigöra {yearly} per år."),
    "in_coffee_q": ("How much do I spend on cafés and fast food, and what if I cut it in half?", "Paljonko kulutan kahviloihin ja pikaruokaan ja mitä jos puolittaisin sen?", "Hur mycket lägger jag på kaféer och snabbmat och vad händer om jag halverar det?"),
    "in_payday_t": ("Most of your fun money goes in week one", "Suurin osa vapaasta rahasta menee ensimmäisellä viikolla", "Det mesta av dina fria pengar går första veckan"),
    "in_payday_b": ("{p} of everyday spending happens in the 7 days after payday.", "{p} arjen kulutuksesta tapahtuu 7 päivän sisällä palkkapäivästä.", "{p} av vardagsutgifterna sker inom 7 dagar efter lönedagen."),
    "in_payday_q": ("Why am I running out of money before payday?", "Miksi rahat loppuvat ennen palkkapäivää?", "Varför tar pengarna slut före lönedagen?"),
    "in_up_t": ("{label} up {p}", "{label}: +{p}", "{label}: +{p}"),
    "in_up_b": ("{b} in {pb} vs {a} in {pa}.", "{pb}: {b}, {pa}: {a}.", "{pb}: {b}, {pa}: {a}."),
    "in_up_q": ("Which categories increased compared with last month?", "Mitkä menot kasvoivat edelliseen kuukauteen verrattuna?", "Vilka utgifter ökade jämfört med förra månaden?"),
    "in_subs_t": ("Repeating extras add up", "Toistuvat lisämenot kertyvät", "Återkommande extrautgifter blir mycket"),
    "in_subs_q": ("What subscriptions am I paying for?", "Mistä tilauksista maksan?", "Vilka prenumerationer betalar jag för?"),
    "in_unc_t": ("{n} merchants need your call", "{n} kauppaa odottaa päätöstäsi", "{n} butiker väntar på ditt beslut"),
    "in_unc_t1": ("1 merchant needs your call", "1 kauppa odottaa päätöstäsi", "1 butik väntar på ditt beslut"),
    "in_unc_b": ("OMA won't guess. Sort them into a basket and your numbers get sharper.", "OMA ei arvaa. Lajittele ne koreihin, niin lukusi tarkentuvat.", "OMA gissar inte. Sortera dem i korgar så blir dina siffror skarpare."),
    # vetted advice catalogue (the only recommendations the coach may give)
    "ad_overspend_t": ("Get back to balance", "Takaisin tasapainoon", "Tillbaka till balans"),
    "ad_overspend_w": ("In {months} more money went out than came in.", "Näinä kuukausina menoja oli enemmän kuin tuloja: {months}.", "Under {months} gick mer pengar ut än in."),
    "ad_overspend_a": ("Cover essentials first (rent, bills, food), then cut back your biggest everyday area, {group} ({amount}/month), until the months balance.",
                       "Hoida ensin välttämättömät (vuokra, laskut, ruoka). Vähennä sitten suurinta arjen menoerää, {group} ({amount}/kk), kunnes kuukaudet ovat tasapainossa.",
                       "Betala det nödvändiga först (hyra, räkningar, mat). Minska sedan din största vardagspost, {group} ({amount}/mån), tills månaderna går ihop."),
    "ad_buffer_t": ("Start a small buffer", "Aloita pieni puskuri", "Börja med en liten buffert"),
    "ad_buffer_w": ("You don't move money to savings yet, so any surprise cost hits your everyday money.", "Et vielä siirrä rahaa säästöön, joten jokainen yllätysmeno osuu arjen rahoihin.", "Du sparar inte ännu, så varje oväntad kostnad drabbar dina vardagspengar."),
    "ad_buffer_a": ("Set an automatic transfer of {amount} to a savings account right after payday.", "Aseta automaattinen siirto säästötilille heti palkkapäivän jälkeen: {amount}.", "Gör en automatisk överföring på {amount} till ett sparkonto direkt efter lönedagen."),
    "ad_target_t": ("Grow your emergency buffer", "Kasvata hätävaraasi", "Bygg upp din buffert"),
    "ad_target_w": ("You already save {amount} a month. A common first target is one month of fixed essentials.", "Säästät jo {amount} kuukaudessa. Yleinen ensimmäinen tavoite on yhden kuukauden kiinteät menot.", "Du sparar redan {amount} i månaden. Ett vanligt första mål är en månads fasta utgifter."),
    "ad_target_a": ("Aim for a buffer of about {amount}, kept separate from everyday money.", "Tavoittele noin {amount} puskuria, erillään arjen rahoista.", "Sikta på en buffert på cirka {amount}, skild från vardagspengarna."),
    "ad_weekly_t": ("Use a weekly allowance", "Ota käyttöön viikkoraha", "Använd en veckopeng"),
    "ad_weekly_w": ("{p} of your everyday spending happens in the week after payday.", "{p} arjen kulutuksestasi tapahtuu palkkapäivää seuraavalla viikolla.", "{p} av dina vardagsutgifter sker veckan efter lönedagen."),
    "ad_weekly_a": ("Right now that's about {amount} a week until payday. Moving it to a separate account each Monday keeps week four as good as week one.",
                    "Juuri nyt se on noin {amount} viikossa palkkapäivään asti. Siirrä se joka maanantai erilliselle tilille, niin neljäs viikko on yhtä hyvä kuin ensimmäinen.",
                    "Just nu är det cirka {amount} i veckan fram till lönedagen. Flytta det till ett eget konto varje måndag, så blir vecka fyra lika bra som vecka ett."),
    "ad_subs_t": ("Review your repeating extras", "Käy toistuvat lisämenot läpi", "Gå igenom återkommande extrautgifter"),
    "ad_subs_w": ("{names}: {amount} a month in total.", "{names}: yhteensä {amount} kuukaudessa.", "{names}: totalt {amount} i månaden."),
    "ad_subs_a": ("Keep the ones you use every week; pause the rest. You can always rejoin.", "Pidä ne, joita käytät viikoittain, ja tauota muut. Voit aina palata.", "Behåll dem du använder varje vecka och pausa resten. Du kan alltid gå med igen."),
    "ad_irregular_t": ("Plan for irregular must-haves", "Varaudu satunnaisiin menoihin", "Planera för oregelbundna måsten"),
    "ad_irregular_w": ("Repairs, health costs and similar have averaged {amount} a month over the past year.", "Korjaukset, terveysmenot ja vastaavat ovat olleet keskimäärin {amount} kuukaudessa viime vuonna.", "Reparationer, hälsokostnader och liknande har i snitt kostat {amount} i månaden det senaste året."),
    "ad_irregular_a": ("Put {amount} aside each month so the next one doesn't come out of your everyday money.", "Laita sivuun {amount} kuukaudessa, niin seuraava yllätys ei syö arjen rahojasi.", "Lägg undan {amount} varje månad, så tas nästa överraskning inte från vardagspengarna."),
    "ad_habit_t": ("Halve one small habit", "Puolita yksi pieni tapa", "Halvera en liten vana"),
    "ad_habit_w": ("{group}: about {n} purchases a month, {amount} in total.", "{group}: noin {n} ostoa kuukaudessa, yhteensä {amount}.", "{group}: cirka {n} köp i månaden, totalt {amount}."),
    "ad_habit_a": ("Halving it would free about {yearly} a year, without giving it up completely.", "Puolittamalla vapautuisi noin {yearly} vuodessa, eikä sinun tarvitse luopua kokonaan.", "Att halvera det skulle frigöra cirka {yearly} per år, utan att du behöver sluta helt."),
}

# Verified free help in Finland (sources: vero.fi "Apua oman talouden hallintaan", oikeus.fi)
HELP = {
    "debt": ("Free, confidential help: the state's Financial and Debt Counselling (oikeus.fi/talousjavelkaneuvonta) and Takuusäätiö's Velkalinja helpline 0800 9 8009 or their 'Kysy rahasta' chat (takuusaatio.fi). You can contact them even before you have debts.",
             "Maksutonta ja luottamuksellista apua: valtion talous- ja velkaneuvonta (oikeus.fi/talousjavelkaneuvonta) sekä Takuusäätiön Velkalinja 0800 9 8009 tai Kysy rahasta -chat (takuusaatio.fi). Yhteyttä voi ottaa jo ennen kuin velkaa on.",
             "Gratis och konfidentiell hjälp: statens ekonomi- och skuldrådgivning (oikeus.fi/talousjavelkaneuvonta) samt Takuusäätiös Velkalinja 0800 9 8009 eller chatten 'Kysy rahasta' (takuusaatio.fi). Du kan ta kontakt redan innan du har skulder."),
    "bank": ("For product decisions, S-Bank's customer service or advisors can look at your full situation.",
             "Tuotepäätöksissä S-Pankin asiakaspalvelu tai neuvojat voivat katsoa tilannettasi kokonaisuutena.",
             "Vid produktbeslut kan S-Bankens kundtjänst eller rådgivare se på din helhetssituation."),
    "tax": ("For tax questions, the Finnish Tax Administration (vero.fi) is the reliable source.",
            "Veroasioissa luotettava lähde on Verohallinto (vero.fi).",
            "I skattefrågor är Skatteförvaltningen (vero.fi) den pålitliga källan."),
}
