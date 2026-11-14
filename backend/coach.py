"""Ask OMA: the conversational coach (Finnish by default, Swedish and English).

Safety design, in order:
1. Topic guards (deterministic, before any AI): investments, loans/credit, debt distress and
   taxes get a vetted answer with verified free help resources. No product recommendations.
2. The language model never produces a number on its own: it calls engine tools and explains.
   Recommendations may only come from the vetted advice catalogue (engine.advice) or lessons.
3. Grounding check: every euro amount in an AI answer must match a tool result. If not, the
   model gets one chance to rewrite; if it still fails, OMA answers with its rule engine instead.
4. No API key or network? The multilingual rule engine answers the core questions.
"""
from __future__ import annotations

import json
import os
import re

from engine import Customer, groups_matching
from i18n import HELP, LANGS, basket_meta, cap, money, norm, parse_amounts, pct, pick, plural
from lessons import LESSON_IDS, lessons
from rules import BASKET_IDS

PERIOD_DOC = "Period: this_month, last_month, this_week, last_week, last_N_days, last_N_months (full months), ytd, last_12_months, or YYYY-MM."
LANG_NAME = {"fi": "Finnish", "sv": "Swedish", "en": "English"}

TOOLS = [
    ("get_spending", "Total spending, optionally filtered, grouped by category, merchant, basket, month (trend) or weekday. For 'how much did I spend on X', 'biggest expenses', trends.",
     {"group_by": {"type": "string", "enum": ["category", "merchant", "basket", "month", "weekday"]}, "period": {"type": "string", "description": PERIOD_DOC},
      "basket": {"type": "string", "enum": BASKET_IDS}, "category": {"type": "string", "description": "Category keyword in any language, e.g. 'Restaurants', 'ravintolat', 'kaffe'"},
      "merchant": {"type": "string", "description": "Merchant name or part of it, e.g. 'Wolt'"}}, []),
    ("list_transactions", "List individual transactions.",
     {"period": {"type": "string", "description": PERIOD_DOC}, "category": {"type": "string"}, "merchant": {"type": "string"},
      "basket": {"type": "string", "enum": BASKET_IDS}, "sort": {"type": "string", "enum": ["date", "amount"]}, "limit": {"type": "integer"}}, []),
    ("compare_periods", "Compare spending between two periods by category/merchant/basket. Partial periods are compared like-for-like.",
     {"period_a": {"type": "string", "description": "Earlier period. " + PERIOD_DOC}, "period_b": {"type": "string"},
      "group_by": {"type": "string", "enum": ["category", "merchant", "basket"]}}, ["period_a", "period_b"]),
    ("get_month_summary", "Income, spending, savings and leftover for a period, split by the three baskets.", {"period": {"type": "string", "description": PERIOD_DOC}}, []),
    ("get_baskets", "Average monthly spending in each basket (fixed essentials, occasional essentials, everyday) with share of income, categories and 6-month trend.", {}, []),
    ("get_safe_to_spend", "How much the user can safely spend until next payday, with the full calculation.", {}, []),
    ("can_i_afford", "Check whether a specific purchase fits the safe-to-spend amount.", {"amount": {"type": "number"}}, ["amount"]),
    ("simulate_what_if", "Simulate reducing spending in a category, merchant or basket by a percentage: monthly/yearly savings and months to a goal.",
     {"target": {"type": "string", "description": "Category keyword (any language), merchant, or basket id"}, "reduce_pct": {"type": "number"}, "goal_amount": {"type": "number"}}, ["target", "reduce_pct"]),
    ("get_safe_to_save", "A realistic monthly savings amount based on leftover money in recent months.", {}, []),
    ("get_payday_pattern", "Everyday spending across the weeks after payday, plus months where spending exceeded income. For 'why do I run out of money before payday'.", {}, []),
    ("get_spender_profile", "What kind of spender the user is: behavioural traits with evidence and tips.", {}, []),
    ("get_benchmark", "The user's spending structure vs Statistics Finland household survey data.", {}, []),
    ("get_peer_benchmark", "The user vs S-Bank customers of the same age band (medians): everyday share, fixed share, saving rate, restaurants etc.", {}, []),
    ("get_advice", "The ONLY source of personal recommendations: vetted, rule-based next steps for this user, ranked. Call it whenever the user asks what to do, for tips or advice.", {}, []),
    ("get_lesson", "A short, vetted financial-literacy lesson.", {"topic": {"type": "string", "enum": LESSON_IDS}}, ["topic"]),
    ("get_help_resources", "Verified free help in Finland for debt or money worries, tax questions, or bank product decisions.", {"topic": {"type": "string", "enum": ["debt", "tax", "bank"]}}, ["topic"]),
]


def run_tool(c: Customer, name: str, a: dict):
    a = {k: v for k, v in (a or {}).items() if v not in (None, "")}
    if name == "get_spending":
        return c.spending(a.get("group_by", "category"), a.get("period", "this_month"), a.get("basket"), a.get("category"), a.get("merchant"))
    if name == "list_transactions":
        return c.transactions(a.get("period", "this_month"), a.get("basket"), a.get("category"), a.get("merchant"), int(a.get("limit", 10)), a.get("sort", "date"))
    if name == "compare_periods":
        return c.compare(a["period_a"], a["period_b"], a.get("group_by", "category"))
    if name == "get_month_summary":
        return c.month_summary(a.get("period", "this_month"))
    if name == "get_baskets":
        return c.baskets()
    if name == "get_safe_to_spend":
        return c.safe_to_spend()
    if name == "can_i_afford":
        return c.can_afford(float(a["amount"]))
    if name == "simulate_what_if":
        return c.what_if(a["target"], float(a.get("reduce_pct", 20)), a.get("goal_amount"))
    if name == "get_safe_to_save":
        return c.safe_to_save()
    if name == "get_payday_pattern":
        return c.payday_cycle()
    if name == "get_spender_profile":
        return c.spender_profile()
    if name == "get_benchmark":
        return c.benchmark()
    if name == "get_peer_benchmark":
        return c.peer_benchmark()
    if name == "get_advice":
        return c.advice()
    if name == "get_lesson":
        return lessons(c.lang).get(a.get("topic"), lessons(c.lang)["three_baskets"])
    if name == "get_help_resources":
        return {"text": pick(HELP.get(a.get("topic"), HELP["bank"]), c.lang)}
    return {"error": f"unknown tool {name}"}


def system_prompt(c: Customer, demo: bool):
    return f"""You are OMA, a warm, encouraging personal finance coach inside S-Bank's S-mobiili app, helping {c.name or 'an S-Bank customer'}{f' (age {c.age})' if c.age else ''} understand their own money.

LANGUAGE: Always answer in {LANG_NAME[c.lang]}{' (use the friendly sinä form, natural everyday Finnish)' if c.lang == 'fi' else ''}. Tool results are already in that language.

DATA: the user's transactions up to {c.as_of:%Y-%m-%d} (treat that as "today"). {'Demo data.' if demo else 'Synthetic S-Bank data: merchants are anonymised and shown by type and number (e.g. "Grocery store #0010").'}
Spending sits in three baskets: fixed essentials (must-haves every month), occasional essentials (must-haves now and then), everyday spending (flexible, slips through your fingers).

HARD RULES
1. Never invent or calculate numbers. Every amount, count or percentage you state must appear in a tool result from this conversation. Need a number? Call a tool. Don't add, subtract, multiply or round figures into new ones.
2. Personal recommendations come ONLY from get_advice, the tips inside tool results, or get_lesson. You may rephrase them warmly; you may not add new advice.
3. Never recommend specific investments, funds, stocks, crypto, loans, credit, insurance or tax strategies, and never predict markets or promise outcomes. Explain general concepts simply and point to get_help_resources (topic "bank" or "tax").
4. If the user mentions debt, unpaid bills or money stress: be kind, never blame, and share get_help_resources(topic="debt").
5. Never suggest cutting rent, food, medicine, childcare or other essentials. Focus changes on everyday spending.
6. If the data can't answer, say so plainly. Estimates are estimates; say so.

STYLE
- Friendly, calm, non-judgemental, like a knowledgeable friend. Teach, never shame. Suggest, never command.
- Mobile screen: at most ~90 words, short sentences, no tables or headings. Bold at most one key number with **.
- Format euros as the tool results do{' (e.g. 49,35 €)' if c.lang != 'en' else ' (e.g. €49.35)'}.
- When useful, add one line starting with "💡 " that teaches the money idea behind the answer.
- End with one line exactly like: FOLLOW-UPS: question 1 | question 2 | question 3  (short questions in the user's voice and language)."""


# ------------------------------------------------------------------ grounding check
def _known(obj, lang, out):
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        out.append(abs(float(obj)))
    elif isinstance(obj, dict):
        for v in obj.values():
            _known(v, lang, out)
    elif isinstance(obj, list):
        for v in obj:
            _known(v, lang, out)
    elif isinstance(obj, str):
        out.extend(parse_amounts(obj, lang))
    return out


def grounding(text: str, cards: list, lang: str):
    known = []
    for cd in cards:
        _known(cd["output"], lang, known)
    _known(lessons(lang), lang, known)
    amounts = parse_amounts(text, lang)
    unverified = [a for a in amounts if not any(abs(a - k) <= max(0.6, 0.01 * k) for k in known)]
    return {"checked": len(amounts), "verified": len(amounts) - len(unverified), "unverified": unverified}


def _split_followups(text: str):
    m = re.search(r"FOLLOW-?UPS?:\s*(.+)$", text, re.I | re.S)
    if not m:
        return text.strip(), []
    return text[: m.start()].strip(), [q.strip(" -•") for q in m.group(1).split("|") if q.strip()][:3]


# ------------------------------------------------------------------ LLM providers
def _anthropic(c, msgs, demo, cards):
    import anthropic
    client = anthropic.Anthropic()
    tools = [{"name": n, "description": d, "input_schema": {"type": "object", "properties": p, "required": r}} for n, d, p, r in TOOLS]
    model = os.environ.get("OMA_MODEL", "claude-sonnet-5-5")
    msgs = list(msgs)
    for _ in range(6):
        resp = client.messages.create(model=model, max_tokens=900, system=system_prompt(c, demo), tools=tools, messages=msgs)
        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text"), model
        msgs.append({"role": "assistant", "content": resp.content})
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                out = run_tool(c, b.name, b.input)
                cards.append({"tool": b.name, "input": b.input, "output": out})
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(out, default=str, ensure_ascii=False)})
        msgs.append({"role": "user", "content": results})
    raise RuntimeError("too many tool steps")


def _openai(c, msgs, demo, cards):
    from openai import OpenAI
    client = OpenAI(base_url=os.environ.get("OPENAI_BASE_URL") or None)
    tools = [{"type": "function", "function": {"name": n, "description": d, "parameters": {"type": "object", "properties": p, "required": r}}} for n, d, p, r in TOOLS]
    model = os.environ.get("OMA_MODEL", "gpt-4.1-mini")
    msgs = [{"role": "system", "content": system_prompt(c, demo)}] + list(msgs)
    for _ in range(6):
        msg = client.chat.completions.create(model=model, messages=msgs, tools=tools, max_tokens=900).choices[0].message
        if not msg.tool_calls:
            return msg.content or "", model
        msgs.append(msg)
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments or "{}")
            out = run_tool(c, tc.function.name, args)
            cards.append({"tool": tc.function.name, "input": args, "output": out})
            msgs.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(out, default=str, ensure_ascii=False)})
    raise RuntimeError("too many tool steps")


def provider():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return None


FIX_NOTE = ("Your answer contained figures that are not in any tool result: {bad}. Rewrite the answer using only numbers that appear in tool results "
            "(call more tools if needed), or leave the number out. Same language, same style.")


def ask(c: Customer, messages: list, demo: bool):
    q = messages[-1]["content"]
    guarded = guard_answer(c, q)
    if guarded:
        guarded["grounding"] = grounding(guarded["text"], guarded["cards"], c.lang)
        return guarded
    prov = provider()
    error = None
    if prov:
        try:
            call = _anthropic if prov == "anthropic" else _openai
            cards = []
            text, model = call(c, messages, demo, cards)
            g = grounding(text, cards, c.lang)
            retried = False
            if g["unverified"]:  # one chance to fix, with the tool results still in context
                retried = True
                fix = messages + [{"role": "assistant", "content": text}, {"role": "user", "content": FIX_NOTE.format(bad=", ".join(f"{x:g}" for x in g["unverified"]))}]
                text, model = call(c, fix, demo, cards)
                g = grounding(text, cards, c.lang)
            if not g["unverified"]:
                text, fu = _split_followups(text)
                return {"text": text, "cards": cards, "followups": fu or followups(c.lang, cards), "grounding": grounding(text, cards, c.lang),
                        "mode": "ai", "model": model, "retried": retried}
            error = "unverified figures after retry"
        except Exception as e:  # network, key, rate limit: never break the demo
            error = str(e)[:200]
    res = offline_answer(c, q)
    res["mode"] = "safe" if error == "unverified figures after retry" else "offline"
    if error:
        res["error"] = error
    res["grounding"] = grounding(res["text"], res["cards"], c.lang)
    return res


# ------------------------------------------------------------------ multilingual text for the rule engine
def R(key, lang, **kw):
    return pick(TXT[key], lang).format(**kw)


TXT = {
    "afford_no": ("Not comfortably right now. You have about **{sts}** safe to spend until payday ({date}), so {amount} would leave you short. Maybe a smaller plan this time, or wait until after payday?",
                  "Ei ihan mukavasti juuri nyt. Turvallisesti käytettävissä on noin **{sts}** palkkapäivään ({date}) asti, joten {amount} ei mahdu siihen. Ehkä pienempi suunnitelma tällä kertaa, tai odota palkkapäivän yli?",
                  "Inte riktigt just nu. Du har cirka **{sts}** tryggt att spendera fram till lönedagen ({date}), så {amount} räcker inte till. Kanske en mindre plan den här gången, eller vänta till efter lönedagen?"),
    "afford_yes": ("Yes{tight}. You have **{sts}** safe to spend until {date}. After {amount} you'd have {left} left: {pd_after} a day instead of {pd_now}.",
                   "Kyllä{tight}. Turvallisesti käytettävissä on **{sts}** palkkapäivään ({date}) asti. Sen jälkeen jäisi {left}: {pd_after} päivässä nykyisen {pd_now} sijaan.",
                   "Ja{tight}. Du har **{sts}** tryggt att spendera fram till lönedagen ({date}). Efter {amount} har du {left} kvar: {pd_after} per dag i stället för {pd_now}."),
    "tight": (", but it will be tight", ", mutta tiukille menee", ", men det blir snävt"),
    "afford_tip": ("💡 Safe-to-spend already sets aside your upcoming bills, groceries and savings, so it's money you can actually use.",
                   "💡 Turvallinen summa huomioi jo tulevat laskut, ruoan ja säästöt, joten sen voi oikeasti käyttää.",
                   "💡 Beloppet tar redan hänsyn till kommande räkningar, mat och sparande, så det är pengar du verkligen kan använda."),
    "whatif_main": ("{target}: about **{monthly} a month** ({np}). Cutting {p} would save {save_m} a month, which is **{save_y} a year**.",
                    "{target}: noin **{monthly} kuukaudessa** ({np}). Vähentämällä {p} säästäisit {save_m} kuukaudessa eli **{save_y} vuodessa**.",
                    "{target}: cirka **{monthly} i månaden** ({np}). Om du minskar med {p} sparar du {save_m} i månaden, alltså **{save_y} per år**."),
    "whatif_fewer": (" That's roughly {np} fewer a month.", " Se on noin {np} vähemmän kuukaudessa.", " Det är ungefär {np} färre i månaden."),
    "whatif_tip": ("💡 Small, repeated choices matter more than one big sacrifice: they add up over the year.",
                   "💡 Pienet toistuvat valinnat merkitsevät enemmän kuin yksi iso uhraus: ne kertyvät vuoden mittaan.",
                   "💡 Små återkommande val betyder mer än en stor uppoffring: de växer under året."),
    "payday_main": ("Your main income arrives around day {day}. In the first week after payday you spend **{p}** of your everyday money; an even pace would be about 25%.",
                    "Päätulosi tulee noin kuun {day}. päivänä. Palkkapäivää seuraavalla viikolla käytät **{p}** arjen rahoistasi, kun tasainen tahti olisi noin 25 %.",
                    "Din huvudinkomst kommer runt den {day}:e. Veckan efter lönedagen använder du **{p}** av dina vardagspengar, medan jämn takt vore ungefär 25 %."),
    "payday_short": (" In {months}, more went out than came in.", " Näinä kuukausina menoja oli enemmän kuin tuloja: {months}.", " Under {months} gick mer ut än in."),
    "payday_small": (" You also make about {n} small purchases (under 15 €) a month, worth {amount}.", " Lisäksi teet noin {n} alle 15 euron ostoa kuukaudessa, yhteensä {amount}.", " Du gör också cirka {n} köp under 15 euro i månaden, totalt {amount}."),
    "sts_over": ("Honest answer: this pay cycle's flexible money is used up (about {over} over the plan). Payday is {date}, {n} days away. Sticking to essentials until then gets you back on track.",
                 "Rehellinen vastaus: tämän palkkajakson vapaa raha on jo käytetty (noin {over} yli suunnitelman). Palkkapäivä on {date}, {n} päivän päästä. Kun pysyt välttämättömissä siihen asti, olet taas raiteilla.",
                 "Ärligt svar: den här löneperiodens fria pengar är slut (cirka {over} över planen). Lönedagen är {date}, om {n} dagar. Håll dig till det nödvändiga tills dess, så är du på rätt spår igen."),
    "sts_ok": ("You can safely spend about **{sts}** until payday on {date}: {pd} a day, or {pw} this week. That's after your bills, groceries, a reserve for irregular costs and saving {rate}.",
               "Voit käyttää turvallisesti noin **{sts}** palkkapäivään ({date}) asti: {pd} päivässä tai {pw} tällä viikolla. Laskut, ruoka, varaus satunnaisiin menoihin ja {rate} säästö on jo huomioitu.",
               "Du kan tryggt spendera cirka **{sts}** fram till lönedagen ({date}): {pd} per dag eller {pw} den här veckan. Räkningar, mat, en reserv för oregelbundna kostnader och {rate} sparande är redan medräknade."),
    "sts_tip": ("💡 Your balance isn't spendable money; safe-to-spend is what's left after what's already promised.",
                "💡 Saldo ei ole käyttörahaa. Turvallinen summa on se, mikä jää, kun jo luvatut menot on vähennetty.",
                "💡 Saldot är inte fria pengar. Det trygga beloppet är det som blir kvar när redan utlovade utgifter är avdragna."),
    "profile_main": ("You look like a **{name}**. {ev}", "Näytät olevan **{name}**. {ev}", "Du verkar vara en **{name}**. {ev}"),
    "profile_also": (" A bit of {names} too.", " Hieman myös: {names}.", " Lite av {names} också."),
    "save_ok": ("Looking at your last {n} months, **{amount} a month** looks realistic to save. That's what you had left even in a weaker month, so it shouldn't squeeze you.",
                "Viime {n} kuukauden perusteella **{amount} kuukaudessa** on realistinen säästösumma. Sen verran sinulle jäi heikompanakin kuukautena, joten sen ei pitäisi kiristää.",
                "Utifrån dina senaste {n} månader ser **{amount} i månaden** realistiskt ut att spara. Det hade du kvar även en svagare månad, så det borde inte bli för snävt."),
    "save_none": ("Right now your weaker months end with nothing left over, so a fixed savings amount could squeeze you. A gentler start: trim one everyday habit. The Goals tab shows which one frees the most.",
                  "Heikompina kuukausina sinulle ei tällä hetkellä jää mitään yli, joten kiinteä säästösumma voisi kiristää. Lempeämpi alku: karsi yhtä arjen tapaa. Tavoitteet-välilehti näyttää, mikä vapauttaa eniten.",
                  "Just nu blir det inget över under svagare månader, så ett fast sparbelopp kan bli för snävt. En mjukare start: dra ner på en vardagsvana. Fliken Mål visar vilken som frigör mest."),
    "save_tip": ("💡 Save right after payday, not with what's left at the end of the month.", "💡 Säästä heti palkkapäivänä, älä siitä mitä kuun lopussa jää.", "💡 Spara direkt på lönedagen, inte det som blir kvar i slutet av månaden."),
    "new": ("new", "uusi", "ny"),
    "compare_none": ("Good news: nothing went up ({pa} → {pb}).", "Hyviä uutisia: mikään meno ei kasvanut ({pa} → {pb}).", "Goda nyheter: ingenting ökade ({pa} → {pb})."),
    "compare_total": (" Total: {a} → {b}.", " Yhteensä: {a} → {b}.", " Totalt: {a} → {b}."),
    "subs_main": ("{period}: **{total}** for subscriptions and entertainment: {items}.", "{period}: tilauksiin ja viihteeseen meni **{total}**: {items}.", "{period}: **{total}** på prenumerationer och nöje: {items}."),
    "subs_tip": ("💡 Repeating payments are easy to forget because they never ask again. Pausing the ones you rarely use is a painless way to save.",
                 "💡 Toistuvat maksut unohtuvat helposti, koska ne eivät kysy uudestaan. Harvoin käytettyjen tauottaminen on kivuton tapa säästää.",
                 "💡 Återkommande betalningar glöms lätt eftersom de aldrig frågar igen. Att pausa det du sällan använder är ett smärtfritt sätt att spara."),
    "bench_main": ("Groceries are {food} of your spending. In Statistics Finland's survey, food takes 18% for lower-income households and 12% for higher-income ones. Housing and energy are {housing} for you, vs 39% for lower-income households. {caveat}",
                   "Ruokaostokset ovat {food} menoistasi. Tilastokeskuksen kulutustutkimuksessa ruoan osuus on pienituloisilla kotitalouksilla 18 % ja suurituloisilla 12 %. Asuminen ja energia ovat sinulla {housing}, pienituloisilla kotitalouksilla 39 %. {caveat}",
                   "Livsmedel utgör {food} av dina utgifter. I Statistikcentralens undersökning är matens andel 18 % för hushåll med låga inkomster och 12 % för hushåll med höga inkomster. Boende och energi är {housing} för dig, jämfört med 39 % för hushåll med låga inkomster. {caveat}"),
    "biggest_main": ("{period}: your biggest spending areas were {items}, out of **{total}** in total.", "{period}: suurimmat menoeräsi olivat {items}. Yhteensä **{total}**.", "{period}: dina största utgiftsposter var {items}, av totalt **{total}**."),
    "biggest_tip": ("💡 Fixed costs like rent are usually biggest; the quickest wins tend to hide in everyday spending.",
                    "💡 Kiinteät menot, kuten vuokra, ovat yleensä suurimpia, mutta nopeimmat säästöt löytyvät usein arjen kulutuksesta.",
                    "💡 Fasta kostnader som hyra är oftast störst, men de snabbaste vinsterna finns ofta i vardagsutgifterna."),
    "byx_main": ("{period}: **{total}**{everyday}. Biggest: {items}.", "{period}: **{total}**{everyday}. Suurimmat: {items}.", "{period}: **{total}**{everyday}. Störst: {items}."),
    "everyday_word": (" on everyday things", " arjen kulutukseen", " på vardagsutgifter"),
    "weekday_tip": ("💡 The days with most spending are usually social days. Planning those ahead is easier than cutting everywhere.",
                    "💡 Eniten kuluttavat päivät ovat yleensä sosiaalisia päiviä. Niiden suunnittelu etukäteen on helpompaa kuin karsiminen kaikesta.",
                    "💡 Dagarna med mest utgifter är oftast sociala dagar. Att planera dem i förväg är lättare än att dra ner överallt."),
    "basket_main": ("{name}: on average **{amount} a month**{share}. Biggest parts: {items}.", "{name}: keskimäärin **{amount} kuukaudessa**{share}. Suurimmat: {items}.", "{name}: i snitt **{amount} i månaden**{share}. Störst: {items}."),
    "share": (" ({p} of your income)", " ({p} tuloistasi)", " ({p} av dina inkomster)"),
    "spent_none": ("{period} – {what}: no spending found.", "{period} – {what}: menoja ei löytynyt.", "{period} – {what}: inga utgifter hittades."),
    "spent_main": ("{period} – {what}: **{total}** in total ({np}{mostly}).", "{period} – {what}: yhteensä **{total}** ({np}{mostly}).", "{period} – {what}: totalt **{total}** ({np}{mostly})."),
    "mostly": (", mostly {m}", ", eniten {m}", ", mest {m}"),
    "advice_main": ("Here's what I'd suggest, based on your own numbers:", "Tässä ehdotukseni omien lukujesi perusteella:", "Här är mina förslag utifrån dina egna siffror:"),
    "advice_none": ("Your money looks balanced right now. A good next step is giving your savings a named goal in the Goals tab.",
                    "Taloutesi näyttää nyt tasapainoiselta. Hyvä seuraava askel on antaa säästöillesi nimetty tavoite Tavoitteet-välilehdellä.",
                    "Din ekonomi ser balanserad ut just nu. Ett bra nästa steg är att ge ditt sparande ett namngivet mål under fliken Mål."),
    "peers_main": ("Compared with {title} (median of {n}): {items}.", "Vertailu: {title} (mediaani {n} asiakkaasta): {items}.", "Jämfört med {title} (median av {n}): {items}."),
    "peers_vs": ("{label} {you} vs {peers}", "{label} {you} vs. {peers}", "{label} {you} mot {peers}"),
    "peers_none": ("I don't have a large enough group of customers your age to compare with.", "Ikäryhmästäsi ei ole tarpeeksi asiakkaita vertailuun.", "Det finns inte tillräckligt många kunder i din ålder att jämföra med."),
    "peers_tip": ("💡 Comparisons show what's common, not what's right for you. Use them as a mirror, not a rule.",
                  "💡 Vertailu kertoo, mikä on tavallista, ei sitä, mikä sopii juuri sinulle. Käytä sitä peilinä, älä sääntönä.",
                  "💡 Jämförelser visar vad som är vanligt, inte vad som passar dig. Använd dem som en spegel, inte en regel."),
    "fallback": ("{period}: you've received {inc} and spent {out}. I can help with your spending, what's safe to spend, what-if savings, your habits and money basics. Try one of these:",
                 "{period}: tuloja {inc}, menoja {out}. Voin auttaa menoissa, turvallisessa käyttörahassa, säästölaskelmissa, kulutustavoissa ja raha-asioiden perusteissa. Kokeile näitä:",
                 "{period}: inkomster {inc}, utgifter {out}. Jag kan hjälpa till med dina utgifter, vad som är tryggt att spendera, sparkalkyler, dina vanor och grunderna i privatekonomi. Prova någon av dessa:"),
    # guards
    "guard_invest": ("I can't recommend specific investments, funds or stocks, because that depends on things I can't see: your goals, timeline and how much risk you can live with. A common order is (1) a buffer for surprises, (2) no expensive debt, (3) then long-term saving. {bank}",
                     "En voi suositella tiettyjä sijoituksia, rahastoja tai osakkeita, koska se riippuu asioista, joita en näe: tavoitteistasi, aikataulustasi ja siitä, kuinka paljon riskiä siedät. Yleinen järjestys on (1) puskuri yllätyksiin, (2) ei kallista velkaa, (3) sitten pitkäaikainen säästäminen. {bank}",
                     "Jag kan inte rekommendera specifika placeringar, fonder eller aktier, eftersom det beror på saker jag inte ser: dina mål, din tidshorisont och hur mycket risk du klarar. En vanlig ordning är (1) en buffert för överraskningar, (2) inga dyra skulder, (3) sedan långsiktigt sparande. {bank}"),
    "guard_credit": ("I won't recommend taking a loan or credit; that's a decision to make with the full picture. Before any credit or instalment plan, check the total cost (not just the monthly amount) and whether the payment fits your safe-to-spend. {bank}",
                     "En suosittele lainan tai luoton ottamista, koska se päätös kannattaa tehdä koko kuvan perusteella. Tarkista ennen luottoa tai osamaksua kokonaishinta (ei vain kuukausierää) ja mahtuuko erä turvallisesti käytettävään rahaasi. {bank}",
                     "Jag rekommenderar inte att ta lån eller kredit, eftersom det beslutet kräver helhetsbilden. Kontrollera före kredit eller avbetalning totalkostnaden (inte bara månadsbeloppet) och om betalningen ryms i dina fria pengar. {bank}"),
    "guard_debt": ("I'm sorry it feels heavy. Money worries are really common, and asking early is a smart move. {debt} I can also help you see where your money goes, so you have the numbers ready when you talk to them.",
                   "Ikävää, että tilanne tuntuu raskaalta. Rahahuolet ovat todella yleisiä, ja avun pyytäminen ajoissa on viisas veto. {debt} Voin myös auttaa sinua näkemään, mihin rahasi menevät, jotta sinulla on luvut valmiina keskustelua varten.",
                   "Tråkigt att det känns tungt. Pengaoro är väldigt vanligt, och att be om hjälp tidigt är ett klokt drag. {debt} Jag kan också hjälpa dig se vart dina pengar tar vägen, så att du har siffrorna redo när du pratar med dem."),
    "guard_tax": ("Tax rules depend on your situation, so I don't want to guess. {tax}", "Verosäännöt riippuvat tilanteestasi, enkä halua arvailla. {tax}", "Skatteregler beror på din situation, så jag vill inte gissa. {tax}"),
}

Q = {  # follow-up questions in the user's voice (the frontend has the same set)
    "payday": ("Why am I running out of money before payday?", "Miksi rahat loppuvat ennen palkkapäivää?", "Varför tar pengarna slut före lönedagen?"),
    "whatif": ("How much could I save if I reduced dining out by 20%?", "Paljonko säästäisin, jos vähentäisin ulkona syömistä 20 %?", "Hur mycket skulle jag spara om jag minskade restaurangbesöken med 20 %?"),
    "profile": ("What kind of spender am I?", "Millainen kuluttaja olen?", "Vilken typ av spenderare är jag?"),
    "safe": ("What is safe for me to spend this week?", "Paljonko voin turvallisesti käyttää tällä viikolla?", "Hur mycket kan jag tryggt spendera den här veckan?"),
    "restaurants": ("How much did I spend on restaurants last month?", "Paljonko käytin ravintoloihin viime kuussa?", "Hur mycket spenderade jag på restauranger förra månaden?"),
    "advice": ("What would you suggest for me?", "Mitä neuvoisit minulle?", "Vad skulle du råda mig att göra?"),
    "goal": ("Make this a savings goal", "Tee tästä säästötavoite", "Gör detta till ett sparmål"),
    "explain_payday": ("Explain the payday effect", "Selitä palkkapäiväilmiö", "Förklara lönedagseffekten"),
    "explain_buffer": ("What is an emergency buffer?", "Mikä on puskuri yllätysten varalle?", "Vad är en buffert?"),
    "explain_bnpl": ("Explain instalments and pay later", "Selitä osamaksut", "Förklara avbetalning"),
}


def followups(lang, cards):
    tools = {c["tool"] for c in cards}
    keys = (["goal", "safe", "profile"] if "simulate_what_if" in tools else
            ["whatif", "safe", "explain_payday"] if "get_payday_pattern" in tools else
            ["safe", "whatif", "explain_buffer"] if "get_advice" in tools or "get_help_resources" in tools else
            ["advice", "whatif", "profile"])
    return [pick(Q[k], lang) for k in keys]


# ------------------------------------------------------------------ intent matching (FI / SV / EN)
TARGETS = [
    (r"coffee|kahvi|café|cafe|latte|snack|välipal|kaffe|fika|fast food|pikaruo|snabbmat|burger", "Coffee & snacks"),
    (r"restaurant|dining|eating out|eat out|takeaway|wolt|foodora|food delivery|lunch|ravintol|ulkona syö|noutoruo|lounas|restaurang|äta ute|hämtmat", "Restaurants & takeaway"),
    (r"\bbars?\b|drink|\bpubs?\b|nightlife|beer|alcohol|baari|yöelä|olut|krog|nöjesliv|\böl\b", "Bars & nightlife"),
    (r"taxi|taks|uber|bolt|\bcab\b", "Taxis"),
    (r"subscription|streaming|netflix|spotify|tilau|suoratoist|prenumer", "Subscriptions & entertainment"),
    (r"grocer|supermarket|ruokaost|ruokakaup|livsmedel|matbutik|mataffär", "Groceries"),
    (r"shopping|clothes|clothing|shoppail|vaatte|ostoks|kläder", "Shopping"),
    (r"\brent\b|housing|vuokra|asumi|\bhyra|boende", "Housing"),
    (r"travel|flight|\btrip|matkoi|matkat|lento|\bresor|\bresa\b|flyg", "Travel"),
    (r"\bgym|sport|kuntosal|liikunt|urheil|träning", "Sports & wellbeing"),
    (r"electric|energy|utilit|bills?\b|sähkö|lasku|räkning", "Utility bills"),
    (r"entertainment|leisure|cinema|movie|concert|viihde|viihte|vapaa-aika|elokuv|konsert|nöje|fritid|\bbio\b", "Entertainment"),
    (r"fuel|petrol|parking|polttoaine|bensa|tankka|pysäköi|bränsle|bensin|parkering", "Car: fuel & parking"),
    (r"electronic|furniture|elektroniik|huonekal|möbler|elektronik", "Electronics & furniture"),
    (r"health|pharmac|doctor|dentist|terveys|apteek|lääkär|hammas|hälsa|apotek|läkare|tandläk", "Health & pharmacy"),
]
LESSON_KW = [("buy_now_pay_later", r"instal|pay later|bnpl|osamaksu|laskulle|avbetal|betala senare|klarna"), ("interest", r"interest|korko|korot|ränta"),
             ("three_baskets", r"basket|\bkori|korit|korg"), ("emergency_fund", r"emergency|buffer|puskuri|hätävara|buffert"),
             ("irregular_expenses", r"irregular|occasional|satunnai|epäsäännöll|oregelbund"), ("fixed_vs_variable", r"fixed|variable|flexible|kiinte|joustav|\bfasta|flexib|rörlig"),
             ("small_expenses", r"small|latte|add up|pienet|små"), ("payday_cycle", r"payday|palkkapäiv|lönedag"),
             ("safe_to_spend", r"safe to spend|turvalli|tryggt"), ("savings_goals", r"goal|tavoit|\bmål")]
EXPLAIN = r"^(explain|teach|what does|what is|what are|what's|how does|selitä|opeta|mikä on|mitä on|mitä tarkoittaa|mitä ovat|miten toimii|miten .* toimii|förklara|vad är|vad betyder|hur fungerar)"
MONTH_RE = [(r"january", 1), (r"february", 2), (r"march", 3), (r"april", 4), (r"\bmay\b", 5), (r"june", 6), (r"july", 7), (r"august", 8), (r"september|sept\b", 9), (r"october", 10), (r"november", 11), (r"december", 12),
            (r"tammikuu", 1), (r"helmikuu", 2), (r"maaliskuu", 3), (r"huhtikuu", 4), (r"toukokuu", 5), (r"kesäkuu", 6), (r"heinäkuu", 7), (r"elokuu", 8), (r"syyskuu", 9), (r"lokakuu", 10), (r"marraskuu", 11), (r"joulukuu", 12),
            (r"januari", 1), (r"februari", 2), (r"\bmars\b", 3), (r"\bapril", 4), (r"\bmaj\b", 5), (r"\bjuni\b", 6), (r"\bjuli\b", 7), (r"augusti", 8), (r"oktober", 10)]


def _period(q, as_of, default="this_month"):
    if re.search(r"last week|viime viiko|förra veckan", q): return "last_week"
    if re.search(r"this week|tällä viikolla|tämä viikko|den här veckan|denna vecka", q): return "this_week"
    if m := re.search(r"last \d+ (full )?months|viimeiset \d+ (täyttä )?kuukautta|\d+ viime kuukau|\d+ kk\b|senaste \d+ (hela )?månader", q):
        n = re.search(r"\d+", m.group(0)).group()
        return f"last_{n}_months"
    if re.search(r"last month|previous month|viime kuu|edellisen kuun|edellisellä kuulla|förra månaden", q): return "last_month"
    if re.search(r"this month|tässä kuussa|tämä kuu|tällä kuulla|den här månaden|denna månad", q): return "this_month"
    if re.search(r"this year|tänä vuonna|\bi år\b", q): return "ytd"
    for pat, i in MONTH_RE:
        if re.search(pat, q):
            y = as_of.year if i <= as_of.month else as_of.year - 1
            return f"{y}-{i:02d}"
    if re.search(r"\byear\b|vuode|vuosi|\bår\b", q): return "last_12_months"
    return default


def _target(q):
    for pat, g in TARGETS:
        if re.search(pat, q):
            return g
    if re.search(r"everyday|arjen kulut|vardagsutg", q):
        return "everyday"
    return None


def _merchant_in(c, q):
    for m in sorted(c.exp["merchant"].unique(), key=len, reverse=True):
        key = m.lower().split(" - ")[0].strip()
        if len(key) >= 3 and re.search(rf"\b{re.escape(key)}\b", q):
            return m
    return None


def guard_answer(c: Customer, q: str):
    ql = q.lower()
    L = c.lang
    if re.match(EXPLAIN, ql) and any(re.search(p, ql) for _, p in LESSON_KW):
        return None  # learning about a concept is fine: the lesson library answers it
    key = None
    if re.search(r"debt|can'?t pay|cannot pay|unpaid bill|collection agenc|bailiff|velka|velkaa|velat\b|velkoj|en pysty maksamaan|en pysty maksaa|maksuhäiriö|ulosot|perintä|rahahuol|skuld|kan inte betala|inkasso|betalningsanmärkning|utsökning|pengaoro", ql):
        key, help_ = "guard_debt", {"debt": pick(HELP["debt"], L)}
    elif re.search(r"invest|stocks?\b|shares\b|crypto|bitcoin|\betf|index fund|sijoit|osake|osakkei|krypto|rahasto|indeksi|aktie|\bfond|placera|placering", ql) and not re.search(r"emergency|hätävara", ql):
        key, help_ = "guard_invest", {"bank": pick(HELP["bank"], L)}
    elif re.search(r"\bloans?\b|credit|borrow|instal|pay later|bnpl|klarna|\blaina|lainan|luotto|luoton|pikavippi|vippi|osamaksu|\blån|kredit|låna|avbetalning", ql):
        key, help_ = "guard_credit", {"bank": pick(HELP["bank"], L)}
    elif re.search(r"\btax(es|ation|ed)?\b|\bvero(t|ja|n|ilmoitus|tus|palautus|kortti)?\b|verotus|skatt", ql):
        key, help_ = "guard_tax", {"tax": pick(HELP["tax"], L)}
    if not key:
        return None
    text = R(key, L, **help_)
    cards = [{"tool": "get_help_resources", "input": {"topic": "debt" if key == "guard_debt" else "tax" if key == "guard_tax" else "bank"}, "output": {"text": list(help_.values())[0]}}]
    if key == "guard_credit":
        les = lessons(L)["buy_now_pay_later"]
        text += f"\n💡 {les['body']}"
    if key == "guard_debt":
        cards.append({"tool": "get_month_summary", "input": {"period": "last_month"}, "output": c.month_summary("last_month")})
    return {"text": text, "cards": cards, "followups": [pick(Q[k], L) for k in ("advice", "safe", "explain_buffer")], "mode": "guard", "model": None}


def offline_answer(c: Customer, q: str):
    ql = q.lower().strip()
    L = c.lang
    m_ = c._m
    cards = []
    fu = None

    def call(name, **a):
        out = run_tool(c, name, a)
        cards.append({"tool": name, "input": a, "output": out})
        return out

    pct_m = re.search(r"(\d+)\s?(%|percent|per cent|prosent|procent)", ql)
    amt = re.search(r"€\s?(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s?(€|eur\b|euro|euroa|euron)", ql)
    amount = float((amt.group(1) or amt.group(2)).replace(",", ".")) if amt else None
    half = re.search(r"\bhalf|halve|halv|puolit|puoleen", ql)
    target = _target(ql)
    lesson_key = next((k for k, p in LESSON_KW if re.search(p, ql)), None)

    if re.search(r"afford|can i (spend|buy)|\bvaraa|har jag råd|råd att|råd med", ql) and amount:
        r = call("can_i_afford", amount=amount)
        if r["verdict"] == "no":
            text = R("afford_no", L, sts=m_(max(r["safe_to_spend"], 0)), date=r["next_payday"], amount=m_(r["amount"]))
        else:
            text = R("afford_yes", L, tight=R("tight", L) if r["verdict"] == "tight" else "", sts=m_(r["safe_to_spend"]), date=r["next_payday"],
                     amount=m_(r["amount"]), left=m_(r["left_after"]), pd_after=m_(r["per_day_after"]), pd_now=m_(r["per_day_now"]))
        text += "\n" + R("afford_tip", L)
    elif re.search(r"what if|save if|could i save|reduc|cut (down|back)|less on|mitä jos|säästäisin|vähentäisin|vähennän|puolit|karsi|om jag minska|minskade|halver|skulle jag spara|dra ner", ql) and (pct_m or target or half):
        p = float(pct_m.group(1)) if pct_m else (50 if half else 20)
        r = call("simulate_what_if", target=target or "everyday", reduce_pct=p)
        if r["current_monthly"] == 0:
            text = r.get("note", "")
        else:
            text = R("whatif_main", L, target=cap(r["target"]), monthly=m_(r["current_monthly"]), np=plural(r["purchases_per_month"], "purchase", L),
                     p=pct(int(p), L), save_m=m_(r["monthly_saving"]), save_y=m_(r["yearly_saving"]))
            if r.get("fewer_purchases_per_month", 0) >= 0.5:
                text += R("whatif_fewer", L, np=plural(max(r["fewer_purchases_per_month"], 1), "purchase", L))
            text += "\n" + R("whatif_tip", L)
    elif re.match(EXPLAIN, ql) and lesson_key:
        r = call("get_lesson", topic=lesson_key)
        text = f"**{r['title']}.** {r['body']}"
    elif re.search(r"advice|advise|suggest|what should i do|\btips?\b|neuvo|ehdot|vinkk|mitä minun pitäisi|mitä kannattaisi|\bråd(a|et)?\b(?! att| med)|förslag|vad ska jag göra|vad bör jag", ql):
        r = call("get_advice")
        if r["items"]:
            text = R("advice_main", L) + "".join(f"\n**{a['title']}.** {a['why']} {a['action']}" for a in r["items"][:3])
        else:
            text = R("advice_none", L)
    elif re.search(r"safe to save|how much (should|can|could) i save|save each month|savings plan|pitäisi säästää|voin säästää|kannattaa säästää|säästää kuukaudessa|ska jag spara|bör jag spara|kan jag spara|spara varje månad", ql):
        r = call("get_safe_to_save")
        text = (R("save_ok", L, n=len(r["months"]), amount=m_(r["suggested_monthly_saving"])) if r["suggested_monthly_saving"] > 0 else R("save_none", L)) + "\n" + R("save_tip", L)
    elif re.search(r"payday|run(ning)? out|end of (the )?month|before pay|palkkapäiv|rahat loppu|loppuvat|kuun lopussa|lönedag|tar slut|slutet av månaden", ql):
        r = call("get_payday_pattern")
        if not r.get("available"):
            text = r["note"]
        else:
            short = [x["month"] for x in r["months"] if x["gap"] < 0]
            text = R("payday_main", L, day=r["payday"]["day"], p=pct(r["first_week_share"], L))
            if short:
                text += R("payday_short", L, months=", ".join(short))
            if r["small_purchases_per_month"] >= 3:
                text += R("payday_small", L, n=r["small_purchases_per_month"], amount=m_(r["small_purchases_monthly_total"]))
            text += "\n💡 " + lessons(L)["payday_cycle"]["body"]
    elif re.search(r"safe|how much can i spend|left to spend|spend this week|turvallisesti|voin käyttää|käytettävissä|tryggt|kan jag spendera|kvar att spendera", ql):
        r = call("get_safe_to_spend")
        if r["status"] == "over":
            text = R("sts_over", L, over=m_(-r["safe_to_spend"]), date=r["next_payday"], n=r["days_left"])
        else:
            text = R("sts_ok", L, sts=m_(r["safe_to_spend"]), date=r["next_payday"], pd=m_(r["per_day"]), pw=m_(r["per_week"]), rate=pct(int(r["savings_rate"] * 100), L))
        text += "\n" + R("sts_tip", L)
    elif re.search(r"kind of spender|spender am i|personality|my habits|spending style|what type|millainen kuluttaja|kuluttajatyyp|kulutustapa|typ av spenderare|vilken typ|mina vanor", ql):
        r = call("get_spender_profile")
        p = r["primary"]
        text = R("profile_main", L, name=p["name"], ev=p["evidence"])
        if len(r["traits"]) > 1:
            text += R("profile_also", L, names=" & ".join(x["name"] for x in r["traits"][1:]))
        text += f"\n💡 {p['tip']}"
    elif re.search(r"increas|went up|compared|\bvs\.?\b|versus|more than last|changed|kasvoi|kasvaneet|verrattuna|nousi|muuttui|ökade|ökat|jämfört|förändr", ql):
        months = sorted(set(c.df["month"]))
        r = call("compare_periods", period_a="last_month", period_b="this_month") if re.search(r"this month|tässä kuussa|tämä kuu|den här månaden", ql) else call("compare_periods", period_a=months[-3], period_b=months[-2])
        ups = [x for x in r["rows"] if x["change"] > 0][:3]
        if ups:
            items = "; ".join(f"{x['label']} {('+' + pct(x['change_pct'], L)) if x['change_pct'] is not None else R('new', L)} ({m_(x['a'])} → {m_(x['b'])})" for x in ups)
            text = f"{cap(r['period_a'])} → {r['period_b']}: {items}."
        else:
            text = R("compare_none", L, pa=r["period_a"], pb=r["period_b"])
        text += R("compare_total", L, a=m_(r["total_a"]), b=m_(r["total_b"]))
    elif re.search(r"subscription|streaming|recurring|tilauks|tilaukset|suoratoist|toistuv|prenumer|återkommande", ql):
        r = call("get_spending", group_by="merchant", period="last_month", category="Subscriptions & entertainment")
        text = R("subs_main", L, period=cap(r["period"]), total=m_(r["total"]), items=", ".join(f"{x['label']} {m_(x['amount'])}" for x in r["rows"][:5])) + "\n" + R("subs_tip", L)
    elif re.search(r"my age|people (of )?my age|peers|same age|ikäis|ikätoveri|samanikäi|ikäryhm|jämnårig|i min ålder|samma ålder", ql):
        r = call("get_peer_benchmark")
        if not r.get("available"):
            text = R("peers_none", L)
        else:
            fmt = lambda row, v: pct(v, L) if row["unit"] == "%" else m_(v)
            items = "; ".join(R("peers_vs", L, label=x["label"], you=fmt(x, x["you"] or 0), peers=fmt(x, x["peers"])) for x in r["rows"][:4])
            text = R("peers_main", L, title=r["title"], n=r["n"], items=items) + "\n" + R("peers_tip", L)
    elif re.search(r"average|normal|other people|\bfinns\b|benchmark|compare me|compare to|typical|muihin|keskimäär|suomalais|vertaudun|andra finländare|genomsnitt|normalt|jämför jag", ql):
        r = call("get_benchmark")
        f, h = r["rows"]
        text = R("bench_main", L, food=pct(f["you"], L), housing=pct(h["you"], L), caveat=r["caveat"])
    elif m := re.search(r"by (category|merchant|weekday|month)|(kategorioittain|kaupoittain|viikonpäivittäin|kuukausittain)|per (kategori|butik|veckodag|månad)", ql):
        word = next(g for g in m.groups() if g)
        gb = {"kategorioittain": "category", "kaupoittain": "merchant", "viikonpäivittäin": "weekday", "kuukausittain": "month",
              "kategori": "category", "butik": "merchant", "veckodag": "weekday", "månad": "month"}.get(word, word)
        r = call("get_spending", group_by=gb, period=_period(ql, c.as_of, "last_month"), basket="everyday" if gb == "weekday" else None)
        top = sorted(r["rows"], key=lambda x: -x["amount"])[:3]
        text = R("byx_main", L, period=cap(r["period"]), total=m_(r["total"]), everyday=R("everyday_word", L) if gb == "weekday" else "",
                 items=", ".join(f"{x['label']} ({m_(x['amount'])})" for x in top))
        if gb == "weekday":
            text += "\n" + R("weekday_tip", L)
    elif bid := next((b for b in ("fixed", "occasional", "everyday") if any(basket_meta(b, x)["name"].lower() in ql for x in LANGS)), None):
        b = next(x for x in call("get_baskets")["baskets"] if x["id"] == bid)
        text = R("basket_main", L, name=b["name"], amount=m_(b["monthly_avg"]), share=R("share", L, p=pct(b["share_of_income"], L)) if b["share_of_income"] is not None else "",
                 items=", ".join(f"{g['label']} ({m_(g['monthly_avg'])})" for g in b["groups"][:3]) or "–")
        text += f"\n💡 {b['explain']}"
    elif re.search(r"biggest|largest|\btop\b|most money|where does my money|suurimm|isoimm|mihin rahani|största|vart tar", ql):
        r = call("get_spending", group_by="category", period=_period(ql, c.as_of, "last_month"))
        text = R("biggest_main", L, period=cap(r["period"]), items=", ".join(f"{x['label']} ({m_(x['amount'])})" for x in r["rows"][:3]), total=m_(r["total"])) + "\n" + R("biggest_tip", L)
    elif re.search(r"how much|spent|spend|cost|paljonko|kulutin|käytin|kulutan|käytän|meni|menee|hur mycket|spenderade|spenderar|lagt|lägger|kostar", ql) and (target or _merchant_in(c, ql)):
        per = _period(ql, c.as_of)
        merchant = _merchant_in(c, ql)
        if merchant:
            r = call("get_spending", group_by="merchant", period=per, merchant=merchant)
        elif target in BASKET_IDS:
            r = call("get_spending", group_by="category", period=per, basket=target)
        else:
            r = call("get_spending", group_by="merchant", period=per, category=target)
        if r["transactions"] == 0:
            text = R("spent_none", L, period=cap(r["period"]), what=r["filter"])
        else:
            top = r["rows"][0]["label"] if r["rows"] and r["rows"][0]["label"].lower() not in r["filter"].lower() else None
            text = R("spent_main", L, period=cap(r["period"]), what=r["filter"], total=m_(r["total"]), np=plural(r["transactions"], "purchase", L),
                     mostly=R("mostly", L, m=top) if top else "")
    elif lesson_key:
        r = call("get_lesson", topic=lesson_key)
        text = f"**{r['title']}.** {r['body']}"
    else:
        r = call("get_month_summary", period="this_month")
        text = R("fallback", L, period=cap(r["period"]), inc=m_(r["income"]), out=m_(r["spending"]))
        fu = [pick(Q[k], L) for k in ("restaurants", "safe", "advice")]
    return {"text": text, "cards": cards, "followups": fu or followups(L, cards), "model": None}
