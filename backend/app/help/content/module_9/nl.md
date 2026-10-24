# MasterData

MasterData bevat de basisgegevens die alle andere modules gebruiken: de jaartallen, festivals, ploegen en hun verantwoordelijken, en de producten met hun type, magazijn, categorie en limiet.

## [start] Zo werkt MasterData
De andere modules lezen deze gegevens, ze bewaren ze niet zelf:

- **Jaartallen** en **Festivals**: het seizoen waarin Altsien Select, KarTracker en StockMaster werken.
- **Ploegen**: de verenigingen, met hun locatie, leverwijze, taken en Altsien Kernleden. Welke ploegen een Kernlid ziet in Altsien Select, beslis je hier.
- **Producten**: alles wat in het magazijn ligt en in de karren gaat. Hun eigenschappen bepalen hoe StockMaster ermee omgaat (blokkeren, limiet, minimum voorraad, ...).
- De kleine lijsten (Type, Magazijnen, Categorieën, Limieten, Teamlocatie, Leveringsmethode, Teamtaken) zijn de keuzes in de formulieren van Producten en Ploegen.

> Op elk scherm opent **Help bij dit scherm** rechtsboven het stuk van deze handleiding over dat scherm. De volledige handleiding vind je onderaan het menu links.

## [overview] Masterdata Overzicht
Het startscherm van MasterData: de producten in één oogopslag.

- **Tegels** bovenaan: het aantal producten en jaartallen, en hoeveel producten geblokkeerd, consumeerbaar of logistiek zijn, en hoeveel er een onvolledige classificatie hebben (geen type, magazijn of categorie).
- **Producten per type**, **per categorie** en **per magazijn**.

![Het Masterdata Overzicht](overview.png)

## [season | masterdata.season] Jaartallen
De jaartallen (seizoenen) waarin de app werkt.

1. Klik op **Nieuw jaartal** en geef de naam, bv. "2027".
2. Zet **Periode Open** aan zolang de Altsien Kernleden hun keuzes voor dat jaartal nog mogen wijzigen. Zet het uit om de keuzes te bevriezen.

![Jaartallen](season.png)

> In StockMaster boek je in een afgesloten jaartal enkel nog met een uitdrukkelijk recht.

## [festival | masterdata.festival] Festivals
De festivals per jaartal, met hun start- en einddatum.

1. Klik op **Nieuw festival**: naam, startdatum, einddatum en jaartal.
2. Zet een festival dat niet doorgaat op niet **Actief**: in de Ploeg Wizard kan het dan niet meer gekozen worden.

![Festivals](festival.png)

## [teams | masterdata.teams] Ploegen
De verenigingen die met een kar werken: naam, locatie, leverwijze, beschrijving en of ze actief zijn.

1. Klik op **Nieuw team** en vul minstens de naam in.
2. Kies de **Taken** van de ploeg en de **Kernleden**: de Altsien Kernleden die deze ploeg in Altsien Select zien en invullen.
3. Kies bij **Levertoeren** de speciale levertoeren (KarTracker > Speciale levertoeren, bijvoorbeeld de wastoer of ijsblokken) die regelmatig bij de ploeg langsgaan.
4. Een ploeg die niet meer meedoet, zet je op niet **Actief**.

![Ploegen](teams.png)

> Enkel gebruikers die als Altsien Kernlid aangeduid zijn, verschijnen in de lijst Kernleden.

## [team-responsibles | masterdata.team-responsibles] Ploegverantwoordelijken
De verantwoordelijken per ploeg en per jaartal, met hun e-mail, telefoonnummer en opmerkingen. Zij hoeven geen RWCrew-gebruiker te zijn.

1. Kies eventueel een ploeg en een jaartal om de lijst te beperken.
2. Klik op **Nieuwe ploegverantwoordelijke**: ploeg, jaartal, naam, e-mail en telefoonnummer zijn verplicht.

![Ploegverantwoordelijken](team-responsibles.png)

> Dit is dezelfde lijst als stap 3 van de Ploeg Wizard in Altsien Select: wat de Kernleden daar ingeven, zie je hier, en omgekeerd.

## [team-location | masterdata.team-location] Teamlocatie
De locaties die je bij een ploeg kan kiezen. Klik op **Nieuwe teamlocatie** om er een toe te voegen, of op **Wijzigen** om een naam aan te passen.

![Teamlocatie](team-location.png)

## [delivery-method | masterdata.delivery-method] Leveringsmethode
De leverwijzes die je bij een ploeg kan kiezen. Klik op **Nieuwe leveringsmethode** om er een toe te voegen.

![Leveringsmethode](delivery-method.png)

## [team-tasks | masterdata.team-tasks] Teamtaken
De taken die een ploeg kan hebben. Klik op **Nieuwe teamtaak** om er een toe te voegen; bij de ploeg vink je aan welke taken ze heeft.

![Teamtaken](team-tasks.png)

## [products | masterdata.products] Producten
Alle producten met hun foto, type, magazijn, categorie en eigenschappen.

1. Klik op **Nieuw product**. Naam, type, magazijn, categorie en limiet zijn verplicht. Vul ook de **Magazijn locatie** in: daar ligt de vrije voorraad in StockMaster.
2. Voeg eventueel een **Foto** toe: die zie je in StockMaster en Altsien Select.
3. Kies de eigenschappen:
   - **Consumeerbaar**: een verbruiksgoed. Enkel daarvoor telt de **minimum voorraad** (oranje balk in StockMaster).
   - **Blokkeer**: kan niet meer ingeboekt of geleverd worden.
   - **Is logistiek product**: krijgt bij Kar laden altijd wat gevraagd is.
   - **Tag Managed (RFID)**: het product draagt een RFID-tag (TagScan).
   - **StockMaster: na 'Kar terug'**: komt het terug in de kar of naar de vrije voorraad?
4. Kies de **Limiet** (Ongelimiteerd, Automatisch, Percentage, Toegewezen aantal) en, bij Percentage, de **Limietwaarde**. Met **Maximum initiële stock** begrens je wat een kar krijgt zolang ze in KarTracker niet geleverd is. Samen bepalen ze wat StockMaster bij Kar laden mag leveren.
5. **Kostprijs (€)** is optioneel.

![Producten](products.png)

> Een product met voorraad of boekingen in StockMaster kan je niet verwijderen: blokkeer het in de plaats.

## [product-types | masterdata.product-types] Type
De producttypes, een keuze op het productformulier. Klik op **Nieuw type** om er een toe te voegen.

![Type](product-types.png)

## [warehouses | masterdata.warehouses] Magazijnen
De magazijnen waar producten liggen. Klik op **Nieuw magazijn** om er een toe te voegen.

![Magazijnen](warehouses.png)

## [product-categories | masterdata.product-categories] Categorieën
De productcategorieën, om producten te groeperen en te filteren. Klik op **Nieuwe categorie** om er een toe te voegen.

![Categorieën](product-categories.png)

## [product-limits | masterdata.product-limits] Limieten
De limieten die je bij een product kiest. StockMaster herkent ze aan hun **naam**: Ongelimiteerd, Automatisch, Percentage en Toegewezen aantal.

![Limieten](product-limits.png)

> Hernoem deze limieten niet: StockMaster kent ze bij naam, en een andere naam telt niet meer mee in de berekening van Kar laden.

## [data-upload | masterdata.dataupload] Data Upload/Download
Alle tabellen van MasterData in bulk importeren en exporteren met Excel, één tegel per tabel.

1. Klik op een tegel, bv. **Producten**.
2. **Sjabloon downloaden** geeft een leeg Excel-bestand met de juiste kolommen.
3. Vul het in, kies het bij **Excel-bestand** en klik op **Uploaden**. Het resultaat toont per rij: **Aangemaakt**, **Bijgewerkt**, **Al aanwezig** of **Fout** (met de reden).
4. Met de knop onderaan exporteer je de volledige lijst.

![Data Upload/Download](data-upload.png)

- **Wijzigen in bulk**: exporteer de lijst, pas ze aan en upload ze opnieuw. Een rij met een **id** (de eerste kolom van de export) wijzigt dat record; een rij zonder id maakt een nieuw aan. Kolommen die niet in je bestand staan, blijven ongewijzigd.
- Lijsten (type, magazijn, ploeg, ...) geef je bij **naam**, hoofdletters maken niet uit.
- Ja/nee-kolommen aanvaarden ja/nee, yes/no, true/false en 1/0.
- **Taken per ploeg**, **Kernleden per ploeg** en **Festivals per ploeg** voegen enkel koppelingen toe: een koppeling die al bestaat, krijgt "Al aanwezig". Kernleden geef je met het e-mailadres van hun account. Verwijderen doe je op het scherm zelf.

> Uploaden kan enkel met het recht **Aanmaken** op dit scherm; sjablonen en exports downloaden kan met **Bekijken**.

## [roles | masterdata.roles] Rollen
Een rol bepaalt wat iemand in MasterData mag doen, per scherm: **Bekijken**, **Aanmaken**, **Wijzigen** en **Verwijderen**.

1. Klik op **Nieuwe rol** en geef een naam (bv. "Magazijn", "Beheerder").
2. Klik bij de rol op **Rechten** en vink per scherm aan wat de rol mag.
3. Sla de rechten op.

![Rollen](roles.png)

## [users | masterdata.users] Gebruikers
Iedereen met toegang tot MasterData en zijn huidige rol.

1. Kies bij een gebruiker de **rol** in de keuzelijst. De wijziging is meteen bewaard.
2. Klik op **Nieuwe gebruiker** om iemand toegang te geven. Bestaat het e-mailadres nog niet, dan wordt er een account gemaakt met de naam en het tijdelijke wachtwoord dat je invult.

![Gebruikers](users.png)
