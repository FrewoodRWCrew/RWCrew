# KarTracker

KarTracker beheert het wagenpark van de organisatie: elke kar met zijn ploeg en status, de plaatsen waar karren geleverd worden en per festival waar elke kar naartoe moet. Elke verplaatsing van een kar wordt geregistreerd, op de pc of met de gsm, en is te zien op de kaart.

## [start] Zo werkt KarTracker
KarTracker volgt het leven van een kar in een seizoen:

1. **Stamgegevens**: de statussen, zones, distributiepunten, afleverlocaties en de karren zelf (met hun ploeg) staan in de groep **Masterdata**. Per festival leg je de **leverdatum** en **ophaaldatum** vast.
2. **Plannen**: met **Plan a kar** kies je per ploeg de afleverlocatie voor elk festival van het jaartal.
3. **Afdrukken**: op **Kar Planning** druk je per kar een **karblad** af dat met de kar meegaat: waar en wanneer hij geleverd en opgehaald wordt, met een QR-code van het karnummer.
4. **Volgen**: elke verplaatsing (nieuwe status + GPS-locatie) registreer je met **Manuele kar beweging**, of met **KarScan** op de gsm door de QR-code op het karblad te scannen.
5. **Bekijken**: **Kar Map** toont alle karren, afleverlocaties en distributiepunten op de kaart, eventueel met het grondplan van het terrein.

### Het jaartal
Het **jaartal** kies je bovenaan in de kopbalk. De KPI, Kar Planning, Plan a kar en Leverdata volgen die keuze. In de kopbalk staan enkel de jaartallen die nog open zijn.

> Op elk scherm opent **Help bij dit scherm** rechtsboven het stuk van deze handleiding over dat scherm. De volledige handleiding vind je onderaan het menu links, bij **Help**.

## [overview] KPI Overzicht
Het startscherm van KarTracker: het wagenpark, de recente bewegingen en de voortgang van Plan a kar voor het gekozen jaartal.

- **Tegels** bovenaan: totaal aantal karren, karren met en zonder ploeg, bewegingen van de laatste 7 dagen en hoeveel afleverlocaties al gepland zijn.
- **Karren per status** en **Karren per ploeg**.
- **Bewegingen per dag**, de laatste 14 dagen.
- **Plan a kar per festival**: hoeveel van de actieve ploegen al een afleverlocatie hebben.

![Het KPI Overzicht](overview.png)

> Zie je bij Plan a kar "kies een jaartal", kies dan eerst een jaartal bovenaan in de kopbalk.

## [movement | kartracker.actions] Manuele kar beweging
Registreer elke verplaatsing van een kar: welke kar, zijn nieuwe status en waar hij nu staat.

1. Kies de **kar** in de lijst, of klik op **Scan QR** en richt de camera op de QR-code rechtsboven op het karblad.
2. Kies de nieuwe **status**.
3. Klik op **Gebruik mijn locatie** om de GPS-locatie van je toestel te nemen, of klik op de kaart om de plaats te kiezen of aan te passen. Zet eventueel de laag **Grondplan** aan om het terrein te zien.
4. Klik op **Beweging opslaan**. De kar krijgt zijn nieuwe status en locatie.

![Manuele kar beweging](movement.png)

Onderaan staan de **geregistreerde bewegingen**. Een foute beweging kan je **verwijderen**: de huidige status en locatie van de kar blijven dan wel zoals ze zijn.

> Camera en GPS werken enkel via een beveiligde verbinding (https). Op het terrein gebruik je best **KarScan** op de gsm (zie "KarTracker op de gsm").

## [kar-planning | kartracker.karplanning] Kar Planning
Een overzicht van het hele wagenpark: per kar het karnummer, de status, de ploeg, het transporttype en de locatie. Voor het jaartal in de kopbalk krijgt elk actief festival een kolom met de afleverlocatie die voor de ploeg van de kar gepland is.

1. Kies bovenaan het **jaartal**.
2. Zoek of filter met de velden onder de kolomtitels.
3. Vink de karren aan waarvan je een karblad wil (of **Alles selecteren**).
4. Klik op **Afdrukken**. Je krijgt een PDF met één **karblad** per kar.

![Kar Planning](kar-planning.png)

Het karblad toont het karnummer, de ploeg en per festival waar en wanneer de kar geleverd en opgehaald wordt. Rechtsboven staat een QR-code met het karnummer (voor KarScan), lager een QR-code naar het formulier om een interventie aan te vragen voor die ploeg.

> Kar Planning is enkel om te bekijken. Wijzig karren in **KarManagement** en afleverlocaties in **Plan a kar**.

## [kar-map | kartracker.karmap] Kar Map
Een kaart met de **karren**, **afleverlocaties** en **distributiepunten** die een gekende locatie hebben.

1. Zet de lagen **Karren**, **Afleverlocaties** en **Distributiepunten** aan of uit.
2. Zet de laag **Grondplan** aan om het plan van het terrein over de kaart te leggen, en kies de **dekking**.
3. Zoek in de lijst op naam, karnummer of ploeg en klik op **Toon op kaart** om er naartoe te gaan.
4. Klik op een punt voor de gegevens: karnummer, status en ploeg, of naam, zone en omschrijving.

![Kar Map](kar-map.png)

> Iets zonder coördinaten staat wel in de lijst ("Geen locatie"), maar niet op de kaart. Vul de breedte- en lengtegraad aan op het scherm van dat gegeven.

## [plan-kar | kartracker.plankar] Plan a kar
Kies per ploeg de afleverlocatie voor elk actief festival van het jaartal.

1. Kies bovenaan in de kopbalk een **open jaartal**.
2. Kies een **team**.
3. Kies per festival de **afleverlocatie** (of "Geen afleverlocatie").
4. Klik op **Opslaan**.

Onder de tabel toont de **kaart afleverlocaties** waar de gekozen locaties liggen, eventueel met het grondplan.

![Plan a kar](plan-kar.png)

> Altsien Kernleden vullen dezelfde afleverlocaties in via de wizard van Altsien Select. Wat je hier opslaat, zien zij daar ook, en omgekeerd.

## [kar-management | kartracker.karmanagement] KarManagement
Het wagenpark: elke kar met zijn karnummer, status, ploeg, transporttype, laatste locatie en wanneer hij het laatst geregistreerd werd.

1. Klik op **Nieuwe kar** en vul minstens het **karnummer** in. Kies de status, de ploeg en het transporttype.
2. Klik bij een kar op **Wijzigen** om bv. de ploeg of de status aan te passen.
3. Zoek of filter met de velden onder de kolomtitels.
4. **Verwijderen** haalt een kar definitief uit het wagenpark.

![KarManagement](kar-management.png)

> De ploeg van een kar bepaalt naar welke afleverlocaties hij gaat (Plan a kar) en wat er in StockMaster voor die kar voorzien wordt. Een kar waarin nog voorraad zit, kan niet verwijderd worden.

## [distributiepunten | kartracker.distributiepunten] Distributiepunten
De distributiepunten van de organisatie: naam, coördinaten, terreinpositie en het verantwoordelijke Altsien Kernlid.

1. Klik op **Nieuw distributiepunt** en vul de gegevens in.
2. Klik op **Wijzigen** om ze aan te passen, of op **Verwijderen**.

![Distributiepunten](distributiepunten.png)

> Met breedte- en lengtegraad verschijnt het distributiepunt op **Kar Map**.

## [zones | kartracker.zones] Zone
De leveringszones, die je kiest bij een afleverlocatie.

1. Klik op **Nieuwe zone** en geef een naam.
2. Klik op **Wijzigen** om de naam aan te passen.
3. **Verwijderen** kan enkel als geen enkele afleverlocatie de zone nog gebruikt.

![Zone](zones.png)

## [afleverlocaties | kartracker.afleverlocaties] Afleverlocatie
De plaatsen waar karren geleverd worden: naam, omschrijving, zone, distributiepunt, coördinaten, terreinpositie, Altsien Kernlid en of de locatie actief is.

1. Klik op **Nieuwe afleverlocatie** en vul de gegevens in.
2. Klik op **Wijzigen** om ze aan te passen, of op **Verwijderen**.
3. Zet een locatie die je niet meer gebruikt op **Actief: Nee** in plaats van ze te verwijderen.

![Afleverlocatie](afleverlocaties.png)

> Enkel actieve afleverlocaties kan je kiezen in Plan a kar.

## [kar-statuses | kartracker.karstatuses] KarStatussen
De statussen die een kar kan hebben, bv. "Beschikbaar", "Geleverd" of "Opgehaald". Je kiest ze in KarManagement en bij een kar beweging.

1. Klik op **Nieuwe status** en geef een naam.
2. Klik op **Wijzigen** om ze te hernoemen.
3. **Verwijderen** kan enkel als geen enkele kar de status nog heeft.

![KarStatussen](kar-statuses.png)

## [delivery-dates | kartracker.leverdata] Leverdata
Stel per actief festival van het jaartal de **leverdatum** en de **ophaaldatum** in.

1. Kies bovenaan in de kopbalk een **open jaartal**.
2. Vul per festival de leverdatum en de ophaaldatum in.
3. Klik op **Opslaan**.

![Leverdata](delivery-dates.png)

> Deze data komen op het **karblad** dat je afdrukt vanuit Kar Planning.

## [data-upload | kartracker.dataupload] Gegevens uploaden/downloaden
De stamgegevens van KarTracker in bulk importeren en exporteren met Excel, één tegel per onderwerp: Karren, KarStatussen, Distributiepunten, Zones, Afleverlocaties en Leverdata.

1. Klik op een tegel en daarna op **Sjabloon downloaden** voor een leeg Excel-bestand met de juiste kolommen.
2. Vul het in, kies het bestand en klik op **Uploaden**.
3. Het resultaat toont per rij wat er aangemaakt werd en wat overgeslagen werd, met de reden.
4. Met **Volledige databank downloaden** exporteer je alles van dat onderwerp.

![Gegevens uploaden/downloaden](data-upload.png)

> Uploaden kan enkel met het recht **Aanmaken** op dit scherm.

## [groundplan | kartracker.groundplan] Grondplan
De grondplannen van de festivalsite, elk met een afbeelding en de coördinaten van zijn hoekpunten. Ze worden samen als laag getoond op Kar Map en bij Manuele kar beweging.

1. Klik op **Nieuw grondplan** en geef een naam.
2. Kies de **afbeelding** van het plan.
3. Vul de breedte- en lengtegraad van de **zuidwesthoek** (linksonder) en de **noordoosthoek** (rechtsboven) in, zodat het plan juist op de kaart ligt.
4. Klik op **Opslaan**. Met **Wijzigen** pas je de hoekpunten aan of kies je een nieuwe afbeelding.

![Grondplan](groundplan.png)

> Ligt het plan wat verschoven op Kar Map? Pas de hoekpunten in kleine stappen aan tot de wegen en gebouwen samenvallen.

## [roles | kartracker.roles] Rollen
Een rol bepaalt wat iemand in KarTracker mag doen, per scherm: **Bekijken**, **Aanmaken**, **Wijzigen** en **Verwijderen**.

1. Klik op **Nieuwe rol** en geef een naam (bv. "Logistiek", "Chauffeur").
2. Klik bij de rol op **Rechten** en vink per scherm aan wat de rol mag.
3. Sla de rechten op.

Enkele voorbeelden:
- **Manuele kar beweging**, Aanmaken: bewegingen registreren (ook met KarScan op de gsm).
- **Plan a kar** en **Leverdata**, Wijzigen: de planning en de data aanpassen.
- **Data Upload/Download**, Aanmaken: Excel-bestanden uploaden.
- **Grondplan**: wie Kar Map mag zien, ziet ook het grondplan. Grondplannen toevoegen of wijzigen vraagt rechten op het scherm Grondplan zelf.

![Rollen](roles.png)

## [users | kartracker.users] Gebruikers
Iedereen met toegang tot KarTracker en zijn huidige rol.

1. Kies bij een gebruiker de **rol** in de keuzelijst. De wijziging is meteen bewaard.
2. Klik op **Nieuwe gebruiker** om iemand toegang te geven. Bestaat het e-mailadres nog niet, dan wordt er een account gemaakt met de naam en het tijdelijke wachtwoord dat je invult.

![Gebruikers](users.png)

> Zonder rol ziet iemand enkel het KPI Overzicht, ook al heeft hij toegang tot de module.

## [phone] KarTracker op de gsm
KarTracker heeft ook een gsm-versie, zonder iets te installeren uit een app store. Open de module **Mobile App** op de startpagina voor het adres, de QR-code en de stappen om ze op je beginscherm te zetten.

- **KarScan**: scan de QR-code op het karblad, kies de nieuwe status en sla de beweging op met de GPS-locatie van je gsm.
- **Kar Planning**: alle karren met hun geplande afleverlocaties.
- **Kar Map**: de kaart met karren, afleverlocaties en distributiepunten.

Je logt in met hetzelfde account en hebt dezelfde rechten als op de pc.
