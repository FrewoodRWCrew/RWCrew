# Atelier

In Atelier the atelier team keeps track of work clothing during the festival days. Team members who work at a place with its own clothing (VIP, RW terrace, ...) get that clothing (T-shirts, hoodies, ...) at the start of their shift and hand it back after the shift. Atelier records what was handed out and returned, so everything stays traceable.

> This module is built in blocks. Ready now: the master data (articles and sizes), the reservations (persons and package per team per festival), the stock (receipt, washing, write-off, count, to order), the counter (pick up and return) and the wristband scans (at the counter and through Test scan; the scans themselves are in the Scans module). Next comes following every piece of clothing by RFID (Scans).

## [overview | atelier.kpi] KPI overview
Atelier's start page. The **Counter** block shows how many pieces were handed out today, how many pieces aren't back yet and how many persons still have clothing. The **Master data** block shows how many active articles and sizes there are and how many article sizes can be handed out. The **Reservations** block shows, per festival of the chosen **season**, the persons and pieces per day, the number of teams with a reservation and how many of those have no package yet. The **Forgotten?** column counts the teams that have a reservation at another festival of this season but nothing here yet (no persons, no note). Click the number for their names and a link to that festival's reservations. If a team really isn't coming, enter 0 persons with a note (e.g. "not coming"). The **Stock** block shows the pieces that are available, to be washed and handed out, and how many sizes are below their minimum stock. The **Washed** block shows for the same season how many pieces were washed: the total, and per festival per day. A wash counts for the festival running that day; what was washed in the days after a festival is listed under **No festival** of that season. Undone washes don't count.

![The KPI overview](overview.png)

## [desk | atelier.desk] Hand-out & return
The counter. Pick the **festival**, the **day** (today by default) and **this counter's scanner** at the top (remembered in this browser).

**Wristband scans**: when a worker scans their wristband at this counter, they appear at the top within seconds ("Scanned: …"). Then choose **Pick up** (name, wristband number, team and size are filled in) or **Return** (their pieces are ready). **Ignore** removes the scan. A scan arriving during a transaction waits until you're done. The email address is optional. **Every transaction starts with the choice between two big buttons: Pick up or Return** (or keys 1 / 2). After booking (or **Cancel**) you're back at that choice for the next person.

**Pick up**
1. Enter the **first name** and **family name**: together they decide who the person is. When the person is known, email, wristband number and team are filled in and you see what they still hold.
2. Optionally enter the **email address** (several people may share one) and the **wristband number** (the number on this festival's wristband; unique within the festival — every festival has new wristbands). The wristband number is required when that is switched on in **Settings**. A filled-in email address (known person or scan) is only partly shown for privacy (GDPR), e.g. fr***@gm***.com; **Change** empties the box so you can type a new address. On Return the email address is masked the same way. Once a team is chosen, a **contact icon** appears on the right (level with "Known: …"): click it for the team's **team leads** in this season (name, phone, email, comments), as set in MasterData > Teams > Team leads. Scanners not working? Click the **camera icon** next to the wristband number and hold the wristband's QR code in front of the PC's camera: the number is filled in.
3. Pick the **team** (only teams with a package at this festival).
4. For each package article pick the **size** (1 piece per article); the number in brackets is how many are available. Every article is **optional**: click the chosen size again to skip the article. An article with only one size in stock (e.g. OneSize) is pre-selected. At least one article is needed; next to the button it says what's still missing.

If a known person already has a **different wristband number** at this festival, the desk asks whether this is the same person with a new wristband. If it's someone else with the same name, choose Cancel and extend the name (e.g. with a second first name): two people with exactly the same name are one person to the desk.

An article the person hasn't returned yet can't be handed out again. An orange box shows what the person still holds, with the button **Return first** that opens the return for that person right away. All other articles can be picked up — several times a day too.
5. Click **Hand out** (or Enter).

**The reservation is a limit.** The counter shows how many people of the team at this festival **hold clothing right now**, against the reserved number of persons. Once that number is reached, the desk refuses a **new** person (someone who already holds something may still pick up another article); someone who returned everything frees a place. With the **Edit** right on Hand-out & return the desk asks whether to **hand out anyway** beyond the reservation; without that right, raise the reservation first on **Reservations**.

**Return**
1. Search the person by name, email address or wristband number (only people holding clothing).
2. Every piece is ticked; untick what didn't come back (that stays outstanding). When something is unticked, the counter first asks for confirmation with the list of what stays with the person.
3. If a piece has a problem (damaged, very dirty, ...), pick a **return status** per piece in the dropdown. It's only a remark: the piece still goes to **To wash**, and it shows up on **Return issues**.
4. Click **Take back**: the pieces go to **To wash**.

**Email**: when the person has an email address, they get a **Hand-out** mail after every pick-up and one **Return** mail after every return (also when the pieces come from several hand-outs). The texts are set on **Settings > Emails**.

With the Edit right you can **cancel** a hand-out of which nothing came back yet (the pieces go back to available).

**On the Raspberry Pi (RWCrew Pi)**: with the RFID reader the same happens without typing. Pick the season, festival, day and the counter's wristband scanner once (remembered). Every wristband scan shows as a card with **Pick up**, **Return** and **Ignore**; the email address is shown, as on the website, but only partly (e.g. fr***@gm***.com). For Pick up you put the pieces on the reader: every piece with a tag (see **Link RFID tags**) shows at once, green when it will be booked, orange with the reason when it can't (not in the package, still held, second piece of the same article, out with someone else, no stock). For Return the pieces read are ticked (also pieces that went out without a tag, per article); you can still tick or untick by hand and pick a return status. **Confirm** books it, with the same rules, mails and rights as on the website. Without a connection to RWCrew nothing is booked (red bar).

![The counter: Pick up or Return](desk.png)

## [open | atelier.open] Outstanding
All clothing that was picked up but hasn't come back, **grouped per team and then per person** (with wristband number; the email address isn't shown, for privacy (GDPR)), with every piece below it: festival, day, article, size and when it was picked up. Pick the festival and optionally the day at the top, or **All festivals** for a full overview of the season (no day choice then; type in the **Festival** column's filter to still show one festival). Every column has a **filter field** above it: type part of a name, team, article, … to narrow the list; the totals follow the filter. If something never comes back, click **Write off** next to the person (with the Create right on the Write-off screen), tick the pieces and confirm: they leave the stock for good with the reason "Not returned", are no longer outstanding, and the person can pick that article up again. The person gets no mail about this, and this write-off can't be undone. **Stock > Write-off** is only for pieces in the store (available or to wash).

With the counter's rights, every person has a **Return** button: it opens the same screen as Return at the counter, for this person, with everything they still hold (also outside the chosen day). The person gets the normal Return mail.

The **Excel** button downloads what's on screen, including the filters you use (without email addresses).

![Outstanding](open.png)

## [returnissues | atelier.returnissues] Return issues
![Return issues](return-issues.png)

All clothing that came back with a **return status**, newest first: status, article, size, festival, team, person, wristband, day, when it was returned and who booked it. Pick the festival and optionally the day at the top, or **All festivals** for the whole season (then filter per festival in the **Festival** column); every column has a text filter. This screen is read-only: a piece that can't be used any more is booked out via **Write-off**. The **Excel** button downloads what's on screen, including the filters you use.

## [tags | atelier.tags] Link RFID tags (Raspberry Pi)
This screen only exists in the **Raspberry Pi app (RWCrew Pi)** with the RFID reader, not on the website. It gives new clothing pieces their RFID tag: from then on the tag says which **article in which size** the piece is.

1. Pick the **article** (searchable), then the **size** (big buttons; each shows how many pieces of that size already carry a tag). An article with one size (OneSize) is picked at once.
2. Put the pieces of that size on the reader. Every tag read gets a line: **New — will be linked** (green), **Already this size** (green, nothing changes), **Already …** another piece (orange) or refused (red: the tag belongs to a StockMaster product or kar, or the piece is out with someone).
3. Every tag that can be linked has a **tick** (on by default): tap a line to **untick** a tag that was read by accident.
4. Tap **Link**: only the ticked tags are linked. When some ticked tags are already another piece, the Pi asks first whether to change them anyway.

The View right shows the screen, Create allows linking. The stock itself doesn't change: it stays counted per size; the tag only says which physical piece is with whom.

## [massreturn | atelier.massreturn] Mass return (Raspberry Pi)
This screen only exists in the **Raspberry Pi app (RWCrew Pi)** with the RFID reader. During the day a team collects its dirty clothing in a **box** and brings it to the atelier: Mass return takes the whole box back in one go, without putting every person through the desk.

1. Put the box on the reader. The **big number** shows how many tags (pieces) were read in the box.
2. On the right, the pieces are listed **per person** who has them out (article and size, with the tag number).
3. A **red line** (unknown tag, a StockMaster product's or kar's tag, an inactive tag, or a piece that isn't handed out) blocks confirming: take that piece out of the box and tap **Read again**.
4. Tap **Confirm** (or press the Pi's confirm button): every piece is returned per person (to the wash), and every person with an email address gets the usual **return mail**.

The View right shows the tile, Create allows confirming. **Tag history** shows these returns with the **Pi** label.

## [taghistory | atelier.taghistory] Tag history
Everything one piece of clothing went through, by its **RFID tag (EPC)**. Type or paste the tag number and click **Search**; from **Outstanding** and **Return issues** you can also open it by clicking an EPC.

At the top is the tag as **Scans > Tag management** knows it now: which piece (article and size), its status and when, by which scanner and where it was last read. Below it every **hand-out and return** with that EPC, newest first: when handed out and returned (or still out, written off, cancelled), person, team, festival, day, piece, who booked it and any return status. A label shows **where** it was booked: **Pi** (RWCrew Pi with the RFID reader) or **Website** (the desk on the website).

The tag number is **stored with** every hand-out and return made with the Pi: even when the tag is later deleted in Tag management or linked to another piece, the history stays right. This screen is read-only.

## [reservations | atelier.reservations] Reservations
Everything per festival on one page: per team **how many people** need clothing and **what each person gets** (the package, e.g. 2 T-shirts and 1 hoodie). A team works **every festival day** with that number of people and returns the clothing **every evening**, so every day needs *persons × package* again. The size isn't part of the package: it is picked at the counter.

1. Pick the **season** and the **festival** at the top. The table lists every active team.
2. Enter the number of **persons** per team, optionally with a **note**.
3. Click **Package** on a team to choose the articles (Add article, remove a line). The **quantity per person** is always **1**: at the counter every person gets one piece per article.
4. Changed lines turn yellow. Click **Save** to store everything at once. Every team shows who changed it last and when.

**Festivals filled in**: per team how many of the festivals it picked in **Altsien Select** already have persons (e.g. *3 / 5*). Green = all filled in, orange = not yet; hover the number to see per festival what's missing. A team that picked nothing yet shows "no selection". A team that picked other festivals but not this one shows "not picked" next to its name.

The toggle above the table shows **All teams** or **Only with a package** (the teams with a package at this festival). Every column has a **filter field** above it. A changed team that isn't saved yet always stays visible; the totals always count every team.

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
Per article and size how many pieces are **available**, **to wash** (returned after a shift) and **handed out**, with the total and the minimum stock. **With RFID tag** counts the pieces with an active tag in Scans > Tag management (linked with the Raspberry Pi; lost or damaged tags don't count), **Without tag** the pieces that still need one (orange). A size below its minimum stock turns orange; every Atelier page then also shows an orange notice. **Only below minimum stock** shows just those sizes.

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

Bookings from last year's lists (loaded by the super admin with the mass test) keep their original date and time; no mail was sent for those hand-outs and returns.

A desk **Hand-out** or **Return** also shows its **pieces** under **View lines** (and on the booking note): article, size, person and the **RFID tag number (EPC)** when the piece was read with the Raspberry Pi; click the EPC for the **Tag history**. A **Pi** label in the list shows the booking was made on RWCrew Pi.

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


## [returnstatuses | atelier.returnstatuses] Return statuses
The list of what can be wrong with a returned piece, such as "Damaged" or "Very dirty". The counter picks this per piece on **Return**.

1. Click **New return status** and enter the name.
2. A status already used can't be deleted: set it to not active instead. It then leaves the dropdown, but stays visible on the pieces that have it.

In bulk this works through **Data Upload/Download**.

![Return statuses](return-statuses.png)

## [dataupload | atelier.dataupload] Data Upload/Download
One tile per table to download a **template**, **upload** a filled-in file and **export** the current data.

- **Return statuses**: a row is looked up by **id**, otherwise by name; a status found is changed, otherwise a new one is added. Nothing is ever removed.
- **Sizes** and **Articles**: a row is looked up by **id** (the export's first column), otherwise by name + fit (sizes) or code (articles); a record that is found is changed, otherwise a new one is added. So an export from another environment (e.g. localhost to test) can be uploaded too.
- **Article sizes** (article code + size + fit), **Reservations** (season + festival + team) and **Package lines** (season + festival + team + article code): a known combination is updated, a new one added.
- The fit may be written as women/men/unisex or Dames/Heren/Unisex.

After uploading you see per row whether it was created, updated, unchanged or an error, with the reason.

![Data Upload/Download](data-upload.png)

## [settings | atelier.settings] Settings
- **Wristband required to pick up**: when on, nothing can be picked up at the counter without a wristband number (scanned or typed). Every festival has new wristbands: a number is unique within one festival.

The wristband scans themselves (the webhook, the scanners with their names and every received message) are in the **Scans** module. A scan only appears at the counter if the team has a reservation with a package at a festival of the season, or if the team name wasn't recognised: the counter then picks the team.

## [scantest | atelier.scantest] Test scan
To test everything before the real connection with the wristband company (from May 2027). The message goes through **the same processing** as the webhook, without token, and is marked **Test**.
- **Form**: pick an existing scanner or type a new device id, fill in first name, family name, wristband number, team (pick or type a name to test a team that doesn't exist), profile and optionally email and size. On the right you see the message that is sent.
- **JSON file**: drop a .json file in the box, choose a file or paste the message — it is sent as is (handy to replay a real example from the company).
Click **Send**: under the button you see what happened to the message, and a valid scan appears right away at the counter that picked that scanner, if the team has a reservation.

![Test scan](scan-test.png)

## [mailtemplates | atelier.mailtemplates] Emails
The mails a person gets after a transaction at the counter, to the email address entered at the counter (without an email address nothing is sent):
- **Hand-out**: after every pick-up;
- **Return**: after every return (one mail per transaction).

Per mail you set the **subject** and the **text**, and **Send** switches it on or off. Click a field such as **{voornaam}** or **{stuks}** to insert it at the cursor; when sending it is replaced by the transaction's data. **{stuks}** = the pieces of this transaction, **{openstaand}** = what the person still holds afterwards. An unknown field can't be saved.

On the right you see a **preview** with example data. **Send test to me** mails the text as it is now (also unsaved) to your own email address. Saving and testing need the Edit right.

![Emails](mails.png)

## [roles | atelier.roles] Roles
A role decides what someone may do in Atelier, per screen: **View**, **Create**, **Edit** and **Delete**.

1. Click **New role** and enter a name (e.g. "Atelier lead", "Staff").
2. Click **Permissions** on the role and tick per screen what the role may do.
3. Save the permissions.

The **Write off** button on Outstanding follows the Create right on the **Write-off** screen. Someone who only works the desk has enough with the desk screens: the festivals are loaded along with them.

![Roles](roles.png)

## [users | atelier.users] Users
Everyone with access to Atelier and their current role.

1. Pick a user's **role** in the drop-down. The change is saved right away.
2. Click **New user** to give someone access. If the email address doesn't exist yet, an account is created with the name and temporary password you enter.

![Users](users.png)
