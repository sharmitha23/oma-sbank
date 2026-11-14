# OMA demo script (3 minutes)

Open `http://localhost:8000/?customer=CUST01365`. The app opens in Finnish; tap **EN** for an English-speaking jury.
**CUST01365** is a 19-year-old from the S-Pankki dataset: salary on the 15th, about €2,130 a month. "Today" is 30 Sep 2026.

1. **Home (30s).** Her balance isn't spendable money. OMA says this pay cycle's flexible money is used up (€129 over plan), with 15 days to payday, and tells her kindly: essentials only until the 15th. Tap *How is this calculated?*: income since payday, rent of €839 due on 3 Oct, food and commuting for 15 days, a reserve for irregular costs, 10% savings, spending so far. Drag the savings target to show it updates. *(Transparency, customer in control.)*
2. **Spending (40s).** The three baskets: fixed €1,193 (56% of income), occasional €65, everyday €483 (23%). Under "Needs your call" sits a €341 electronics purchase: OMA asks whether it was a replacement or an extra instead of guessing. The pay-cycle chart shows **42% of her everyday spending in payday week** (even pace: 25%). "You vs. people your age" compares her with S-Bank's own 18–24-year-old customers.
3. **Ask OMA (60s).** Tap *Miksi rahat loppuvat ennen palkkapäivää?* (Why am I running out of money before payday?), then *Paljonko säästäisin, jos vähentäisin ulkona syömistä 20 %?* (How much would I save if I ate out 20% less?) → **€292 a year**. Tap **Show the math**: the AI only chose the tool; the bank's engine produced the numbers, and every euro was checked before she saw it.
4. **Safety (20s).** Ask *Kannattaako ottaa pikavippi?* (Should I take a payday loan?). You get a vetted answer, no product advice. Then *Minulla on velkaa enkä pysty maksamaan laskujani* (I have debts and can't pay my bills) → kind words plus free state debt counselling and Takuusäätiö's Velkalinja.
5. **Goals (20s).** *Seuraavat askeleesi* (Your next steps): "Get back to balance", "Plan for irregular costs", "Halve one habit", each triggered by her own numbers. Tap *Make it a goal* on the what-if: €500 buffer, with the date she'd reach it.
6. **Close (10s).** Tap **SV** for Swedish. Switch to **CUST03749** (30 years old, 47% of income on everyday spending) or **CUST01546** (18, on track) to show it's personal, not scripted.

## Mapping to the judging criteria

| Criterion | Where OMA shows it |
|---|---|
| Financial literacy & pedagogy | Three baskets everywhere; pay-cycle chart; 💡 lesson in answers; 10 team-written lessons; spender profile with kind tips; vetted next steps; Statistics Finland + age-peer benchmarks |
| Originality of AI integration | AI as interpreter over 16 deterministic tools; grounding check with retry and fallback; topic guards; Show-the-math; answers come with charts; works offline |
| Mobile UX clarity | 4 tabs, one job each; hero number first; bottom sheets; one-handed at 390px; FI/SV/EN switch |
| Feasibility | Runs on the full S-Pankki dataset (3.6M rows) on a laptop; MCC rules in plain Python; balance-aware; no new bank integration needed |
| S-mobiili integration | Finnish-first and bilingual like S-mobiili; WebView-ready; S-Bank green palette; peer benchmarks from S-Bank's own customers; PSD2 data from other banks would plug into the same engine as extra transactions |

## Likely judge questions

- **"Can the AI hallucinate numbers?"** Every € amount is verified against the engine. Unverified means one rewrite; otherwise the rule engine answers. The UI says which happened.
- **"Could it give bad advice?"** Recommendations only come from a vetted catalogue triggered by the customer's data. Investment, loan and tax questions are caught before the AI.
- **"Why is safe-to-spend €0 for her?"** Because it's honest: she's already spent this cycle's flexible money, and rent is due before payday. OMA also caps the figure by the real balance, so it never suggests money that isn't there.
- **"How do you classify without merchant names?"** By transaction type, MCC code and bank category, and by asking the customer when it's genuinely unclear.
