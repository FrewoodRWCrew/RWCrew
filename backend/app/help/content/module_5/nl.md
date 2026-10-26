# Atelier

In Atelier volgt het atelierteam tijdens de festivaldagen de werkkledij op. Medewerkers van ploegen die op een plaats werken met eigen kledij (VIP, RW terras, ...) krijgen die kledij (T-shirts, hoodies, ...) bij het begin van hun shift en geven ze na de shift terug. Atelier houdt bij wat uitgegeven en teruggebracht werd, zodat alles traceerbaar blijft.

> Deze module wordt in blokken gebouwd. Nu klaar: de masterdata (artikelen en maten), de reservaties (personen en pakket per ploeg per festival), de stock (ontvangst, wassen, afboeken, telling, te bestellen), de balie (ophalen en terugbrengen) en de polsbandscans (webhook, instellingen en Test-scan). Daarna volgt het opvolgen van elk kledingstuk via RFID (TagScan).

## [overview | atelier.kpi] KPI overzicht
De startpagina van Atelier. Het blok **Balie** toont hoeveel stuks vandaag uitgegeven werden, hoeveel stuks nog niet terug zijn en hoeveel personen nog kledij in bezit hebben. Het blok **Masterdata** toont hoeveel actieve artikelen en maten er zijn en hoeveel artikelmaten uitgegeven kunnen worden. Het blok **Reservaties** toont per festival van het gekozen **seizoen** de personen en stuks per dag, het aantal ploegen met een reservatie en hoeveel daarvan nog geen pakket hebben. De kolom **Vergeten?** telt de ploegen die op een ander festival van dit seizoen een reservatie hebben, maar hier nog niets (geen personen, geen opmerking). Klik op het getal voor de namen en een link naar de reservaties van dat festival. Komt een ploeg echt niet, vul dan 0 personen in met een opmerking (bv. "komt niet"). Het blok **Stock** toont de stuks die beschikbaar zijn, te wassen zijn en uitgegeven zijn, en hoeveel maten onder hun minimumstock zitten.

![Het KPI overzicht](overview.png)

## [desk | atelier.desk] Uitgifte & inname
De balie. Kies bovenaan het **festival**, de **dag** (standaard vandaag) en de **scanner van deze balie** (wordt onthouden in deze browser).

**Polsbandscans**: scant een medewerker zijn polsband aan deze balie, dan verschijnt hij binnen enkele seconden bovenaan ("Gescand: …"). Kies dan **Ophalen** (naam, polsbandnummer, ploeg en maat staan al ingevuld) of **Terugbrengen** (zijn stuks staan meteen klaar). Met **Negeren** verdwijnt de scan. Komt er een scan binnen tijdens een transactie, dan wacht hij tot je klaar bent. Het e-mailadres is optioneel. **Elke transactie begint met de keuze tussen twee grote knoppen: Ophalen of Terugbrengen** (of toets 1 / 2). Na het boeken (of **Annuleren**) kom je terug bij die keuze voor de volgende persoon.

**Ophalen**
1. Vul **voornaam** en **familienaam** in: samen bepalen ze wie de persoon is. Is de persoon al gekend, dan worden e-mailadres, polsbandnummer en ploeg ingevuld en zie je wat hij of zij nog in bezit heeft.
2. Vul eventueel het **e-mailadres** in (optioneel; meerdere personen mogen hetzelfde adres hebben) en het **polsbandnummer** (het nummer op de polsband van dit festival; uniek binnen het festival — elk festival heeft nieuwe polsbanden). Het polsbandnummer is verplicht als dat in **Instellingen** aanstaat.
3. Kies de **ploeg** (enkel ploegen met een pakket op dit festival).
4. Per artikel van het pakket kies je de **maat** (1 stuk per artikel); tussen haakjes staat hoeveel er beschikbaar zijn. Elk artikel is **optioneel**: klik de gekozen maat nog eens om het artikel over te slaan. Heeft een artikel maar één maat in stock (bv. OneSize), dan staat die al aangeduid. Minstens één artikel is nodig; naast de knop staat wat nog ontbreekt.

Een artikel dat de persoon nog niet teruggebracht heeft, kan niet opnieuw meegegeven worden. Een oranje kader toont wat de persoon nog heeft, met de knop **Eerst terugbrengen** die meteen het terugbrengen voor die persoon opent. Alle andere artikels kan de persoon wel ophalen — ook meerdere keren per dag.
5. Klik op **Uitgeven** (of Enter).

Staan er vandaag al evenveel of meer personen van de ploeg genoteerd dan gereserveerd, dan kleurt de teller oranje — uitgeven kan nog altijd.

**Terugbrengen**
1. Zoek de persoon op naam, e-mailadres of polsbandnummer (enkel wie nog kledij heeft).
2. Alle stuks staan aangevinkt; vink af wat niet terug is (dat blijft openstaan). Is er iets afgevinkt, dan vraagt de balie eerst bevestiging met de lijst van wat bij de persoon blijft.
3. Klik op **Terugnemen**: de stuks gaan naar **Te wassen**.

**E-mail**: heeft de persoon een e-mailadres, dan krijgt hij of zij na elke Ophalen een mail **Uitgifte** en na elke Terugbrengen één mail **Inname** (ook als de stuks van verschillende uitgiftes komen). De teksten stel je in op **Instellingen > E-mails**.

Met het recht Wijzigen kan je een uitgifte waarvan nog niets terug is **annuleren** (de stuks gaan terug naar beschikbaar).

![De balie: Ophalen of Terugbrengen](desk.png)

## [open | atelier.open] Openstaand
Alle kledij die opgehaald werd maar nog niet terug is, **gegroepeerd per ploeg en dan per persoon** (met polsbandnummer en e-mailadres — klik om te mailen), met daaronder elk stuk: dag, artikel, maat en wanneer het opgehaald werd. Kies bovenaan het festival en eventueel de dag. Boven elke kolom staat een **filterveld**: typ er een deel van een naam, ploeg, artikel, … in om de lijst te verkleinen; de totalen volgen de filter. Komt iets nooit terug, boek het dan af via **Stock > Afboeken** (reden "Niet teruggebracht").

![Openstaand](open.png)

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
Per artikel en maat hoeveel stuks **beschikbaar** zijn, **te wassen** zijn (teruggebracht na een shift) en **uitgegeven** zijn, met het totaal en de minimumstock. Een maat onder de minimumstock kleurt oranje; boven elke Atelier-pagina staat dan ook een oranje melding. Met **Enkel onder minimumstock** zie je alleen die maten.

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


## [dataupload | atelier.dataupload] Data Upload/Download
Per tabel een tegel om een **sjabloon** te downloaden, een ingevuld bestand te **uploaden** en de huidige gegevens te **exporteren**.

- **Maten** en **Artikelen**: een rij wordt gezocht op **id** (de eerste kolom van de export) en anders op naam + pasvorm (maten) of code (artikelen); een gevonden record wordt gewijzigd, anders komt er een nieuw bij. Zo kan je ook een export van een andere omgeving (bv. localhost naar test) opladen.
- **Artikelmaten** (artikelcode + maat + pasvorm), **Reservaties** (seizoen + festival + ploeg) en **Pakketlijnen** (seizoen + festival + ploeg + artikelcode): een bestaande combinatie wordt bijgewerkt, een nieuwe toegevoegd.
- Pasvorm mag als women/men/unisex of Dames/Heren/Unisex.

Na het uploaden zie je per rij of ze aangemaakt, bijgewerkt, ongewijzigd of fout is, met de reden.

![Data Upload/Download](data-upload.png)

## [settings | atelier.settings] Instellingen
- **Polsband verplicht bij Ophalen**: staat dit aan, dan kan aan de balie niets opgehaald worden zonder polsbandnummer (gescand of getypt). Elk festival heeft nieuwe polsbanden: een nummer is uniek binnen één festival.
- **Webhook**: het adres waarop het polsbandbedrijf zijn scans stuurt, en of de token op deze server ingesteld is. Zonder token wordt elk bericht geweigerd (Test-scan werkt wel).
- **Scanners**: elke scanner van het polsbandbedrijf verschijnt automatisch bij zijn eerste bericht. Geef hem een naam (bv. "Balie 1"); aan de balie kies je bovenaan welke scanner bij die balie staat.
- **Ontvangen berichten**: elk bericht dat binnenkwam — ook geweigerde (verkeerde token, geen leesbare JSON) en berichten die niet voor de balie zijn — met status, scanner, persoon, polsband en ploeg. Met het oog-icoon zie je het bericht zoals het binnenkwam. "geen ploeg met deze naam" betekent dat de ploegnaam niet overeenkomt met een ploeg uit MasterData; de balie kiest dan zelf de ploeg.

![Instellingen](settings.png)

## [scantest | atelier.scantest] Test-scan
Om alles te testen voor de echte koppeling met het polsbandbedrijf (vanaf mei 2027). Het bericht gaat door **dezelfde verwerking** als de webhook, zonder token, en is gemarkeerd als **Test**.
- **Formulier**: kies een bestaande scanner of typ een nieuw toestel-id, vul voornaam, familienaam, polsbandnummer, ploeg (kies of typ een naam om een niet-bestaande ploeg te testen), profiel en eventueel e-mail en maat in. Rechts zie je het bericht dat verstuurd wordt.
- **JSON-bestand**: sleep een .json-bestand in het vak, kies een bestand of plak het bericht — het wordt verstuurd zoals het is (handig om een echt voorbeeld van het bedrijf opnieuw af te spelen).
Klik op **Versturen**: onder de knop zie je wat er met het bericht gebeurde, en een geldige scan verschijnt meteen aan de balie die die scanner gekozen heeft.

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

![Rollen](roles.png)

## [users | atelier.users] Gebruikers
Iedereen met toegang tot Atelier en zijn huidige rol.

1. Kies bij een gebruiker de **rol** in de keuzelijst. De wijziging is meteen bewaard.
2. Klik op **Nieuwe gebruiker** om iemand toegang te geven. Bestaat het e-mailadres nog niet, dan wordt er een account gemaakt met de naam en het tijdelijke wachtwoord dat je invult.

![Gebruikers](users.png)
