# Altsien Select

In Altsien Select maken de Altsien Kernleden per ploeg en per jaartal de keuzes waarop de organisatie haar instructies bouwt: op welke festivals de ploeg staat, waar er geleverd wordt, wie de verantwoordelijken zijn, welke producten elke kar meekrijgt en welke speciale aanvragen er zijn.

## [start] Zo werkt Altsien Select
1. De beheerder van MasterData koppelt jou als **Altsien Kernlid** aan je ploeg(en). Enkel die ploegen zie je hier.
2. In de **Ploeg Wizard** doorloop je per ploeg de stappen en rond je elke stap af.
3. De **Ploegfiche** toont alle keuzes van een ploeg op één scherm, ook als PDF.
4. De organisatie volgt de speciale aanvragen op in **Opvolging aanvragen** en geeft er een antwoord op.

### Het jaartal
Bovenaan kies je het **jaartal**. Zolang de periode van dat jaartal open staat (MasterData > Jaartallen), kan je je keuzes wijzigen. Daarna is alles enkel nog te bekijken, tenzij je rol het uitdrukkelijk toelaat.

### Waar je keuzes terechtkomen
Altsien Select bewaart zelf enkel de voortgang en de speciale aanvragen. De rest komt meteen in de andere modules: de festivals en ploegverantwoordelijken in **MasterData**, de afleverlocaties in KarTracker (**Plan a kar**) en de producten in de **Benodigdheden** van StockMaster.

> Op elk scherm opent **Help bij dit scherm** rechtsboven het stuk van deze handleiding over dat scherm. De volledige handleiding vind je onderaan het menu links.

## [overview] KPI overzicht
Hoe ver staan de ploegen met hun Ploeg Wizard in het gekozen jaartal?

- **Tegels** bovenaan: het aantal ploegen, hoeveel hun wizard afrondden, hoeveel er nog bezig zijn en hoeveel speciale aanvragen nog open staan.
- **Voortgang per stap**: hoeveel ploegen elke stap al afrondden.
- **Speciale aanvragen per status**.

![Het KPI overzicht](overview.png)

## [wizard | altsienselect.wizard] Ploeg Wizard
De lijst van jouw ploegen met hun voortgang ("3/6 stappen") en hun open aanvragen. Klik op **Starten** of **Verder** om de wizard van een ploeg te openen.

![De Ploeg Wizard](wizard.png)

In de wizard zie je de stappen bovenaan. Vul een stap in en klik op **Stap afronden & verder**. Een afgeronde stap toont wanneer en door wie hij afgerond werd; met **Heropenen** pas je hem opnieuw aan. Met **Vorige** en **Volgende** blader je zonder af te ronden.

### 1. Festivals
Vink de festivals van het jaartal aan waarop de ploeg actief is. Een festival weghalen, wist ook zijn afleverlocatie.

### 2. Afleverlocaties
Kies per gekozen festival de **afleverlocatie** waar de goederen geleverd worden. Dit komt terecht in KarTracker (Plan a kar).

### 3. Ploegverantwoordelijken
Geef minstens één verantwoordelijke op met naam, e-mail en telefoonnummer (**Verantwoordelijke toevoegen**). Deze personen hoeven geen RWCrew-gebruiker te zijn.

### 4. Producten
Kies een **kar** van de ploeg en stel haar lijst samen: welke producten en hoeveel. Dit is dezelfde lijst waarmee StockMaster de kar laadt (Benodigdheden). Per kar kan je de lijst van vorig jaar overnemen.

### 5. Speciale aanvragen
Heeft de ploeg iets speciaals nodig? Klik op **Aanvraag toevoegen** en beschrijf het zo duidelijk mogelijk. De organisatie zet er een status op en kan antwoorden; dat antwoord zie je bij de aanvraag. Geen aanvragen? Rond de stap gewoon af.

### 6. Walkie-talkies
Deze stap volgt later.

> Bij de stappen Afleverlocaties, Ploegverantwoordelijken en Speciale aanvragen staat bovenaan **Overnemen van vorig jaartal**: klik op **Tonen**, vink de lijnen van vorig jaar aan die je wil overnemen en klik op **Geselecteerde overnemen**. Er wordt nooit iets gewist, en de stap wordt niet automatisch afgerond.

## [ploegfiche | altsienselect.ploegfiche] Ploegfiche
Alle keuzes van één ploeg op één scherm: ploeginfo (locatie, leveringswijze, kernleden), de voortgang van de wizard, de karren, festivals en afleverlocaties, ploegverantwoordelijken, producten per kar en speciale aanvragen.

1. Kies het jaartal en de ploeg.
2. Klik op **PDF** om de ploegfiche af te drukken.
3. Iets aanpassen? **Wijzigen in de wizard** opent de wizard van die ploeg.

![De Ploegfiche](ploegfiche.png)

## [requests | altsienselect.requests] Opvolging aanvragen
Alle speciale aanvragen van de ploegen in het gekozen jaartal, voor de organisatie.

1. Filter eventueel op **status**.
2. Klik bij een aanvraag op **Opvolgen**, kies de status en schrijf een **Antwoord organisatie**.
3. Klik op **Opslaan**. De ploeg ziet het antwoord in haar wizard en op de ploegfiche.

![Opvolging aanvragen](requests.png)

## [statuses | altsienselect.statuses] Statussen aanvragen
De statussen die een speciale aanvraag kan hebben, met een kleur en of ze **open** of **gesloten** zijn.

1. Klik op **Nieuwe status**, geef een naam, een kleur en of ze open of gesloten is.
2. Bepaal de **volgorde**: de status met de laagste volgorde is de beginstatus van elke nieuwe aanvraag.

![Statussen aanvragen](statuses.png)

## [roles | altsienselect.roles] Rollen
Een rol bepaalt wat iemand in Altsien Select mag doen, per scherm: **Bekijken**, **Aanmaken**, **Wijzigen** en **Verwijderen**.

1. Klik op **Nieuwe rol** en geef een naam (bv. "Kernlid", "Organisatie").
2. Klik bij de rol op **Rechten** en vink per scherm aan wat de rol mag.
3. Sla de rechten op.

Wat de rechten betekenen:
- **Ploeg Wizard**: Bekijken om de wizard te openen, Wijzigen om keuzes te maken.
- **All teams (organisation)** is geen scherm maar een schakelaar: Bekijken toont **alle** ploegen in plaats van enkel de eigen ploegen; Wijzigen laat toe om nog te wijzigen nadat de periode van het jaartal gesloten werd.
- **Opvolging aanvragen** en **Statussen aanvragen**: voor de organisatie.

![Rollen](roles.png)

## [users | altsienselect.users] Gebruikers
Iedereen met toegang tot Altsien Select en zijn huidige rol.

1. Kies bij een gebruiker de **rol** in de keuzelijst. De wijziging is meteen bewaard.
2. Klik op **Nieuwe gebruiker** om iemand toegang te geven. Bestaat het e-mailadres nog niet, dan wordt er een account gemaakt met de naam en het tijdelijke wachtwoord dat je invult.

![Gebruikers](users.png)

> Welke ploegen een Kernlid ziet, kies je niet hier maar in MasterData > Ploegen (Kernleden), of in bulk via MasterData > Data Upload/Download.
