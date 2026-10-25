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
- **Karren per status** en **Karren per transporttype**.
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

## [karcode | kartracker.karcodesimulator] Karcode Simulator
Elke kar wordt afgesloten met een cijferslot. De code van dat slot volgt uit het karnummer via een vaste formule.

1. Tik het **karnummer** in met de toetsen van de rekenmachine, of typ het op je toetsenbord.
2. De **code** verschijnt meteen groot op het scherm. **=** rekent opnieuw, **C** wist alles en **⌫** wist het laatste cijfer.
3. Met het **kopieer**-icoon naast de code zet je ze op het klembord.

In plaats van te typen kan je ook op **Scan QR-code van de kar** klikken en de camera op de QR-code van de kar richten: de laatste 3 cijfers van de QR-code worden het karnummer en de code verschijnt.

Onder de rekenmachine staan je **laatste berekeningen**; klik er één aan om die kar opnieuw te tonen.

> De formule zelf zie je hier niet. Beheerders passen ze aan onder **Instellingen**.

## [kar-planning | kartracker.karplanning] Kar Planning
Een overzicht van het hele wagenpark: per kar het karnummer, de status, de ploeg, het transporttype en de locatie. Voor het jaartal in de kopbalk krijgt elk actief festival een kolom met de afleverlocatie die voor de ploeg van de kar gepland is. Heeft de ploeg een festival afgevinkt in Altsien Select, dan staat er **Niet actief** in een lege cel en telt die als gepland.

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
Kies per ploeg de afleverlocatie voor elk festival van het jaartal.

Het scherm opent op een **overzicht van alle karren** (van actieve ploegen): per kar zie je hoeveel festivals van zijn ploeg al een afleverlocatie hebben (bv. "2/3 festivals", groen zodra alles ingevuld is). Afleverlocaties horen bij de ploeg, dus alle karren van dezelfde ploeg tonen hetzelfde cijfer. Er tellen enkel de festivals die de ploeg in Altsien Select koos; koos ze er nog geen, dan tellen alle actieve festivals.

1. Kies bovenaan in de kopbalk een **open jaartal**.
2. Zoek een kar (karnummer of ploeg) en klik op **Plannen**.
3. Kies per festival de **afleverlocatie** (of "Geen afleverlocatie").
4. Klik op **Opslaan** en daarna op **Terug naar overzicht**.

Onder de tabel toont de **kaart afleverlocaties** waar de gekozen locaties liggen, eventueel met het grondplan.

![Plan a kar](plan-kar.png)

> Altsien Kernleden vullen dezelfde afleverlocaties in via de wizard van Altsien Select. Wat je hier opslaat, zien zij daar ook, en omgekeerd.

## [leveringsvolgorde | kartracker.leveringsvolgorde] Leveringsvolgorde
Zet de afleverlocaties in de volgorde waarin ze over het terrein beleverd worden, zodat karren in de juiste volgorde geladen en geleverd worden.

Links staat de **levertoer**, genummerd 1, 2, 3, … in volgorde van levering. Rechts staan de **actieve afleverlocaties die nog niet in de toer zitten** (op naam; per lijn de omschrijving met daaronder naam en zone, en een zoekveld).

1. Klik op de **pijl naar links** naast een locatie (of sleep ze naar links) om ze aan de toer toe te voegen. **Alle getoonde toevoegen** voegt alles toe wat de zoekterm rechts toont.
2. Sleep de lijnen links in de juiste volgorde.
3. Haal een locatie uit de toer met de **pijl naar rechts** (of sleep ze terug naar rechts).
4. Klik op **Opslaan**. Elke locatie links krijgt haar positie als **Terreinpositie** (1, 2, 3, …); locaties rechts krijgen geen terreinpositie.

Naast elke lijn staat de **opgeslagen terreinpositie**, zodat je voor het opslaan ziet wat er verandert: in de toer (links) "was 3" (oranje als Opslaan ze wijzigt) of "nieuw" (had nog geen positie), rechts "was 3 → wordt leeg" (Opslaan maakt ze leeg). Bovenaan zie je hoeveel locaties er wijzigen.

Met **Kaart** (rechtsboven) open je het grondplan met de toer zoals hij nu op het scherm staat: elke locatie toont haar nieuwe nummer en, tussen haakjes, het opgeslagen (bv. "5 (was 3)"). Een stippellijn volgt de toer van 1 tot het einde, zodat een onlogische volgorde opvalt. Ga met de muis over een locatie om haar naam te zien.

> Zolang je niet opslaat, is er niets gewijzigd: **Wijzigingen ongedaan maken** zet de laatst opgeslagen volgorde terug. Inactieve afleverlocaties staan niet op dit scherm en houden hun terreinpositie.

## [initial-delivery | kartracker.initieleleverplanning] Initiële leverplanning
In de groep **Planningsanalyses** staan analyses van wat voor, tijdens of na het festival georganiseerd moet worden. **Initiële leverplanning** toont welke karren bij de start geleverd moeten worden en waar, voor het jaartal in de kopbalk.

Een kar gaat naar de afleverlocatie die in **Plan a kar** voor zijn ploeg gepland is op het **eerste festival van die ploeg** (het vroegste festival dat de ploeg in Altsien Select aanduidde, of het eerste festival van het jaar zolang ze niets aanduidde). Karren zonder ploeg, of waarvan de ploeg voor dat festival nog geen locatie plande, staan er niet bij.

- Bovenaan staan het **totaal** aantal karren en het aantal **per distributiepunt**.
- De lijst is eerst gegroepeerd per **distributiepunt** (paarse kopregel met het aantal karren). De distributiepunten staan in de volgorde van hun eerste locatie in de levertoer.
- Daarbinnen per afleverlocatie een grijze kopregel met de **terreinpositie** (#1, #2, …), de naam en omschrijving, de zone en het aantal karren. De locaties staan in de volgorde van de **Leveringsvolgorde**; locaties zonder positie ("geen positie") komen achteraan.
- Daaronder de karren (op karnummer) met ploeg, transporttype, status, het festival waarvoor ze geleverd worden en de leverdatum uit **Leverdata**.

**Filteren**: onder de kolomkoppen staat een filterrij. Kies bij **Status** een status in de keuzelijst, of typ in de andere kolommen een stukje tekst (de filter onder **Positie** zoekt in de positie, naam, omschrijving en zone van de locatie). Locaties en distributiepunten zonder passende kar verdwijnen en de aantallen volgen de filter. **Filters wissen** zet alles terug. Alles selecteren, de groepsvakjes en Shift-klik werken enkel op de getoonde karren; al aangevinkte karren blijven aangevinkt (en worden afgedrukt), ook als een filter ze verbergt.

**Leverplanning afdrukken** voor de chauffeurs:

1. Vink de karren aan. **Shift-klik** vinkt de hele reeks aan (of uit) tussen je vorige en deze klik; het vakje op een distributiepunt- of locatieregel doet al zijn karren tegelijk, het vakje in de kop alles.
2. Vink eventueel **Kaart toevoegen** aan.
3. Klik op **Print leverplanning**. Je krijgt een liggende PDF met per distributiepunt (**Ophalen bij**) de afleverlocaties in de volgorde van de levertoer, hun karren en een leeg vakje **Geleverd** om af te vinken.

Met **Kaart toevoegen** komt er een pagina **Leverroute** bij: het grondplan met de route van 1 tot het einde (stippellijn), de afleverlocaties als genummerde bolletjes, locaties zonder positie als grijze puntjes en de distributiepunten als zwarte vierkantjes. De kaart zoomt in op de afgedrukte locaties. Rechts staat de legende met de stops van de levertoer (positie, omschrijving en zone). Locaties buiten het grondplan of zonder coördinaten worden onder de legende opgesomd.

> Dit scherm wijzigt niets. Pas de volgorde aan in **Leveringsvolgorde** en de locaties in **Plan a kar**.

## [kar-moves | kartracker.karverplaatsingen] Verplaatsingen tussen festivals
**Verplaatsingen tussen festivals** toont welke karren tussen twee festivals op het terrein verplaatst moeten worden, voor het jaartal in de kopbalk. Dat is nodig wanneer een ploeg in **Plan a kar** op het volgende festival een andere afleverlocatie heeft dan op het vorige.

Kies bovenaan **Van festival** en **Naar festival** (de actieve festivals van het jaar, in volgorde van datum; het scherm opent op de eerste twee). Een kar staat in de lijst wanneer:

- zijn ploeg aan **beide** festivals deelneemt (de festivals die de ploeg in Altsien Select aanduidde, of alle festivals zolang ze niets aanduidde);
- voor de ploeg op **beide** festivals een afleverlocatie gepland is;
- en die twee locaties **verschillen**.

Karren die op dezelfde plek blijven, of waarvoor nog niet alles gepland is, staan er niet bij. Naast de keuzelijsten staat de leverdatum van het **Naar**-festival (uit **Leverdata**).

- De lijst is gegroepeerd per **ophaallocatie** (waar de karren op het Van-festival staan): een paarse kopregel met de **terreinpositie** (#1, #2, …), naam, zone en het aantal karren, in de volgorde van de **Leveringsvolgorde** (locaties zonder positie achteraan).
- Daaronder de karren (op karnummer) met ploeg, transporttype, status en de kolom **Naar**: de afleverlocatie waar de kar naartoe moet, met haar positie en zone.

**Filteren** werkt zoals in de Initiële leverplanning: Status via de keuzelijst, de andere kolommen met een stukje tekst (de filters onder **Van** en **Naar** zoeken in positie, naam, omschrijving en zone). **Filters wissen** zet alles terug.

**Verplaatsingen afdrukken** voor de chauffeurs:

1. Vink de karren aan (Shift-klik voor een reeks, het vakje op een ophaallocatie voor al haar karren, het vakje in de kop voor alles).
2. Vink eventueel **Kaart toevoegen** aan.
3. Klik op **Print verplaatsingen**. Je krijgt een liggende PDF met per ophaallocatie (**Ophalen bij**) de karren, waar ze naartoe moeten en een leeg vakje **Verplaatst** om af te vinken.

Met **Kaart toevoegen** komt er een kaartpagina bij: het grondplan met de ophaallocaties als paarse bolletjes, de locaties die enkel karren ontvangen als groene bolletjes, en een **pijl per verplaatsing** met het aantal karren. De bolletjes dragen de positie in de levertoer; een locatie zonder positie krijgt een letter (A, B, …). Rechts staat de legende met alle locaties.

> Dit scherm wijzigt niets. Pas de locaties aan in **Plan a kar** en de volgorde in **Leveringsvolgorde**.

## [special-tour-planning | kartracker.levertoerplanning] Speciale levertoeren-planning
**Speciale levertoeren-planning** toont welke karren een speciale levertoer (bijvoorbeeld de wastoer of de ijsblokkentoer) op een festival aandoet en waar ze staan, voor het jaartal in de kopbalk.

Kies bovenaan het **Festival** (het scherm opent op het eerste festival van het jaar) en één of meer **Levertoeren**. Een kar staat in de lijst wanneer:

- zijn ploeg op haar ploegfiche (MasterData > Ploegen, veld **Levertoeren**) aan minstens één gekozen levertoer gekoppeld is;
- de ploeg aan het festival deelneemt (de festivals die ze in Altsien Select aanduidde, of alle festivals zolang ze niets aanduidde);
- en voor de ploeg op dat festival een afleverlocatie gepland is in **Plan a kar**.

Een kar van een ploeg die op twee gekozen levertoeren staat, verschijnt maar één keer; de kolom **Levertoer** toont dan beide.

De lijst toont de **stops** van de toer: de afleverlocaties in de volgorde van de **Leveringsvolgorde** (locaties zonder positie daarna, op naam), genummerd **Stop 1, 2, 3, …**, elk met de karren die er staan (op karnummer). Distributiepunten staan er niet bij: de toer komt langs de karren, er wordt niets opgehaald. Filteren en aanvinken (Shift-klik voor een reeks) werken zoals in de Initiële leverplanning. **Print leverplanning** maakt een PDF met de stops, de levertoeren en het festival bovenaan en per kar een vakje **Geleverd**; met **Kaart toevoegen** komt er een kaartpagina bij met elke stop als genummerd bolletje en de route van stop 1 tot de laatste. Zet de afleverlocaties in **Leveringsvolgorde** voor een logische route.

> Dit scherm wijzigt niets. Koppel ploegen aan een levertoer op hun ploegfiche en pas hun locatie aan in **Plan a kar**.

## [kar-management | kartracker.karmanagement] KarManagement
Het wagenpark: elke kar met zijn karnummer, status, ploeg, transporttype, laatste locatie en wanneer hij het laatst geregistreerd werd.

1. Klik op **Nieuwe kar** en vul minstens het **karnummer** in. Kies de status, de ploeg en het transporttype.
2. Klik bij een kar op **Wijzigen** om bv. de ploeg of de status aan te passen.
3. Zoek of filter met de velden onder de kolomtitels.
4. **Verwijderen** haalt een kar definitief uit het wagenpark.

![KarManagement](kar-management.png)

> De ploeg van een kar bepaalt naar welke afleverlocaties hij gaat (Plan a kar) en wat er in StockMaster voor die kar voorzien wordt. Een kar waarin nog voorraad zit, kan niet verwijderd worden. Klik je in TagScan op een karnummer, dan opent het formulier van die kar hier meteen.

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

## [special-tours | kartracker.specialelevertoeren] Speciale levertoeren
De speciale levertoeren die regelmatig bij een aantal ploegen langsgaan, bijvoorbeeld **Kleine wastoer**, **Grote wastoer** of **Ijsblokken**.

1. Klik op **Nieuwe levertoer**, geef een naam en eventueel een beschrijving (wat de toer controleert en wanneer).
2. Klik op **Wijzigen** om de naam, beschrijving of status aan te passen. Een levertoer die niet **Actief** is, kan niet meer op een ploegfiche gekozen worden.
3. **Verwijderen** kan enkel als geen enkele ploeg nog aan de levertoer gekoppeld is.

De kolom **Ploegen** toont welke ploegen op de toer staan. Die koppel je op de ploegfiche in MasterData (veld **Levertoeren**); de planning per festival zie je op **Speciale levertoeren-planning**.

## [afleverlocaties | kartracker.afleverlocaties] Afleverlocatie
De plaatsen waar karren geleverd worden: naam, omschrijving, zone, distributiepunt, coördinaten, terreinpositie, Altsien Kernlid en of de locatie actief is.

1. Klik op **Nieuwe afleverlocatie** en vul de gegevens in.
2. Klik op **Wijzigen** om ze aan te passen, of op **Verwijderen**.
3. Zet een locatie die je niet meer gebruikt op **Actief: Nee** in plaats van ze te verwijderen.

De **terreinpositie** is een getal: de plaats van de locatie in de levertoer (1 = eerst beleverd). Je zet ze het makkelijkst op het scherm **Leveringsvolgorde**.

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
3. Het resultaat toont per rij wat er aangemaakt, bijgewerkt of overgeslagen werd, met de reden.
4. Met **Volledige databank downloaden** exporteer je alles van dat onderwerp.

Bestaat een lijn al (zelfde karnummer, of zelfde naam ongeacht hoofdletters), dan wordt die **bijgewerkt** in plaats van een nieuwe aangemaakt. Enkel ingevulde cellen overschrijven; een lege cel behoudt de huidige waarde. Zo kan je een export aanpassen en opnieuw uploaden. Een waarde wissen doe je op het scherm zelf. Bij KarStatussen en Zones (enkel een naam) blijft een bestaande naam ongewijzigd.

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

## [settings | kartracker.settings] Instellingen
Hier staat de **karcode formule** waarmee de Karcode Simulator de code van een slot berekent.

- De formule werkt zoals in Excel: gebruik **kar** voor het karnummer, de bewerkingen **+ - * / ^**, haakjes en de functies **LEFT**, **RIGHT**, **MID**, **MOD**, **INT**, **ROUND** en **ABS**.
- Zet **;** tussen de argumenten van een functie; een kommagetal schrijf je met **,** of **.**.
- Voorbeeld: **LEFT(kar*500+3118; 4)** geeft voor kar 36 de code **2111** (36 × 500 + 3118 = 21118, de eerste 4 cijfers).

Test een formule eerst bij **Testen** met een karnummer: het resultaat verschijnt meteen, zonder iets op te slaan. Met **Opslaan** wordt de formule actief voor iedereen; enkel wie "bewerken" mag op dit scherm kan opslaan. Onderaan zie je wie de formule het laatst wijzigde.

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
- **Karcode Simulator**: scan de QR-code op de kar (of tik het karnummer in) en zie meteen de code van het slot.

Je logt in met hetzelfde account en hebt dezelfde rechten als op de pc.
