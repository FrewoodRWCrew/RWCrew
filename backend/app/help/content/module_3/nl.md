# Interventies

Interventies registreert en volgt de interventieaanvragen van de verenigingen op: een ploeg heeft iets nodig aan haar kar of op haar standplaats, en TeamKar gaat langs. Elke aanvraag krijgt een nummer, een status en (eventueel) een uitvoerder.

## [start] Zo werkt Interventies
Een aanvraag komt op drie manieren binnen, en volgt daarna altijd dezelfde weg:

1. **Openbaar formulier**: een medewerker van de ploeg scant de QR-code op de kar en vult het formulier in, zonder in te loggen.
2. **Interventieaanvragen**: iemand van de organisatie registreert de aanvraag zelf, bv. na een telefoontje.
3. **Gsm-app**: in de gsm-app (Interventies > Akties) maak je een aanvraag aan onderweg.

Elke nieuwe aanvraag krijgt automatisch een **aanvraagnummer** en gaat per e-mail (met de leveringsbon als PDF) naar iedereen op de **Mailinglijst**. Daarna wijs je een **uitvoerder** en een **Team kar** toe en zet je de **status** tot de aanvraag afgesloten is.

> Op elk scherm opent **Help bij dit scherm** rechtsboven het stuk van deze handleiding over dat scherm. De volledige handleiding vind je onderaan het menu links.

## [overview] KPI overzicht
Het startscherm van Interventies: de aanvragen in één oogopslag.

- **Tegels** bovenaan: het totaal aantal aanvragen, hoeveel er nog open staan en hoeveel er afgesloten zijn.
- **Aanvragen per status**: hoeveel aanvragen elke status nu hebben.
- **Aanvragen per team**: hoeveel aanvragen elke ploeg indiende.

![Het KPI overzicht](overview.png)

## [requests | interventionrequests.requests] Interventieaanvragen
Alle aanvragen met hun nummer, wanneer ze ingediend werden, de ploeg, het karnummer, de vraag, de medewerker en zijn gsm-nummer, de voorkeur voor levering, de afleverplaats en zone, de status, de uitvoerder en de Team kar.

1. Klik op **Nieuwe aanvraag** om een aanvraag te registreren. Kies de ploeg (of **Andere** en typ de naam) en vul minstens de vraag in.
2. Klik bij een aanvraag op **Wijzigen** om de **status**, de **uitvoerder** of de **Team kar** te kiezen, of de gegevens aan te passen.
3. **Groepeer op Voorkeur Levering** zet de aanvragen per leverdag onder elkaar (standaard aan). Met **Toon Alle Interventies** zie je ook de afgesloten aanvragen; **Toon Open Interventies** toont enkel wat nog open staat.
4. Zoek met de filters onder de kolomtitels, bv. op ploeg, karnummer of status.
5. Het PDF-icoon downloadt de **leveringsbon** van een aanvraag.

![Interventieaanvragen](requests.png)

> De link **Test: open het openbare aanvraagformulier** opent het formulier dat de ploegen via de QR-code zien, zodat je het kan uitproberen. Een aanvraag wijzigen stuurt geen nieuwe e-mail.

## [statuses | interventionrequests.statuses] Interventiestatussen
De statussen die een aanvraag kan hebben, bv. "Nieuw", "Onderweg" of "Afgewerkt".

1. Klik op **Nieuwe status** en geef een naam.
2. Duid aan of de status **Open** of **Gesloten** is: een aanvraag met een gesloten status telt als afgesloten en verdwijnt uit **Toon Open Interventies**.
3. Kies een **kleur**: zo herken je de status meteen in de lijst.

![Interventiestatussen](statuses.png)

## [teamkar | interventionrequests.teamkar] TeamKar
Wie lid is van TeamKar: de personen die je bij een aanvraag als **Team kar** kan kiezen.

1. Vink bij een gebruiker **Lid van TeamKar** aan of uit.
2. De wijziging is meteen bewaard.

![TeamKar](teamkar.png)

## [mailing-list | interventionrequests.mailinglist] Mailinglijst
Iedereen die hier actief staat, krijgt een e-mail met de leveringsbon als PDF zodra er een nieuwe aanvraag binnenkomt, via welk kanaal ook.

1. Klik op **Nieuw adres** en vul het e-mailadres (en eventueel een naam) in.
2. Wil iemand tijdelijk geen mails? Klik op **Wijzigen** en zet het adres op **Gepauzeerd**.
3. **Verwijderen** haalt een adres definitief van de lijst.

![Mailinglijst](mailing-list.png)

## [roles | interventionrequests.roles] Rollen
Een rol bepaalt wat iemand in Interventies mag doen, per scherm: **Bekijken**, **Aanmaken**, **Wijzigen** en **Verwijderen**.

1. Klik op **Nieuwe rol** en geef een naam (bv. "TeamKar", "Beheerder").
2. Klik bij de rol op **Rechten** en vink per scherm aan wat de rol mag.
3. Sla de rechten op.

Wat de rechten betekenen:
- **Interventieaanvragen**: aanvragen aanmaken, wijzigen (status, uitvoerder, Team kar) en verwijderen. Dezelfde rechten gelden in de gsm-app.
- **Interventiestatussen**, **TeamKar** en **Mailinglijst**: de lijsten op die schermen beheren.

![Rollen](roles.png)

## [users | interventionrequests.users] Gebruikers
Iedereen met toegang tot Interventies en zijn huidige rol.

1. Kies bij een gebruiker de **rol** in de keuzelijst. De wijziging is meteen bewaard.
2. Klik op **Nieuwe gebruiker** om iemand toegang te geven. Bestaat het e-mailadres nog niet, dan wordt er een account gemaakt met de naam en het tijdelijke wachtwoord dat je invult.

![Gebruikers](users.png)

> Zonder rol ziet iemand enkel het KPI overzicht, ook al heeft hij toegang tot de module.

## [phone] Interventies op de gsm
In de gsm-app (zie de module **Mobile App** voor de installatie) heeft Interventies twee tabbladen:

- **Akties**: de aanvragen, standaard enkel de open aanvragen (**Open** / **Alle**), met een zoekveld. Tik op een aanvraag om ze te bekijken of te wijzigen, of maak een nieuwe aan.
- **KPI overzicht**: dezelfde cijfers als op de pc.

> Op de gsm kan je niets verwijderen en geen PDF's maken. Wie een aanvraag mag bekijken maar niet wijzigen, ziet ze enkel.
