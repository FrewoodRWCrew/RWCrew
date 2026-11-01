# Scans

De module Scans heeft twee delen, met dezelfde rollen en gebruikers: de **RFID-tags** en de **polsbanden (QR)**. Het RFID-deel verwerkt de CSV-bestanden van de RFID-scanners. Elk bestand komt binnen in de map **Unreaded Tags**, wordt gescand en geregistreerd, en elke gelezen tag (EPC) wordt gekoppeld aan het register in **TagBeheer**. Acties in het bestand, zoals **Assignment**, maken daarna tags aan voor een product.

## [start] Zo werkt Scans
Een gescand bestand doorloopt altijd dezelfde weg:

1. Een scanner (bv. een Raspberry Pi) stuurt zijn CSV-bestand via HTTPS naar Scans. Het komt in de map **Unreaded Tags** terecht.
2. **Scannen** registreert het bestand in **Tag Headergegevens**, leest elke regel in **Tag Regelgegevens** en zet het bestand in de map **Read Tags**. Dit gebeurt ook automatisch op de achtergrond (zie Instellingen).
3. Elke regel wordt gekoppeld aan de tag met dezelfde EPC in **TagBeheer** en aan de scanner uit het register **Scanners**.
4. Regels met een actie die Scans kent (vandaag **Assignment**) wachten op verwerking. Je verwerkt ze via de blauwe balk bovenaan.

### Twee soorten status
- **Matchstatus** (op een regel): werd de EPC gevonden in TagBeheer? Geconverteerd, Geen match of Geannuleerd.
- **Verwerking** (op een regel en een bestand): werd de actie uitgevoerd? **Nieuw** (oranje), **Geladen** (groen) of **Geannuleerd** (rood). De rijen in de tabellen krijgen die kleur.

### De blauwe balk "wachten op verwerking"
Staan er gescande regels klaar met een actie, dan zie je bovenaan elk Scans scherm een **blauwe balk** met het aantal. Klik op **Bekijken** om ze te verwerken (zie "Wachtende acties verwerken").

> Op elk scherm opent **Help bij dit scherm** rechtsboven het stuk van deze handleiding over dat scherm. De volledige handleiding vind je onderaan het menu links.

## [overview] Scans Overzicht
Het startscherm van Scans: de tags in één oogopslag.

- **Tegels** bovenaan: totaal aantal tags, ongelezen CSV's (nog in Unreaded Tags), toegewezen en niet-toegewezen tags, verloren of beschadigde tags en het aantal tags dat deze maand geregistreerd werd.
- **Tags per status**: de verdeling van alle tags.
- **Registraties over tijd**: nieuwe tags per week, de laatste 12 weken.
- **Top producten**: de 5 producten met de meeste tags.

![Het overzicht van Scans](overview.png)

> Staan er veel **ongelezen CSV's**, dan werd er nog niet gescand. Kijk bij Instellingen of de automatische scan aan staat, of klik op **Scannen** in Tag Headergegevens.

## [pending | tagscan.tag-linedata] Wachtende acties verwerken
Gescande regels met een actie (bv. **Assignment**: tags aanmaken voor een product) wachten tot iemand ze verwerkt.

1. Klik in de blauwe balk bovenaan op **Bekijken**. Je ziet de wachtende regels, gegroepeerd per bestand.
2. Kies per bestand het **product** (verplicht). Bij elk bestand zie je ook wat de scanner zelf als product of opmerking meestuurde.
3. Klik op **Bestand verwerken** voor één bestand, of op **Alles verwerken** voor alle bestanden.
4. Het resultaat toont per regel wat er gebeurde: **Aangemaakt** (nieuwe tag), **Product toegewezen** (bestaande tag zonder product), **Al toegewezen** of **Fout**.

- Een regel die je niet wil verwerken, **annuleer** je met een reden (verplicht). Hij krijgt dan de status Geannuleerd.
- Een tag die al een product heeft, wordt nooit gewijzigd.
- Regels met de actie **Book In** worden hier ook geteld, maar ingeboekt via StockMaster (**Open Inboeken** in hun bestandsblok); **Alles verwerken** laat ze ongemoeid.
- Om te verwerken heb je het recht **Wijzigen** op Tag Regelgegevens én **Aanmaken** op TagBeheer nodig (er worden tags aangemaakt). Annuleren kan met Wijzigen op Tag Regelgegevens.

## [files | tagscan.dashboard] CSV Bron Bestanden
De mappen en bestanden op de server zoals de scanners ze aanleveren, met een voorbeeld van de inhoud.

1. Klik links op een map, bv. **Unreaded Tags** (nog te scannen) of **Read Tags** (al gescand).
2. Klik op een bestand om de inhoud te bekijken. Van een groot bestand zie je enkel het eerste deel.
3. Met **Vernieuwen** laad je de lijst opnieuw.
4. Wil je bestanden opruimen? Vink ze aan en klik op **Verwijderen**.

![CSV Bron Bestanden](files.png)

> Verwijderen haalt het bestand definitief van de server. Een bestand dat al geregistreerd is, blijft wel in Tag Headergegevens staan. Daarvoor heb je het recht **Verwijderen** op dit scherm nodig.

## [header-data | tagscan.tag-headerdata] Tag Headergegevens
Elk gescand CSV-bestand op één lijn: de bestandsnaam, wanneer het geregistreerd werd, het aantal regels, de scanner (naam, type, locatie, technologie), de modus, de actie, de **karnummers** van zijn regels, de **CSV Comment** (de Comment-cellen van het bestand samen), de verwerkingsstatus en het commentaar bij de verwerking.

1. Klik op **Scannen** om de nieuwe bestanden in Unreaded Tags meteen te verwerken. De scanlog toont per bestand: **Geregistreerd**, **Al geregistreerd** of **Fout**.
2. Zoek met de filters onder de kolomtitels, bv. op bestandsnaam, scanner of verwerkingsstatus.
3. Klik bij een bestand op het PDF-icoon voor een **PDF-overzicht** van het bestand en zijn regels.
4. Een bestand verkeerd ingelezen? **Verwijderen** wist de registratie én al zijn regels in Tag Regelgegevens. Het CSV-bestand zelf blijft staan.

![Tag Headergegevens](header-data.png)

> Scannen kan enkel met het recht **Aanmaken** op dit scherm, verwijderen met **Verwijderen**.

## [line-data | tagscan.tag-linedata] Tag Regelgegevens
Elke gescande CSV-regel, aangevuld met de tag uit TagBeheer: EPC, RSSI, antenne, aantal, laatst gezien, product, serienummer, karnummer, fabrikant, batchnummer, **CSV Comment** (de Comment-cel van die regel), matchstatus, verwerking en **Commentaar** (bv. de reden van een annulering).

1. Zoek met de filters onder de kolomtitels, bv. op EPC, product, scanner of status.
2. Klik op **Groeperen per product** om per bestand en product een subtotaal te zien, of op **Groeperen per kar** om de regels van elk bestand met een kar (een tag met karnummer) onder die kar te zien (dit staat standaard aan). Klik op een EPC, product of karnummer om die tag, productfiche of kar meteen te openen.
3. Werd TagBeheer of het scannerregister intussen aangevuld? Klik op **Synchro**: alle regels worden opnieuw gekoppeld aan de tags en scanners van nu.
4. Een regel die niet klopt, kan je **annuleren**.

![Tag Regelgegevens](line-data.png)

> **Geen match** betekent dat de EPC (nog) niet in TagBeheer staat. Voeg de tag toe in TagBeheer of via een Assignment, en klik daarna op **Synchro**.

## [tag-management | tagscan.tag-management] TagBeheer
Het register van alle RFID-tags: EPC / UID, status, toegewezen product en serienummer, karnummer (de kar uit KarTracker waarop de tag hangt), data, laatste lezing en locatie, fabrikant, batchnummer, vijf notitievelden en **CSV Comment**: de laatste Comment uit een gescande CSV met deze EPC. Die vult Scans zelf in; je kan ze niet wijzigen.

1. Klik op **Nieuwe tag** om een tag te registreren. Vul minstens de **EPC / UID** in.
2. Klik bij een tag op **Wijzigen** om bv. het product, het serienummer, het karnummer of de **status** aan te passen (Actief, Inactief, Verloren, Beschadigd, Uit dienst).
3. Zoek met de filters onder de kolomtitels, bv. op status of product.
4. Vink tags aan en klik op **Verwijderen** om er meerdere tegelijk te verwijderen.

![TagBeheer](tag-management.png)

> Klik je in Tag Regelgegevens op een EPC, dan opent TagBeheer meteen het formulier van die tag. Veel tags tegelijk registreren of wijzigen? Gebruik een Excel-bestand in **Data Upload/Download**.

## [scanners | tagscan.scanners] Scanners
Het register van de fysieke RFID-scanners die de CSV-bestanden maken: naam, type, technologie, locatie, beschrijving en drie infovelden.

1. Klik op **Nieuwe scanner** en vul minstens de naam in, precies zoals de scanner hem in zijn CSV schrijft.
2. Klik bij een scanner op **Wijzigen** om de gegevens aan te passen.
3. Klik op **API-sleutel** om een sleutel aan te maken voor het apparaat. Kopieer de sleutel en de upload-URL meteen naar de configuratie van het apparaat.

![Scanners](scanners.png)

> De API-sleutel wordt maar **één keer** getoond. Een nieuwe sleutel aanmaken maakt de vorige meteen ongeldig, en een sleutel werkt enkel op de omgeving (test of productie) waar hij gemaakt werd.

## [data-upload | tagscan.dataupload] Data Upload/Download
Tags en scanners in bulk importeren en exporteren met Excel, één tegel per tabel.

1. Klik op **Sjabloon downloaden** voor een leeg Excel-bestand met de juiste kolommen.
2. Vul het in en kies het bij **Excel-bestand**. Klik op **Uploaden**.
3. Het resultaat toont per rij: **Aangemaakt**, **Bijgewerkt** of **Fout** (met de reden).
4. Met **Tags downloaden** of **Scanners downloaden** exporteer je de volledige lijst.

![Data Upload/Download](data-upload.png)

> Een bestaande EPC / UID of scannernaam wordt **bijgewerkt**, niet dubbel aangemaakt. Kolommen die niet in je bestand staan, blijven ongewijzigd (een oud sjabloon zonder bv. kar_nummer wist dus niets). De kolom **csv_comment** in de export is enkel ter info en wordt bij het uploaden genegeerd. De API-sleutel van een scanner blijft behouden. Uploaden kan enkel met het recht **Aanmaken** op dit scherm.

## [wristband-files | tagscan.wristband-files] JSON Bron Bestanden
Hetzelfde scherm als CSV Bron Bestanden, voor de polsbanden. Elk bericht van het polsbandbedrijf wordt als .json-bestand bewaard, in één map per dag. Bestandsnamen beginnen met het uur; testberichten eindigen op **_test**.

- Kies links een dag en in het midden een bestand: rechts zie je de inhoud.
- Met het recht "verwijderen" vink je bestanden aan en verwijder je ze van de server. De scan blijft in de tabel Scans staan.

> Bestanden bevatten namen en soms e-mailadressen. Ze worden niet automatisch opgeruimd: verwijder ze zelf als ze niet meer nodig zijn.

## [wristband-scans | tagscan.wristband-scans] Scans
Elk ontvangen polsbandbericht als rij in een tabel, ook geweigerde berichten en berichten die niet voor de balie zijn. Filter op dag, status, scanner of ploeg. Met het oog-icoon zie je het bericht zoals het binnenkwam.

- **geen ploeg met deze naam**: de ploegnaam komt niet overeen met een ploeg uit MasterData. De scan verschijnt toch aan de balie, en de balie kiest zelf de ploeg.
- **aan geen enkele balie**: de ploeg heeft geen reservatie. Een balie toont enkel scans van ploegen met een reservatie op een festival van het seizoen (nu Atelier, later Walkies).

Heeft een ploeg uitzonderlijk reservaties bij twee balies, dan staat de scan aan beide; wie hem eerst gebruikt, verwerkt hem.

## [wristband-scanners | tagscan.wristband-scanners] Scanners (polsbanden)
Elke scanner van het polsbandbedrijf verschijnt automatisch bij zijn eerste bericht. Geef hem een naam (bv. "Balie 1"): die wordt bewaard als je het vak verlaat. Aan de balie kies je bovenaan welke scanner daar staat.

## [wristband-test | tagscan.wristband-test] Test-scan
Om alles te testen voor de echte koppeling met het polsbandbedrijf (vanaf mei 2027). Het bericht gaat door **dezelfde verwerking** als de webhook, zonder token, en is gemarkeerd als **Test**. Dit scherm staat ook in Atelier en Walkies, elk met zijn eigen recht.

- **Formulier**: kies een bestaande scanner of typ een nieuw toestel-id en vul de persoon en de ploeg in. Rechts zie je het bericht dat verstuurd wordt.
- **JSON-bestand**: sleep een .json-bestand in het vak, kies een bestand of plak het bericht. Het wordt verstuurd zoals het is.

Klik op **Versturen**: onder de knop zie je wat er met het bericht gebeurde en of een balie het toont.

## [roles | tagscan.roles] Rollen
Een rol bepaalt wat iemand in Scans mag doen, per scherm: **Bekijken**, **Aanmaken**, **Wijzigen** en **Verwijderen**.

1. Klik op **Nieuwe rol** en geef een naam (bv. "Scanner operator", "Beheerder").
2. Klik bij de rol op **Rechten** en vink per scherm aan wat de rol mag.
3. Sla de rechten op.

Wat de rechten betekenen:
- **CSV Bron Bestanden**, Verwijderen: bestanden van de server verwijderen.
- **Tag Headergegevens**, Aanmaken: scannen. Verwijderen: een registratie met zijn regels wissen.
- **Tag Regelgegevens**, Wijzigen: Synchro, wachtende acties verwerken (samen met Aanmaken op TagBeheer) en regels annuleren.
- **TagBeheer** en **Scanners**: aanmaken, wijzigen en verwijderen in het register.
- **Data Upload/Download**, Aanmaken: Excel-bestanden uploaden.

![Rollen](roles.png)

## [users | tagscan.users] Gebruikers
Iedereen met toegang tot Scans en zijn huidige rol.

1. Kies bij een gebruiker de **rol** in de keuzelijst. De wijziging is meteen bewaard.
2. Klik op **Nieuwe gebruiker** om iemand toegang te geven. Bestaat het e-mailadres nog niet, dan wordt er een account gemaakt met de naam en het tijdelijke wachtwoord dat je invult.

![Gebruikers](users.png)

> Zonder rol ziet iemand enkel het Scans Overzicht, ook al heeft hij toegang tot de module.

## [settings | tagscan.settings] Instellingen
Hoe Scans de CSV-bestanden van de apparaten ontvangt en scant.

- **Ontvangstmap**: de map op de server waar de bestanden binnenkomen, in de submap "Unreaded Tags". Laat de standaardwaarde staan, tenzij de beheerder van de server iets anders vraagt.
- **Upload-URL voor apparaten**: het adres waarnaar een scanner zijn bestanden stuurt, samen met zijn eigen API-sleutel (zie Scanners). Klik op **Kopiëren** en plak het in de configuratie van het apparaat.
- **Automatische scan**: scant Unreaded Tags op de achtergrond, net zoals de knop Scannen. Zet het aan en kies het **interval** in seconden (standaard 60). Je ziet ook wanneer de laatste automatische scan liep en wat hij vond.
- **Webhook voor het polsbandbedrijf**: het adres waarop het polsbandbedrijf zijn scans stuurt en de map met de JSON-bestanden. Met **Genereer token** maak je de token van deze omgeving aan; hij wordt maar één keer getoond, dus kopieer hem meteen. **Vervang token** en **Intrekken** maken de oude token meteen ongeldig. Zonder token wordt elk bericht geweigerd (Test-scan werkt wel). De link **Uitleg koppeling polsbandbedrijf** opent een PDF die je naar het bedrijf kan doorsturen.

![Instellingen](settings.png)

> Een wijziging werkt meteen, zonder de server te herstarten.

## [wristband-integration | tagscan.settings] Koppeling met het polsbandbedrijf
Deze uitleg kan je zo doorsturen naar het polsbandbedrijf. Er staat geen token of serveradres in: die geven we apart.

### Hoe het werkt
Na elke scan aan een van onze balies stuurt het polsbandbedrijf meteen één JSON-bericht via HTTPS naar onze webhook. Wij bewaren het bericht als bestand, zetten het in onze tabel met scans en tonen de persoon binnen enkele seconden aan de juiste balie.

### Wat het polsbandbedrijf van ons krijgt
- Het **webhookadres** en de **token**, voor elke omgeving apart: test en productie hebben een eigen adres en een eigen token.
- Het adres staat in Scans > Instellingen. De token wordt daar aangemaakt en maar één keer getoond.
- Stuur de token **apart en beveiligd** door (bv. via een wachtwoordkluis of een eenmalige link), nooit in dezelfde mail als het adres en nooit in een document.

### Wat er bij elke scan verstuurd wordt
Een **POST** met een JSON-bericht in deze vorm:

```
{
  "event": "crew_participation",
  "token": "<de token die u van ons kreeg>",
  "data": {
    "id": "557087",
    "device": { "id": 14734, "name": "SUN0410" },
    "person": {
      "first_name": "Voornaam",
      "last_name": "Familienaam",
      "email": "optioneel",
      "size": "optioneel, bv. M"
    },
    "attending_group": { "name": "Naam van de ploeg" },
    "profile": { "name": "optioneel" }
  }
}
```

- **Verplicht**: event, token, data.device.id, data.person.first_name en data.person.last_name.
- **data.id** is het polsbandnummer van dit festival.
- **data.device.id** duidt de scanner aan: elke scanner aan een balie moet zijn eigen vaste id houden.
- **data.attending_group.name** is de ploeg. We herkennen de naam ook als die bij ons als alias van een ploeg staat.
- Andere events dan crew_participation worden gelogd maar niet aan een balie getoond.

### Onze antwoorden
- **200**: aanvaard (of gelogd, bij een ander event).
- **400**: geen leesbare JSON, of er ontbreekt een verplicht veld.
- **401**: verkeerde of ontbrekende token.

Verstuur een bericht alleen opnieuw als er geen antwoord kwam of bij een 5xx-fout. Een bericht dat twee keer aankomt, telt als twee scans.

### Een token vervangen
Een nieuwe token maakt de oude meteen ongeldig. Spreek dus eerst een moment af met het polsbandbedrijf, buiten de festivaldagen.
