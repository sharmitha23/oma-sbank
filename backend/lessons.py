"""Short, plain-language money lessons written by the team (not generated), in EN / FI / SV.
The coach may only teach from these and from the advice catalogue in engine.advice()."""
from i18n import norm

_L = {
    "three_baskets": (
        ("The three baskets", "Every euro you spend lands in one of three baskets. Fixed essentials (rent, bills, groceries) come every month. Occasional essentials (a broken washing machine, the dentist) are necessary but irregular. Everyday spending (coffees, takeaway, taxis) is flexible. Plan the first, save for the second, and steer the third."),
        ("Kolme koria", "Jokainen käyttämäsi euro päätyy yhteen kolmesta korista. Kiinteät pakolliset (vuokra, laskut, ruoka) tulevat joka kuukausi. Satunnaiset pakolliset (rikkoutunut pesukone, hammaslääkäri) ovat välttämättömiä mutta epäsäännöllisiä. Arjen kulutus (kahvit, noutoruoka, taksit) on joustavaa. Suunnittele ensimmäinen, varaudu toiseen ja ohjaa kolmatta."),
        ("De tre korgarna", "Varje euro du spenderar hamnar i en av tre korgar. Fasta nödvändiga (hyra, räkningar, mat) kommer varje månad. Oregelbundna nödvändiga (en trasig tvättmaskin, tandläkaren) är nödvändiga men oregelbundna. Vardagsutgifter (kaffe, hämtmat, taxi) är flexibla. Planera den första, spara för den andra och styr den tredje."),
    ),
    "small_expenses": (
        ("Why small purchases add up", "A 4.50 € coffee feels like nothing, and that's the point: small amounts don't trigger the 'is this worth it?' check. Twenty a month is 90 €, and 1,080 € a year. You don't need to quit; you need to notice."),
        ("Miksi pienet ostot kasvavat suuriksi", "4,50 euron kahvi tuntuu mitättömältä, ja juuri siksi: pienet summat eivät herätä kysymystä 'onko tämä sen arvoista?'. Kaksikymmentä kuukaudessa on 90 €, ja vuodessa 1 080 €. Lopettaa ei tarvitse, kunhan huomaat."),
        ("Varför små köp blir stora", "Ett kaffe för 4,50 € känns som ingenting, och det är just poängen: små belopp väcker inte frågan 'är det värt det?'. Tjugo i månaden blir 90 €, och 1 080 € per år. Du behöver inte sluta, bara lägga märke till det."),
    ),
    "fixed_vs_variable": (
        ("Fixed vs. flexible costs", "Fixed costs are hard to change quickly (you can't renegotiate rent on a Tuesday). Flexible costs change with every decision. That's why most quick wins come from flexible spending, while big wins come from rare fixed-cost decisions like where you live."),
        ("Kiinteät ja joustavat menot", "Kiinteitä menoja on vaikea muuttaa nopeasti (vuokraa ei neuvotella uusiksi tiistaina). Joustavat menot muuttuvat jokaisen päätöksen myötä. Siksi nopeat voitot löytyvät yleensä joustavista menoista, ja isot voitot harvoista kiinteistä päätöksistä, kuten asumisesta."),
        ("Fasta och flexibla kostnader", "Fasta kostnader är svåra att ändra snabbt (hyran omförhandlas inte en tisdag). Flexibla kostnader ändras med varje beslut. Därför kommer snabba vinster oftast från flexibla utgifter, och stora vinster från sällsynta beslut om fasta kostnader, som var du bor."),
    ),
    "irregular_expenses": (
        ("Irregular costs aren't surprises", "Any single repair is unpredictable; that you'll have some repairs in a year is not. If irregular must-haves cost you 600 € a year, putting 50 € aside every month turns a future crisis into a planned payment."),
        ("Epäsäännölliset menot eivät ole yllätyksiä", "Yksittäinen korjaus on arvaamaton, mutta se, että vuoden aikana jotain korjattavaa tulee, ei ole. Jos satunnaiset pakolliset menot ovat 600 € vuodessa, 50 € kuukausittainen varaus tekee tulevasta kriisistä suunnitellun maksun."),
        ("Oregelbundna kostnader är inga överraskningar", "En enskild reparation går inte att förutse, men att något behöver repareras under ett år gör det. Om oregelbundna måsten kostar 600 € per år gör 50 € i månaden en framtida kris till en planerad betalning."),
    ),
    "emergency_fund": (
        ("Your emergency buffer", "A buffer is money set aside only for real surprises: job loss, illness, a big repair. A common starting goal is one month of fixed essentials; a fuller target is three months. Keep it separate from everyday money so it doesn't quietly get spent."),
        ("Puskuri yllätysten varalle", "Puskuri on rahaa vain todellisiin yllätyksiin: työn menetykseen, sairauteen tai isoon korjaukseen. Yleinen ensimmäinen tavoite on yhden kuukauden kiinteät menot, laajempi tavoite kolme kuukautta. Pidä se erillään arjen rahoista, ettei se huomaamatta kulu."),
        ("Din buffert", "En buffert är pengar som bara är till för verkliga överraskningar: arbetslöshet, sjukdom, en stor reparation. Ett vanligt första mål är en månads fasta utgifter, ett större mål tre månader. Håll den skild från vardagspengarna så att den inte försvinner obemärkt."),
    ),
    "safe_to_spend": (
        ("What 'safe to spend' means", "Your balance is not the same as spendable money. Safe-to-spend starts from your income this pay cycle, then subtracts bills still coming, groceries until payday, a reserve for irregular costs and your savings target. What's left is genuinely yours to enjoy."),
        ("Mitä 'turvallisesti käytettävissä' tarkoittaa", "Tilin saldo ei ole sama asia kuin käytettävissä oleva raha. Laskelma lähtee tämän palkkajakson tuloista ja vähentää niistä tulevat laskut, ruoan palkkapäivään asti, varauksen satunnaisiin menoihin sekä säästötavoitteesi. Se mitä jää, on aidosti sinun käytettävissäsi."),
        ("Vad 'tryggt att spendera' betyder", "Ditt saldo är inte samma sak som pengar du kan spendera. Beräkningen utgår från inkomsterna denna löneperiod och drar av kommande räkningar, mat fram till lönedagen, en reserv för oregelbundna kostnader och ditt sparmål. Det som blir kvar är verkligen ditt att använda."),
    ),
    "payday_cycle": (
        ("The payday effect", "Right after payday the account looks full, so spending feels safe. But the money has to last until the next payday. Splitting your flexible money into weekly amounts keeps week four as good as week one."),
        ("Palkkapäiväilmiö", "Heti palkkapäivän jälkeen tili näyttää täydeltä, joten kuluttaminen tuntuu turvalliselta. Rahan pitää kuitenkin riittää seuraavaan palkkapäivään. Kun jaat vapaan rahan viikkosummiin, neljäs viikko on yhtä hyvä kuin ensimmäinen."),
        ("Lönedagseffekten", "Direkt efter lönedagen ser kontot fullt ut, så det känns tryggt att spendera. Men pengarna ska räcka till nästa lönedag. Om du delar upp dina fria pengar i veckobelopp blir vecka fyra lika bra som vecka ett."),
    ),
    "savings_goals": (
        ("Goals that actually work", "A goal works when it's specific (a name, an amount, a date) and automatic. Save at the start of the month, right after payday, not with what's left at the end. Even 20 € a month builds the habit."),
        ("Tavoitteet, jotka toimivat", "Tavoite toimii, kun se on tarkka (nimi, summa, päivämäärä) ja automaattinen. Säästä kuun alussa heti palkkapäivänä, älä siitä mitä lopussa jää. Jo 20 € kuukaudessa rakentaa tavan."),
        ("Mål som fungerar", "Ett mål fungerar när det är konkret (namn, belopp, datum) och automatiskt. Spara i början av månaden, direkt efter lönedagen, inte det som blir kvar i slutet. Redan 20 € i månaden bygger vanan."),
    ),
    "buy_now_pay_later": (
        ("Instalments and 'pay later'", "Instalment plans and 'pay later' make things feel cheaper because you see a small monthly amount, not the total. Fees and interest can make the total clearly higher, and several small plans add up. Before saying yes, check the total cost and whether the monthly amount fits your safe-to-spend."),
        ("Osamaksut ja 'maksa myöhemmin'", "Osamaksu ja laskulle ostaminen saavat asiat tuntumaan halvemmilta, koska näet pienen kuukausierän etkä kokonaissummaa. Kulut ja korot voivat nostaa kokonaishintaa selvästi, ja monta pientä erää kertyy yhteen. Tarkista ennen kuin sanot kyllä: mikä on kokonaishinta ja mahtuuko kuukausierä käytettävissä olevaan rahaasi."),
        ("Avbetalning och 'betala senare'", "Avbetalning och 'betala senare' får saker att kännas billigare eftersom du ser ett litet månadsbelopp och inte totalen. Avgifter och ränta kan göra totalen klart högre, och flera små avtal blir mycket tillsammans. Kontrollera innan du säger ja: vad är totalkostnaden och ryms månadsbeloppet i dina fria pengar?"),
    ),
    "interest": (
        ("How interest works", "Interest is the price of borrowed money. On a loan or credit it's charged on what you still owe, so the longer you take to pay, the more it costs. On savings it works the other way: interest is paid to you, and over years it also grows on earlier interest (compound interest)."),
        ("Miten korko toimii", "Korko on lainatun rahan hinta. Lainassa tai luotossa korkoa maksetaan siitä, mitä on vielä maksamatta, joten mitä pidempään maksat, sitä kalliimmaksi se tulee. Säästöissä toimii päinvastoin: korko maksetaan sinulle, ja vuosien mittaan korolle kertyy korkoa (korkoa korolle)."),
        ("Hur ränta fungerar", "Ränta är priset för lånade pengar. På ett lån eller en kredit betalar du ränta på det du ännu är skyldig, så ju längre du betalar, desto dyrare blir det. På sparande fungerar det tvärtom: räntan betalas till dig, och med åren växer ränta på ränta."),
    ),
}

_I = {"en": 0, "fi": 1, "sv": 2}


def lessons(lang):
    return {k: {"title": v[_I[norm(lang)]][0], "body": v[_I[norm(lang)]][1]} for k, v in _L.items()}


LESSON_IDS = list(_L)
