# Atelier

In Atelier volgt het atelierteam tijdens de festivaldagen de werkkledij op. Medewerkers van ploegen die op een plaats werken met eigen kledij (VIP, RW terras, ...) krijgen die kledij (T-shirts, hoodies, ...) bij het begin van hun shift en geven ze na de shift terug. Atelier houdt bij wat uitgegeven en teruggebracht werd, zodat alles traceerbaar blijft.

> Deze module wordt in blokken gebouwd. Nu klaar: de masterdata (artikelen en maten), de reservaties (personen en pakket per ploeg per festival), de stock (ontvangst, wassen, afboeken, telling, te bestellen), de balie (ophalen en terugbrengen) en de polsbandscans (aan de balie en via Test-scan; de scans zelf staan in de module Scans). Daarna volgt het opvolgen van elk kledingstuk via RFID (Scans).

## [overview | atelier.kpi] KPI overzicht
De startpagina van Atelier. Het blok **Balie** toont hoeveel stuks vandaag uitgegeven werden, hoeveel stuks nog niet terug zijn en hoeveel personen nog kledij in bezit hebben. Het blok **Masterdata** toont hoeveel actieve artikelen en maten er zijn en hoeveel artikelmaten uitgegeven kunnen worden. Het blok **Reservaties** toont per festival van het gekozen **seizoen** de personen en stuks per dag, het aantal ploegen met een reservatie en hoeveel daarvan nog geen pakket hebben. De kolom **Vergeten?** telt de ploegen die op een ander festival van dit seizoen een reservatie hebben, maar hier nog niets (geen personen, geen opmerking). Klik op het getal voor de namen en een link naar de reservaties van dat festival. Komt een ploeg echt niet, vul dan 0 personen in met een opmerking (bv. "komt niet"). Het blok **Stock** toont de stuks die beschikbaar zijn, te wassen zijn en uitgegeven zijn, en hoeveel maten onder hun minimumstock zitten. Het blok **Gewassen** toont voor hetzelfde seizoen hoeveel stuks er gewassen werden: het totaal, en per festival per dag. Een wasbeurt telt voor het festival dat op die dag liep; wat in de dagen na een festival gewassen werd, staat onder **Geen festival** van dat seizoen. Ongedaan gemaakte wasbeurten tellen niet mee.

![Het KPI overzicht](overview.png)

## [desk | atelier.desk] Uitgifte & inname
De balie. Kies bovenaan het **festival**, de **dag** (standaard vandaag) en de **scanner van deze balie** (wordt onthouden in deze browser).

**Polsbandscans**: scant een medewerker zijn polsband aan deze balie, dan verschijnt hij binnen enkele seconden bovenaan ("Gescand: …"). Kies dan **Ophalen** (naam, polsbandnummer, ploeg en maat staan al ingevuld) of **Terugbrengen** (zijn stuks staan meteen klaar). Met **Negeren** verdwijnt de scan. Komt er een scan binnen tijdens een transactie, dan wacht hij tot je klaar bent. Het e-mailadres is optioneel. **Elke transactie begint met de keuze tussen twee grote knoppen: Ophalen of Terugbrengen** (of toets 1 / 2). Na het boeken (of **Annuleren**) kom je terug bij die keuze voor de volgende persoon.

**Ophalen**
1. Vul **voornaam** en **familienaam** in: samen bepalen ze wie de persoon is. Is de persoon al gekend, dan worden e-mailadres, polsbandnummer en ploeg ingevuld en zie je wat hij of zij nog in bezit heeft.
2. Vul eventueel het **e-mailadres** in (optioneel; meerdere personen mogen hetzelfde adres hebben) en het **polsbandnummer** (het nummer op de polsband van dit festival; uniek binnen het festival — elk festival heeft nieuwe polsbanden). Het polsbandnummer is verplicht als dat in **Instellingen** aanstaat. Een ingevuld e-mailadres (gekende persoon of scan) wordt om privacyredenen (GDPR) maar deels getoond, bv. fr***@gm***.com; met **Wijzig** maak je het vak leeg en typ je een nieuw adres. Ook bij Terugbrengen staat het e-mailadres zo afgeschermd. Zodra er een ploeg gekozen is, staat rechts (op de hoogte van "Gekend: …") een **contacticoon**: klik erop voor de **ploegverantwoordelijken** van die ploeg in dit seizoen (naam, telefoon, e-mail, opmerkingen), zoals ingevuld bij MasterData > Teams > Ploegverantwoordelijken. Lukt scannen met de scanners niet? Klik dan op het **camera-icoon** naast het polsbandnummer en houd de QR-code van de polsband voor de camera van de pc: het nummer wordt ingevuld.
3. Kies de **ploeg** (enkel ploegen met een pakket op dit festival).
4. Per artikel van het pakket kies je de **maat** (1 stuk per artikel); tussen haakjes staat hoeveel er beschikbaar zijn. Elk artikel is **optioneel**: klik de gekozen maat nog eens om het artikel over te slaan. Heeft een artikel maar één maat in stock (bv. OneSize), dan staat die al aangeduid. Minstens één artikel is nodig; naast de knop staat wat nog ontbreekt.

Heeft een gekende persoon op dit festival al een **ander polsbandnummer**, dan vraagt de balie of het dezelfde persoon is met een nieuwe polsband. Is het iemand anders met dezelfde naam, kies dan Annuleren en vul de naam aan (bv. met een tweede voornaam): twee mensen met exact dezelfde naam zijn voor de balie één persoon.

Een artikel dat de persoon nog niet teruggebracht heeft, kan niet opnieuw meegegeven worden. Een oranje kader toont wat de persoon nog heeft, met de knop **Eerst terugbrengen** die meteen het terugbrengen voor die persoon opent. Alle andere artikels kan de persoon wel ophalen — ook meerdere keren per dag.
5. Klik op **Uitgeven** (of Enter).

**De reservatie is een limiet.** De teller toont hoeveel personen van de ploeg op dit festival **nu kledij in bezit** hebben, tegenover het gereserveerde aantal personen. Is dat aantal bereikt, dan weigert de balie een **nieuwe** persoon (wie al iets heeft, mag wel een ander artikel ophalen); wie alles terugbracht, maakt een plaats vrij. Met het recht **Wijzigen** op Uitgifte & inname vraagt de balie of je **toch wil uitgeven** boven de reservatie; zonder dat recht verhoog je eerst de reservatie op **Reservaties**.

**Terugbrengen**
1. Zoek de persoon op naam, e-mailadres of polsbandnummer (enkel wie nog kledij heeft).
2. Alle stuks staan aangevinkt; vink af wat niet terug is (dat blijft openstaan). Is er iets afgevinkt, dan vraagt de balie eerst bevestiging met de lijst van wat bij de persoon blijft.
3. Heeft een stuk een probleem (beschadigd, zeer vuil, ...), kies dan per stuk een **retourstatus** in de keuzelijst. Dat is enkel een opmerking: het stuk gaat gewoon naar **Te wassen**, en je ziet het terug op **Retourproblemen**.
4. Klik op **Terugnemen**: de stuks gaan naar **Te wassen**.

**E-mail**: heeft de persoon een e-mailadres, dan krijgt hij of zij na elke Ophalen een mail **Uitgifte** en na elke Terugbrengen één mail **Inname** (ook als de stuks van verschillende uitgiftes komen). De teksten stel je in op **Instellingen > E-mails**.

Met het recht Wijzigen kan je een uitgifte waarvan nog niets terug is **annuleren** (de stuks gaan terug naar beschikbaar).

**Op de Raspberry Pi (RWCrew Pi)**: met de RFID-lezer verloopt hetzelfde zonder typen. Kies één keer seizoen, festival, dag en de polsbandscanner van de balie (wordt onthouden). Elke polsbandscan verschijnt als kaart met **Ophalen**, **Terugbrengen** en **Negeren**; het e-mailadres staat er, net als op de website, maar deels (bv. fr***@gm***.com). Bij Ophalen leg je de stukken op de lezer: elk stuk met een tag (zie **RFID-tags koppelen**) wordt meteen getoond, groen als het geboekt wordt, oranje met de reden als het niet kan (niet in het pakket, nog in bezit, tweede stuk van hetzelfde artikel, bij iemand anders, geen stock). Bij Terugbrengen worden de gelezen stuks aangevinkt (ook stuks die zonder tag meegingen, per artikel); je kan nog met de hand aan- of afvinken en een retourstatus kiezen. **Bevestigen** boekt het, met dezelfde regels, mails en rechten als op de website. Zonder verbinding met RWCrew wordt er niets geboekt (rode balk).

![De balie: Ophalen of Terugbrengen](desk.png)

## [open | atelier.open] Openstaand
Alle kledij die opgehaald werd maar nog niet terug is, **gegroepeerd per ploeg en dan per persoon** (met polsbandnummer; het e-mailadres staat er om privacyredenen (GDPR) niet bij), met daaronder elk stuk: festival, dag, artikel, maat en wanneer het opgehaald werd. Kies bovenaan het festival en eventueel de dag, of **Alle festivals** voor een volledig overzicht van het seizoen (dan zonder dagkeuze; typ in de filter van de kolom **Festival** om toch één festival te tonen). Boven elke kolom staat een **filterveld**: typ er een deel van een naam, ploeg, artikel, … in om de lijst te verkleinen; de totalen volgen de filter. Komt iets nooit terug, klik dan bij de persoon op **Afboeken** (met het recht Aanmaken op het scherm Afboeken), vink de stuks aan en bevestig: ze verlaten de stock definitief met de reden "Niet teruggebracht", staan niet meer open en de persoon kan dat artikel opnieuw ophalen. De persoon krijgt hiervan geen mail, en deze afboeking kan niet ongedaan gemaakt worden. **Stock > Afboeken** is er enkel voor stuks die in de winkel liggen (beschikbaar of te wassen).

Heb je de rechten van de balie, dan staat bij elke persoon de knop **Inname**: die opent hetzelfde scherm als Terugbrengen aan de balie, voor deze persoon, met alles wat die nog in bezit heeft (ook buiten de gekozen dag). De persoon krijgt de gewone Inname-mail.

Met de knop **Excel** download je wat op het scherm staat, ook met de filters die je gebruikt (zonder e-mailadressen).

![Openstaand](open.png)

## [returnissues | atelier.returnissues] Retourproblemen
![Retourproblemen](return-issues.png)

Alle kledij die teruggebracht werd met een **retourstatus**, de nieuwste bovenaan: status, artikel, maat, festival, ploeg, persoon, polsband, dag, wanneer teruggebracht en door wie geboekt. Kies bovenaan het festival en eventueel de dag, of **Alle festivals** voor het hele seizoen (filter dan per festival in de kolom **Festival**); boven elke kolom staat een tekstfilter. Dit scherm is enkel om te bekijken: een stuk dat niet meer bruikbaar is, boek je af via **Afboeken**. Met de knop **Excel** download je wat op het scherm staat, ook met de filters die je gebruikt.

## [tags | atelier.tags] RFID-tags koppelen (Raspberry Pi)
Dit scherm bestaat enkel op de **Raspberry Pi-app (RWCrew Pi)** met de RFID-lezer, niet op de website. Je geeft er nieuwe kledingstukken hun RFID-tag: de tag zegt voortaan welk **artikel in welke maat** het stuk is.

1. Kies het **artikel** (zoekbaar) en daarna de **maat** (grote knoppen; per maat zie je hoeveel stuks al een tag hebben). Een artikel met één maat (OneSize) is meteen gekozen.
2. Leg de stukken van die maat op de lezer. Elke gelezen tag krijgt een regel: **Nieuw — wordt gekoppeld** (groen), **Al deze maat** (groen, er verandert niets), **Al …** een ander stuk (oranje) of geweigerd (rood: de tag hoort bij een StockMaster-product of kar, of het stuk is uitgegeven aan iemand).
3. Elke tag die gekoppeld kan worden, heeft een **vinkje** (standaard aan): tik een regel aan om een tag die per ongeluk mee gelezen werd **uit te vinken**.
4. Tik op **Koppelen**: enkel de aangevinkte tags worden gekoppeld. Staan er aangevinkte tags bij die al een ander stuk zijn, dan vraagt de Pi eerst of je ze toch wil wijzigen.

Met het recht Bekijken zie je het scherm, met Aanmaken mag je koppelen. De stock zelf verandert niet: die blijft per maat geteld; de tag zegt enkel welk fysiek stuk bij wie is.

## [massreturn | atelier.massreturn] Massa-inname (Raspberry Pi)
Dit scherm bestaat enkel op de **Raspberry Pi-app (RWCrew Pi)** met de RFID-lezer. Een ploeg verzamelt in de loop van de dag de vuile kledij in een **bak** en brengt die naar het atelier: met Massa-inname neem je de hele bak in één keer in, zonder elke persoon apart aan de balie te zetten.

1. Zet de bak op de lezer. Het **grote getal** toont hoeveel tags (stukken) er in de bak gelezen zijn.
2. Rechts staan de stukken **per persoon** die ze uit heeft (artikel en maat, met het tagnummer).
3. Staat er een **rode regel** bij (onbekende tag, tag van een StockMaster-product of kar, inactieve tag, of een stuk dat niet uitgegeven is), dan kan je niet bevestigen: haal dat stuk uit de bak en tik **Opnieuw lezen**.
4. Tik **Bevestigen** (of druk op de bevestigknop van de Pi): elk stuk wordt per persoon teruggebracht (naar de was), en elke persoon met een e-mailadres krijgt zijn gewone **Inname-mail**.

Met het recht Bekijken zie je de tegel, met Aanmaken mag je bevestigen. In **Tag-historiek** staan deze innames met het label **Pi**.

## [taghistory | atelier.taghistory] Tag-historiek
Alles wat één kledingstuk meemaakte, op basis van zijn **RFID-tag (EPC)**. Typ of plak het tagnummer en klik **Zoeken**; vanuit **Openstaand** en **Retourproblemen** open je het ook door op een EPC te klikken.

Bovenaan staat de tag zoals **Scans > Tagbeheer** hem nu kent: welk stuk (artikel en maat), de status en wanneer, door welke scanner en waar hij laatst gelezen werd. Daaronder elke **uitgifte en inname** met die EPC, de nieuwste bovenaan: wanneer uitgegeven en teruggebracht (of nog uit, afgeboekt, geannuleerd), persoon, ploeg, festival, dag, stuk, wie het boekte en een eventuele retourstatus. Een label toont **waar** het geboekt werd: **Pi** (RWCrew Pi met de RFID-lezer) of **Website** (de balie op de website).

Het tagnummer wordt bij elke uitgifte en inname met de Pi **mee bewaard**: ook als de tag later in Tagbeheer verwijderd of aan een ander stuk gekoppeld wordt, blijft de historiek kloppen. Dit scherm is enkel om te bekijken.

## [reservations | atelier.reservations] Reservaties
Alles per festival op één pagina: per ploeg **hoeveel mensen** kledij nodig hebben en **wat elke persoon krijgt** (het pakket, bv. 2 T-shirts en 1 hoodie). Een ploeg werkt **elke festivaldag** met dat aantal mensen en brengt de kledij **elke avond terug**, dus elke dag is er opnieuw *personen × pakket* nodig. De maat zit niet in het pakket: die wordt aan de balie gekozen.

1. Kies bovenaan het **seizoen** en het **festival**. De tabel toont alle actieve ploegen.
2. Vul per ploeg het aantal **personen** in, eventueel met een **opmerking**.
3. Klik bij de ploeg op **Pakket** om de artikelen te kiezen (Artikel toevoegen, lijn verwijderen). Het **aantal per persoon** is altijd **1**: aan de balie krijgt elke persoon één stuk per artikel.
4. Gewijzigde lijnen kleuren geel. Klik op **Opslaan** om alles in één keer te bewaren. Bij elke ploeg zie je wie het laatst iets wijzigde en wanneer.

**Festivals ingevuld**: per ploeg hoeveel van de festivals die de ploeg in **Altsien Select** koos al personen hebben (bv. *3 / 5*). Groen = alles ingevuld, oranje = nog niet; beweeg over het getal om per festival te zien wat ontbreekt. Koos de ploeg nog niets, dan staat er "geen selectie". Koos ze andere festivals maar niet dit, dan staat "niet gekozen" bij de ploegnaam.

Met de knop boven de tabel kies je **Alle ploegen** of **Enkel met pakket** (de ploegen die op dit festival een pakket hebben). Boven elke kolom staat een **filterveld**. Een gewijzigde, nog niet opgeslagen ploeg blijft altijd zichtbaar; de totalen tellen altijd alle ploegen.

Het pakket geldt enkel voor dit festival. Een ploeg met personen maar zonder pakket krijgt een waarschuwing. Een reservatie zonder personen, opmerking en pakket verdwijnt.

**Kopiëren van vorig jaar**: bestond hetzelfde festival vorig seizoen (zelfde naam, het jaartal telt niet mee), dan zie je boven de tabel de reservaties van toen. Vink de ploegen aan en klik op **Kopiëren**. Het pakket wordt aangevuld (er wordt nooit iets verwijderd, niet-actieve artikels worden overgeslagen) en het aantal personen wordt enkel overgenomen als het dit jaar nog 0 is.

Reservaties en pakketlijnen kan je ook in bulk inladen op **Data Upload/Download**.

![Reservaties](reservations.png)

## [preparation | atelier.preparation] Voorbereiden
Wat de winkel **elke festivaldag** klaarlegt (elke dag is hetzelfde, want de kledij komt elke avond terug).

- **Totaal uit de winkel per dag**: per artikel het aantal stuks, met de **geschatte maten**. Die schatting komt van de maatverdeling (%) die je bij het artikel invult (Artikelen, kolom % per maat). Heeft een artikel geen volledige maatverdeling, dan wordt gelijk verdeeld. Naast elke maat staat de beschikbare stock: **rood** als het atelier te weinig stuks in bezit heeft, **oranje** als er genoeg zijn maar nog niet alles gewassen of terug is.
- **Per ploeg**: het pakket van elke ploeg voor het aantal personen. De maat wordt aan de balie gekozen.

**Picklijst afdrukken**: kies de dag en klik op de knop. Zonder aangevinkte ploegen staan alle ploegen erin; vink je ploegen aan, dan enkel die (en het totaal enkel voor hen). De picklijst heeft per ploeg een vakje om af te vinken wanneer het pakket klaar ligt.

![Voorbereiden](preparation.png)

## [stock | atelier.stock] Stock
Per artikel en maat hoeveel stuks **beschikbaar** zijn, **te wassen** zijn (teruggebracht na een shift) en **uitgegeven** zijn, met het totaal en de minimumstock. **Met RFID-tag** telt de stuks met een actieve tag in Scans > Tagbeheer (gekoppeld met de Raspberry Pi; verloren of beschadigde tags tellen niet), **Zonder tag** de stuks die er nog een nodig hebben (oranje). Een maat onder de minimumstock kleurt oranje; boven elke Atelier-pagina staat dan ook een oranje melding. Met **Enkel onder minimumstock** zie je alleen die maten.

![Stock](stock.png)

## [receipt | atelier.receipt] Ontvangst
Nieuwe kledij boeken: kies met **Artikel toevoegen** de artikelen, vul per maat het aantal in en eventueel een **referentie** (bv. de leveringsbon). Klik op **Inboeken**: de stuks zijn meteen beschikbaar. Enkel actieve artikelen en maten kunnen ontvangen worden.

![Ontvangst](receipt.png)

## [wash | atelier.wash] Wassen
Het scherm toont alle artikelen met stuks **te wassen**. Vul per maat in hoeveel stuks gewassen zijn (of klik op **Alles**) en klik op **Gewassen boeken**: ze worden weer beschikbaar.

![Wassen](wash.png)

## [writeoff | atelier.writeoff] Afboeken
Kledij die definitief uit de stock gaat. Kies eerst of je afboekt uit **Beschikbaar** of **Te wassen**, dan de artikelen en aantallen, en de **reden**: beschadigd, verloren, niet teruggebracht of andere (dan is een opmerking verplicht).

![Afboeken](write-off.png)

## [count | atelier.count] Telling
Kies de artikelen die je geteld hebt. Per maat staan de geboekte aantallen al ingevuld; pas aan wat je telde (beschikbaar en te wassen). Enkel de **verschillen** worden geboekt, als één telling. Uitgegeven stuks tel je hier niet.

![Telling](count.png)

## [bookings | atelier.bookings] Boekingen
Alle stockboekingen, de nieuwste eerst, met een filter op soort. Bekijk de lijnen, druk de **boekingsbon** af (PDF) of klik op **Ongedaan maken** (enkel met het recht Wijzigen): er wordt een tegenboeking gemaakt en de oorspronkelijke blijft zichtbaar als ongedaan gemaakt. Dat lukt enkel als de stuks er nog zijn (maak dan eerst de latere boeking ongedaan).

Boekingen uit de lijsten van vorig jaar (ingeladen door de superbeheerder met de massatest) staan op hun oorspronkelijke datum en uur; voor die uitgiftes en innames werd geen mail verstuurd.

Een **Uitgifte** of **Inname** van de balie toont bij **Lijnen bekijken** (en op de boekingsbon) ook de **stuks**: artikel, maat, persoon en het **RFID-tagnummer (EPC)** als het stuk met de Raspberry Pi gelezen werd; klik op de EPC voor de **Tag-historiek**. Een label **Pi** in de lijst toont dat de boeking op RWCrew Pi gebeurde.

![Boekingen](bookings.png)

## [orderneeds | atelier.orderneeds] Te bestellen
Per maat wat er te kort is voor het gekozen **seizoen**: de hoogste dagbehoefte over de festivals (personen × pakket, geschat per maat met de maatverdeling van het artikel) min alles wat het atelier in bezit heeft (beschikbaar + te wassen + uitgegeven). Met **Afdrukken** krijg je de bestellijst als PDF.

![Te bestellen](order-needs.png)

## [articles | atelier.articles] Artikelen
De catalogus van de werkkledij, bv. "T-shirt crew zwart" of "Hoodie VIP". Een artikel is altijd alle maten samen.

1. Klik op **Nieuw artikel**.
2. Vul de **code** (uniek, bv. TS-CREW-ZW) en de **naam** in. Kleur, omschrijving en aankoopprijs per stuk zijn optioneel.
3. Vink onder **Maten** aan in welke maten het artikel bestaat, gegroepeerd per Dames, Heren en Unisex. Per maat kan je een **minimumstock** en het **aandeel (%)** in de maatverdeling invullen (samen 100%); daarmee schat Voorbereiden hoeveel stuks per maat klaar te leggen.
4. Kies eventueel een **foto** (PNG, JPEG of WebP, max. 5 MB).
5. Klik op **Opslaan**.

Een artikel dat in het pakket van een reservatie zit, kan niet verwijderd worden: zet het dan op **niet actief**. Een niet-actief artikel kan niet meer aan een pakket toegevoegd worden.

![Artikelen](articles.png)

## [sizes | atelier.sizes] Maten
De lijst met maten die je bij een artikel kan aanvinken. Een maat is een **naam** (XS, S, M, ..., OneSize) plus een **pasvorm**: Dames, Heren of Unisex. "M · Dames" en "M · Heren" zijn dus twee aparte maten. Gebruik **OneSize · Unisex** voor artikels die maar in één maat bestaan.

1. Klik op **Nieuwe maat**, vul de naam in, kies de pasvorm en een **volgorde** (lager = eerder in de lijst).
2. Met de filter bovenaan toon je enkel de maten van één pasvorm.

Een maat die bij een artikel gebruikt wordt, kan niet verwijderd worden: zet ze dan op niet actief.

![Maten](sizes.png)


## [returnstatuses | atelier.returnstatuses] Retourstatussen
De lijst met wat er mis kan zijn met een teruggebracht stuk, zoals "Beschadigd" of "Zeer vuil". De balie kiest dit per stuk bij **Terugbrengen**.

1. Klik op **Nieuwe retourstatus** en vul de naam in.
2. Een status die al gebruikt werd, kan niet verwijderd worden: zet ze dan op niet actief. Ze staat dan niet meer in de keuzelijst, maar blijft zichtbaar bij de stuks die ze al hebben.

In bulk kan dit via **Data Upload/Download**.

![Retourstatussen](return-statuses.png)

## [dataupload | atelier.dataupload] Data Upload/Download
Per tabel een tegel om een **sjabloon** te downloaden, een ingevuld bestand te **uploaden** en de huidige gegevens te **exporteren**.

- **Retourstatussen**: een rij wordt gezocht op **id** en anders op naam; een gevonden status wordt gewijzigd, anders komt er een nieuwe bij. Er wordt nooit iets verwijderd.
- **Maten** en **Artikelen**: een rij wordt gezocht op **id** (de eerste kolom van de export) en anders op naam + pasvorm (maten) of code (artikelen); een gevonden record wordt gewijzigd, anders komt er een nieuw bij. Zo kan je ook een export van een andere omgeving (bv. localhost naar test) opladen.
- **Artikelmaten** (artikelcode + maat + pasvorm), **Reservaties** (seizoen + festival + ploeg) en **Pakketlijnen** (seizoen + festival + ploeg + artikelcode): een bestaande combinatie wordt bijgewerkt, een nieuwe toegevoegd.
- Pasvorm mag als women/men/unisex of Dames/Heren/Unisex.

Na het uploaden zie je per rij of ze aangemaakt, bijgewerkt, ongewijzigd of fout is, met de reden.

![Data Upload/Download](data-upload.png)

## [settings | atelier.settings] Instellingen
- **Polsband verplicht bij Ophalen**: staat dit aan, dan kan aan de balie niets opgehaald worden zonder polsbandnummer (gescand of getypt). Elk festival heeft nieuwe polsbanden: een nummer is uniek binnen één festival.

De polsbandscans zelf (de webhook, de scanners met hun naam en alle ontvangen berichten) staan in de module **Scans**. Aan de balie verschijnt een scan enkel als de ploeg een reservatie met pakket heeft op een festival van het seizoen, of als de ploegnaam niet herkend werd: dan kiest de balie zelf de ploeg.

## [scantest | atelier.scantest] Test-scan
Om alles te testen voor de echte koppeling met het polsbandbedrijf (vanaf mei 2027). Het bericht gaat door **dezelfde verwerking** als de webhook, zonder token, en is gemarkeerd als **Test**.
- **Formulier**: kies een bestaande scanner of typ een nieuw toestel-id, vul voornaam, familienaam, polsbandnummer, ploeg (kies of typ een naam om een niet-bestaande ploeg te testen), profiel en eventueel e-mail en maat in. Rechts zie je het bericht dat verstuurd wordt.
- **JSON-bestand**: sleep een .json-bestand in het vak, kies een bestand of plak het bericht — het wordt verstuurd zoals het is (handig om een echt voorbeeld van het bedrijf opnieuw af te spelen).
Klik op **Versturen**: onder de knop zie je wat er met het bericht gebeurde, en een geldige scan verschijnt meteen aan de balie die die scanner gekozen heeft, als de ploeg een reservatie heeft.

![Test-scan](scan-test.png)

## [mailtemplates | atelier.mailtemplates] E-mails
De mails die een persoon na een transactie aan de balie krijgt, naar het e-mailadres dat aan de balie ingevuld werd (zonder e-mailadres wordt niets verstuurd):
- **Uitgifte**: na elke Ophalen;
- **Inname**: na elke Terugbrengen (één mail per transactie).

Per mail stel je het **onderwerp** en de **tekst** in, en met **Versturen** zet je hem aan of uit. Klik op een veld zoals **{voornaam}** of **{stuks}** om het op de plaats van de cursor in te voegen; bij het versturen wordt het vervangen door de gegevens van de transactie. **{stuks}** = de stuks van deze transactie, **{openstaand}** = wat de persoon daarna nog in bezit heeft. Een onbekend veld kan niet opgeslagen worden.

Rechts zie je een **voorbeeld** met voorbeeldgegevens. **Stuur test naar mij** stuurt de tekst zoals hij nu staat (ook niet opgeslagen) naar je eigen e-mailadres. Opslaan en testen vragen het recht Wijzigen.

![E-mails](mails.png)

## [roles | atelier.roles] Rollen
Een rol bepaalt wat iemand in Atelier mag doen, per scherm: **Bekijken**, **Aanmaken**, **Wijzigen** en **Verwijderen**.

1. Klik op **Nieuwe rol** en geef een naam (bv. "Atelierverantwoordelijke", "Medewerker").
2. Klik bij de rol op **Rechten** en vink per scherm aan wat de rol mag.
3. Sla de rechten op.

De knop **Afboeken** op Openstaand volgt het recht Aanmaken op het scherm **Afboeken**. Wie enkel de balie doet, heeft genoeg aan de balieschermen: de festivals worden dan mee geladen.

![Rollen](roles.png)

## [users | atelier.users] Gebruikers
Iedereen met toegang tot Atelier en zijn huidige rol.

1. Kies bij een gebruiker de **rol** in de keuzelijst. De wijziging is meteen bewaard.
2. Klik op **Nieuwe gebruiker** om iemand toegang te geven. Bestaat het e-mailadres nog niet, dan wordt er een account gemaakt met de naam en het tijdelijke wachtwoord dat je invult.

![Gebruikers](users.png)
