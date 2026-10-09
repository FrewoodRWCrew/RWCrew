# StockMaster

StockMaster houdt de voorraad van het magazijn bij: wat er **vrij** op zijn vaste locatie ligt en wat er **in de karren** zit zolang die in het magazijn staan. Elke actie in het magazijn (goederen komen binnen, een kar wordt geladen, vertrekt of komt terug) is één boeking op jouw naam.

## [start] Zo werkt StockMaster
StockMaster volgt het verloop in het magazijn. Het menu **Akties** staat in die volgorde: Inboeken, Kar laden, Uitboeken, Kar vertrekt, Kar terug, Kar uitladen en Telling.

### Vrije voorraad en karvoorraad
- **Vrije voorraad**: ligt op de vaste locatie van het product (magazijn + locatie uit MasterData).
- **In karren**: geladen in een kar die in het magazijn staat. Eén product kan tegelijk vrij liggen en in meerdere karren zitten.
- **Totaal** = vrij + in karren. Een kar die **onderweg** is telt niet meer mee: zijn inhoud werd uitgeboekt bij "Kar vertrekt".

### Het seizoen
Bovenaan de meeste schermen kies je het **seizoen**. Benodigdheden, Te bestellen, de KPI en de karren volgen die keuze. In een afgesloten seizoen kan je niet meer boeken, tenzij je rol dat uitdrukkelijk toelaat.

### Niets gaat verloren
- Elke boeking wordt bewaard op **jouw naam**, met datum en uur.
- Een boeking wordt nooit gewist. Een fout herstel je met **Ongedaan maken**: er komt een tegenboeking bij en alles gaat terug naar waar het vandaan kwam.
- De voorraad kan nooit negatief worden: je kan niet meer uit een plaats halen dan er ligt.

### Onder minimum
Verbruiksgoederen met een minimum stock die eronder zakken, geven een **oranje balk** bovenaan elk StockMaster scherm. Klik op **Bekijken** om enkel die producten te zien.

> Op elk scherm opent de knop **Help bij dit scherm** rechtsboven het stuk van deze handleiding dat over dat scherm gaat. De volledige handleiding vind je onderaan het menu links.

## [booking] Boeken in 4 stappen
Alle akties (Inboeken, Kar laden, Uitboeken, ...) werken met dezelfde **boekingslijst**: een mandje waar je één of meer producten in legt en dat je in één keer bevestigt.

1. Kies indien nodig eerst de **kar** (typ een paar cijfers van het karnummer).
2. Typ een paar letters van een **product**. Je ziet meteen de locatie en hoeveel er vrij ligt.
3. Vul het **aantal** in en druk **Enter**: de lijn staat in de lijst en je kan het volgende product zoeken.
4. Controleer de kolom **Voor → na** en klik op **Bevestigen**.

> Je kan alles met het toetsenbord: product typen, Enter, aantal typen, Enter. **Ctrl+Enter** bevestigt de boeking.

Na het bevestigen verschijnt onderaan een melding met **Ongedaan maken**, voor als je je vergist hebt. Waar een document bij hoort (bv. de Vertrekbon) kan je het meteen afdrukken.

## [kpi | stockmaster.kpi] KPI
Het startscherm van StockMaster: de voorraad en de karren in één oogopslag, voor het gekozen seizoen.

- **Tegels** bovenaan: totale voorraad, vrije voorraad, in karren, karren in het magazijn of onderweg, karren die volledig geladen zijn, producten onder minimum en lijnen die nog besteld moeten worden. Klik op een tegel om het scherm erachter te openen.
- **Boekingen per maand**, per actie (ongedaan gemaakte boekingen tellen niet mee).
- **Verbruik per ploeg**: wat niet terugkwam met de karren.
- **Meest verbruikte producten**: niet teruggekomen + uitgeboekt.

![Het KPI scherm](kpi.png)

## [stock | stockmaster.stock] Voorraadoverzicht
Per product zie je hoeveel er **vrij** ligt, hoeveel **in karren** zit en het **totaal**, met de locatie en het magazijn.

1. Zoek op productnaam of locatie, of filter op magazijn en categorie.
2. Zet **Alleen onder minimum** aan om enkel de verbruiksgoederen te zien die onder hun minimum zitten.
3. Klik op een lijn om de verdeling **per kar** te zien.
4. Gebruik de knoppen op de lijn om meteen **Inboeken**, **Uitboeken** of **Laden in kar...** te openen, met het product al ingevuld.

![Het voorraadoverzicht](stock.png)

> Een oranje label **Onder minimum** betekent dat er (vrij + in karren) minder ligt dan de minimum stock uit MasterData.

## [kars | stockmaster.kars] Karren
Elke kar als een kaart: het karnummer, de ploeg, of hij **in het magazijn** of **onderweg** is en hoe ver hij geladen is tegenover zijn benodigdheden ("18 / 20"). Groen is volledig geladen, oranje is nog niet volledig.

1. Typ een karnummer en druk **Enter** om de kar meteen te openen, of filter op ploeg en op in het magazijn/onderweg.
2. Klik op een kaart voor de **detailpagina** van de kar.
3. Op de detailpagina zie je per product wat **nodig** is, wat **in de kar** zit, wat **ontbreekt** en wat er **vrij beschikbaar** is.
4. Met de knoppen **Laden**, **Uitladen**, **Vertrekt**, **Terug** en **Tellen** open je de actie voor deze kar. **Laadlijst** drukt de lijst af om de kar te laden, gesorteerd op locatie.

![Het overzicht van de karren](kars.png)

> Een kar die onderweg is, kan je niet laden, uitladen of tellen. Boek eerst **Kar terug**.

## [book-in | stockmaster.stock] 1. Inboeken
Goederen komen binnen (levering, aankoop) en gaan naar de **vrije voorraad** op hun vaste locatie.

1. Leg de producten met hun aantal in de boekingslijst (zie "Boeken in 4 stappen").
2. Vul de **leveringsbon of het bestelnummer** in als referentie.
3. Klik op **Bevestigen: inboeken**.

![Inboeken](book-in.png)

> Geblokkeerde producten kunnen niet ingeboekt worden. Komt een volledige bestelling binnen, start dan vanuit **Te bestellen**: de aantallen staan dan al klaar.

## [kar-load | stockmaster.kars] 2. Kar laden
Vul een kar vanuit de vrije voorraad (of vanuit een andere kar).

1. Kies de kar.
2. Wat de kar volgens zijn **benodigdheden** nog mist, staat al in de lijst. Klik op **Vul aan met wat ontbreekt** als je de lijst opnieuw wil laten vullen.
3. Pas de aantallen aan als je minder of meer laadt, of voeg andere producten toe.
4. Kies bij **Van** of het uit de vrije voorraad of uit een andere kar komt.
5. Klik op **Bevestigen: kar laden**.

![Kar laden](kar-load.png)

> Staat er "vrij 3 van 5 nodig" in het oranje, dan ligt er niet genoeg vrije voorraad. Kijk bij **Te bestellen** wat er nog moet komen.

## [book-out | stockmaster.stock] 3. Uitboeken
Verbruikte, kapotte of verloren goederen gaan uit de voorraad: uit de vrije voorraad of uit een kar die in het magazijn staat.

1. Kies bij **Van** de vrije voorraad of een kar.
2. Leg de producten met hun aantal in de boekingslijst.
3. Kies een **reden** (verplicht), bv. verbruikt, kapot of verloren.
4. Klik op **Bevestigen: uitboeken**.

![Uitboeken](book-out.png)

## [kar-dispatch | stockmaster.kars] 4. Kar vertrekt
De kar verlaat het magazijn naar de ploeg en het festival. De **volledige inhoud** gaat mee en wordt uit de voorraad geboekt.

1. Kies de kar. Je ziet wat er met de kar vertrekt.
2. Controleer de **ploeg** en het **festival** (ingevuld vanuit KarTracker).
3. Klik op **Bevestigen: kar vertrekt**.
4. Druk de **Vertrekbon** af en laat hem tekenen door het magazijn en de ploeg.

![Kar vertrekt](kar-dispatch.png)

> Mist de kar nog iets van zijn benodigdheden, dan krijg je een waarschuwing. Je kan toch laten vertrekken.

## [kar-return | stockmaster.kars] 5. Kar terug
De kar is terug van het festival. Wat vertrok, staat al ingevuld: je past enkel aan wat anders is.

1. Kies de kar. De lijst toont per product wat **vertrokken** is en wat **terug** is.
2. Verlaag het aantal bij de producten die niet (volledig) terugkwamen. Je ziet meteen "2 niet terug → verbruikt".
3. Kies per lijn of het **terug in de kar** gaat of naar de **vrije voorraad** (standaard volgens de instelling van het product).
4. Klik op **Bevestigen: kar terug**.

![Kar terug](kar-return.png)

> Wat niet terugkomt, telt als **verbruik van de ploeg**. Je ziet het op de KPI bij "Verbruik per ploeg".

## [kar-unload | stockmaster.kars] 6. Kar uitladen
Haal goederen uit een kar in het magazijn terug naar de vrije voorraad, bijvoorbeeld na het seizoen.

1. Kies de kar.
2. Leg de producten die eruit gaan in de lijst, of klik op **Alles uitladen**.
3. Klik op **Bevestigen: kar uitladen**.

![Kar uitladen](kar-unload.png)

## [count | stockmaster.count] 7. Telling
Tel de voorraad op een plaats en boek enkel de verschillen.

1. Kies **Vrije voorraad** (een magazijn, eventueel van locatie ... tot locatie ...) of **Een kar**.
2. Klik op **Lijst laden**. De lijst staat klaar met wat er **verwacht** wordt.
3. Druk eventueel het **Telblad** af om op papier te tellen.
4. Vul bij **Geteld** enkel in wat anders is. Iets gevonden dat niet op de lijst staat? Zoek het om het toe te voegen.
5. Controleer de reden (standaard "Telverschil") en klik op **Verschillen boeken**.

![De telling](count.png)

## [requirements | stockmaster.requirements] Benodigdheden
Wat elke ploeg per seizoen nodig heeft, **per kar**. Dit vult "Kar laden" aan, toont hoe ver een kar geladen is en bepaalt wat er besteld moet worden.

1. Kies het seizoen en de ploeg.
2. Klik op een kar van de ploeg.
3. Voeg producten toe met hun aantal en eventueel een opmerking, of pas bestaande lijnen aan.
4. Klik op **Opslaan**.

![Benodigdheden per kar](requirements.png)

> Bij **Kopieer van vorig seizoen** zie je de lijnen van vorig seizoen. Vink aan wat je wil overnemen en klik op **Kopiëren**. Vergeet daarna niet op te slaan.

## [order-needs | stockmaster.orderneeds] Te bestellen
De benodigdheden van alle karren van het seizoen tegenover wat er in voorraad is (vrij + in karren). **Te bestellen** = nodig min in voorraad.

1. Kies het seizoen en filter eventueel op magazijn en categorie.
2. Laat **Alleen wat besteld moet worden** aan om enkel de tekorten te zien.
3. Druk de **Bestellijst** af of **exporteer** naar CSV voor de leverancier.
4. Komt de bestelling binnen? Vink de lijnen aan en klik op **Inboeken**: de aantallen staan al klaar, je corrigeert enkel wat anders geleverd is.

![Te bestellen](order-needs.png)

## [bookings | stockmaster.bookings] Boekingen
Alle boekingen, de nieuwste eerst, met wie ze deed en wanneer.

1. Filter op datum, actie, product, kar of gebruiker.
2. Klik op een boeking voor alle lijnen: van waar, naar waar, hoeveel en de locatie op dat moment.
3. Druk de **Bon** af (bij Kar vertrekt is dat de Vertrekbon).
4. Een fout? Klik op **Ongedaan maken** en geef eventueel een opmerking. De oorspronkelijke boeking blijft zichtbaar als "Ongedaan gemaakt".

![De boekingen](bookings.png)

> Ongedaan maken gaat niet als de goederen intussen al verder geboekt zijn (bv. de kar is al vertrokken). Maak dan eerst die latere boeking ongedaan.

## [reasons | stockmaster.reasons] Redenen
De redenen die je kiest bij het uitboeken of bij een telling, zoals "Verbruikt", "Kapot" of "Telverschil".

1. Klik op **Nieuwe reden**, geef een naam en kies voor welke boeking ze geldt (of alle boekingen).
2. Bepaal de **volgorde** in de keuzelijst.
3. Zet een reden die je niet meer gebruikt op **Inactief**. Verwijderen kan enkel als ze nog nooit gebruikt werd.

![De redenen](reasons.png)

## [roles | stockmaster.roles] Rollen
Een rol bepaalt wat iemand in StockMaster mag doen, per scherm: **Bekijken**, **Aanmaken**, **Wijzigen** en **Verwijderen**.

1. Klik op **Nieuwe rol** en geef een naam (bv. "Magazijnier", "Ploeg").
2. Klik bij de rol op **Rechten** en vink per scherm aan wat de rol mag.
3. Sla de rechten op.

Wat de rechten betekenen:
- **Voorraad**, Aanmaken: Inboeken en Uitboeken.
- **Karren**, Aanmaken: Kar laden, uitladen, vertrekt en terug.
- **Telling**, Aanmaken: een telling boeken.
- **Boekingen**, Verwijderen: een boeking ongedaan maken.
- **Boeken in een afgesloten seizoen** is geen scherm maar een schakelaar: Wijzigen laat toe om nog te boeken nadat het seizoen afgesloten werd.

![De rollen](roles.png)

## [users | stockmaster.users] Gebruikers
Iedereen met toegang tot StockMaster en zijn huidige rol.

1. Kies bij een gebruiker de **rol** in de keuzelijst. De wijziging is meteen bewaard.
2. Klik op **Nieuwe gebruiker** om iemand toegang te geven. Bestaat het e-mailadres nog niet, dan wordt er een account gemaakt met de naam en het tijdelijke wachtwoord dat je invult.

![De gebruikers](users.png)

> Zonder rol ziet iemand in StockMaster niets, ook al heeft hij toegang tot de module.
