# Atelier

In Atelier the atelier team keeps track of work clothing during the festival days. Team members who work at a place with its own clothing (VIP, RW terrace, ...) get that clothing (T-shirts, hoodies, ...) at the start of their shift and hand it back after the shift. Atelier records what was handed out and returned, so everything stays traceable.

> This module is built in blocks. Ready now: the master data (articles and sizes), the reservations (persons and package per team per festival), the stock (receipt, washing, write-off, count, to order), the counter (pick up and return) and the wristband scans (webhook, settings and Test scan). Next comes following every piece of clothing by RFID (TagScan).

## [overview | atelier.kpi] KPI overview
Atelier's start page. The **Counter** block shows how many pieces were handed out today, how many pieces aren't back yet and how many persons still have clothing. The **Master data** block shows how many active articles and sizes there are and how many article sizes can be handed out. The **Reservations** block shows, per festival of the chosen **season**, the persons and pieces per day, the number of teams with a reservation and how many of those have no package yet. The **Forgotten?** column counts the teams that have a reservation at another festival of this season but nothing here yet (no persons, no note). Click the number for their names and a link to that festival's reservations. If a team really isn't coming, enter 0 persons with a note (e.g. "not coming"). The **Stock** block shows the pieces that are available, to be washed and handed out, and how many sizes are below their minimum stock.

![The KPI overview](overview.png)

## [desk | atelier.desk] Hand-out & return
The counter. Pick the **festival**, the **day** (today by default) and **this counter's scanner** at the top (remembered in this browser).

**Wristband scans**: when a worker scans their wristband at this counter, they appear at the top within seconds ("Scanned: …"). Then choose **Pick up** (name, wristband number, team and size are filled in) or **Return** (their pieces are ready). **Ignore** removes the scan. A scan arriving during a transaction waits until you're done. The email address is optional. **Every transaction starts with the choice between two big buttons: Pick up or Return** (or keys 1 / 2). After booking (or **Cancel**) you're back at that choice for the next person.

**Pick up**
1. Enter the **first name** and **family name**: together they decide who the person is. When the person is known, email, wristband number and team are filled in and you see what they still hold.
2. Optionally enter the **email address** (several people may share one) and the **wristband number** (the number on this festival's wristband; unique within the festival — every festival has new wristbands). The wristband number is required when that is switched on in **Settings**.
3. Pick the **team** (only teams with a package at this festival).
4. For each package article pick the **size** (1 piece per article); the number in brackets is how many are available. Every article is **optional**: click the chosen size again to skip the article. An article with only one size in stock (e.g. OneSize) is pre-selected. At least one article is needed; next to the button it says what's still missing.

An article the person hasn't returned yet can't be handed out again. An orange box shows what the person still holds, with the button **Return first** that opens the return for that person right away. All other articles can be picked up — several times a day too.
5. Click **Hand out** (or Enter).

When the team already has as many or more people served today than reserved, the counter turns orange — handing out is still possible.

**Return**
1. Search the person by name, email address or wristband number (only people holding clothing).
2. Every piece is ticked; untick what didn't come back (that stays outstanding). When something is unticked, the counter first asks for confirmation with the list of what stays with the person.
3. Click **Take back**: the pieces go to **To wash**.

With the Edit right you can **cancel** a hand-out of which nothing came back yet (the pieces go back to available).

![The counter: Pick up or Return](desk.png)

## [open | atelier.open] Outstanding
All clothing that was picked up but hasn't come back: person, email address (click to mail), team, day, what they still hold and when it was picked up. Filter by festival, day and team. If something never comes back, write it off via **Stock > Write-off** (reason "Not returned").

![Outstanding](open.png)

## [reservations | atelier.reservations] Reservations
Everything per festival on one page: per team **how many people** need clothing and **what each person gets** (the package, e.g. 2 T-shirts and 1 hoodie). A team works **every festival day** with that number of people and returns the clothing **every evening**, so every day needs *persons × package* again. The size isn't part of the package: it is picked at the counter.

1. Pick the **season** and the **festival** at the top. The table lists every active team.
2. Enter the number of **persons** per team, optionally with a **note**.
3. Click **Package** on a team to choose the articles (Add article, remove a line). The **quantity per person** is always **1**: at the counter every person gets one piece per article.
4. Changed lines turn yellow. Click **Save** to store everything at once. Every team shows who changed it last and when.

The package only applies to this festival. A team with persons but no package gets a warning. A reservation without persons, note and package disappears.

**Copy from last year**: when the same festival existed last season (same name, the year doesn't count), last year's reservations are shown above the table. Tick the teams and click **Copy**. The package is topped up (nothing is ever removed, inactive articles are skipped) and the persons are only taken over while this year's number is still 0.

Reservations and package lines can also be loaded in bulk on **Data Upload/Download**.

![Reservations](reservations.png)

## [preparation | atelier.preparation] Preparation
What the store prepares **every festival day** (every day is the same, since the clothing comes back every evening).

- **Total from the store per day**: the pieces per article, with the **estimated sizes**. The estimate comes from the size split (%) you enter on the article (Articles, % per size). An article without a complete size split is split equally. Next to each size the available stock: **red** when the atelier doesn't own enough pieces, **orange** when it does but not all are washed or back yet.
- **Per team**: each team's package for its number of persons. The size is picked at the counter.

**Print picklist**: pick the day and click the button. With no teams ticked, every team is on it; tick teams to print only those (and the total for them only). The picklist has a box per team to tick off once its bundle is ready.

![Preparation](preparation.png)

## [stock | atelier.stock] Stock
Per article and size how many pieces are **available**, **to wash** (returned after a shift) and **handed out**, with the total and the minimum stock. A size below its minimum stock turns orange; every Atelier page then also shows an orange notice. **Only below minimum stock** shows just those sizes.

![Stock](stock.png)

## [receipt | atelier.receipt] Receipt
Book new clothing: pick the articles with **Add article**, enter the quantity per size and optionally a **reference** (e.g. the delivery note). Click **Book in**: the pieces are available right away. Only active articles and sizes can be received.

![Receipt](receipt.png)

## [wash | atelier.wash] Washing
The screen shows every article with pieces **to wash**. Enter per size how many pieces were washed (or click **All**) and click **Book washed**: they're available again.

![Washing](wash.png)

## [writeoff | atelier.writeoff] Write-off
Clothing that leaves the stock for good. First choose whether you write off from **Available** or **To wash**, then the articles and quantities, and the **reason**: damaged, lost, not returned or other (then a note is required).

![Write-off](write-off.png)

## [count | atelier.count] Stock count
Pick the articles you counted. The booked quantities are filled in per size; change what you counted (available and to wash). Only the **differences** are booked, as one count. Pieces handed out aren't counted here.

![Stock count](count.png)

## [bookings | atelier.bookings] Bookings
All stock bookings, newest first, with a filter on type. View the lines, print the **booking note** (PDF) or click **Undo** (only with the Edit right): a counter-booking is made and the original stays visible as undone. That only works while the pieces are still there (undo the later booking first).

![Bookings](bookings.png)

## [orderneeds | atelier.orderneeds] To order
Per size what is short for the chosen **season**: the highest day need over the festivals (persons × package, estimated per size with the article's size split) minus everything the atelier owns (available + to wash + handed out). **Print** gives the order list as a PDF.

![To order](order-needs.png)

## [articles | atelier.articles] Articles
The catalogue of work clothing, e.g. "Crew T-shirt black" or "VIP hoodie". An article is always all its sizes together.

1. Click **New article**.
2. Enter the **code** (unique, e.g. TS-CREW-BL) and the **name**. Colour, description and purchase price per piece are optional.
3. Under **Sizes**, tick the sizes the article comes in, grouped by Women, Men and Unisex. Per size you can enter a **minimum stock** and its **share (%)** of the size split (100% together); Preparation uses it to estimate how many pieces per size to prepare.
4. Optionally pick a **picture** (PNG, JPEG or WebP, max. 5 MB).
5. Click **Save**.

An article that is in a reservation's package can't be deleted: set it to **not active** instead. An inactive article can no longer be added to a package.

![Articles](articles.png)

## [sizes | atelier.sizes] Sizes
The list of sizes you can tick on an article. A size is a **name** (XS, S, M, ..., OneSize) plus a **fit**: Women, Men or Unisex. So "M · Women" and "M · Men" are two separate sizes. Use **OneSize · Unisex** for articles that only come in one size.

1. Click **New size**, enter the name, pick the fit and an **order** (lower = earlier in the list).
2. The filter at the top shows only the sizes of one fit.

A size used by an article can't be deleted: set it to not active instead.

![Sizes](sizes.png)


## [dataupload | atelier.dataupload] Data Upload/Download
One tile per table to download a **template**, **upload** a filled-in file and **export** the current data.

- **Sizes** and **Articles**: a row with an existing **id** (the export's first column) changes that record, a row without an id creates a new one.
- **Article sizes** (article code + size + fit), **Reservations** (season + festival + team) and **Package lines** (season + festival + team + article code): a known combination is updated, a new one added.
- The fit may be written as women/men/unisex or Dames/Heren/Unisex.

After uploading you see per row whether it was created, updated, unchanged or an error, with the reason.

![Data Upload/Download](data-upload.png)

## [settings | atelier.settings] Settings
- **Wristband required to pick up**: when on, nothing can be picked up at the counter without a wristband number (scanned or typed). Every festival has new wristbands: a number is unique within one festival.
- **Webhook**: the address the wristband company sends its scans to, and whether the token is set on this server. Without a token every message is refused (Test scan still works).
- **Scanners**: every scanner of the wristband company appears automatically with its first message. Give it a name (e.g. "Counter 1"); at the counter you pick which scanner stands there.
- **Received messages**: every message that came in — also refused ones (wrong token, unreadable JSON) and messages not meant for the counter — with status, scanner, person, wristband and team. The eye icon shows the message as received. "no team with this name" means the team name doesn't match a MasterData team; the counter then picks the team.

![Settings](settings.png)

## [scantest | atelier.scantest] Test scan
To test everything before the real connection with the wristband company (from May 2027). The message goes through **the same processing** as the webhook, without token, and is marked **Test**.
- **Form**: pick an existing scanner or type a new device id, fill in first name, family name, wristband number, team (pick or type a name to test a team that doesn't exist), profile and optionally email and size. On the right you see the message that is sent.
- **JSON file**: drop a .json file in the box, choose a file or paste the message — it is sent as is (handy to replay a real example from the company).
Click **Send**: under the button you see what happened to the message, and a valid scan appears right away at the counter that picked that scanner.

![Test scan](scan-test.png)

## [roles | atelier.roles] Roles
A role decides what someone may do in Atelier, per screen: **View**, **Create**, **Edit** and **Delete**.

1. Click **New role** and enter a name (e.g. "Atelier lead", "Staff").
2. Click **Permissions** on the role and tick per screen what the role may do.
3. Save the permissions.

![Roles](roles.png)

## [users | atelier.users] Users
Everyone with access to Atelier and their current role.

1. Pick a user's **role** in the drop-down. The change is saved right away.
2. Click **New user** to give someone access. If the email address doesn't exist yet, an account is created with the name and temporary password you enter.

![Users](users.png)
