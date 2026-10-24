# KarTracker

KarTracker manages the organisation's fleet of karren: every kar with its team and status, the places karren are delivered to and, per festival, where each kar has to go. Every move of a kar is logged, on the PC or with the phone, and shows on the map.

## [start] How KarTracker works
KarTracker follows a kar through a season:

1. **Master data**: the statuses, zones, distribution points, delivery locations and the karren themselves (with their team) are in the **Masterdata** group. Per festival you set the **delivery date** and **pick-up date**.
2. **Planning**: with **Plan a kar** you choose per team the delivery location for every festival of the year.
3. **Printing**: on **Kar Planning** you print a **kar sheet** per kar that travels with it: where and when it is delivered and picked up, with a QR code of the kar number.
4. **Tracking**: every move (new status + GPS location) is logged with **Manual kar movement**, or with **KarScan** on the phone by scanning the QR code on the kar sheet.
5. **Viewing**: **Kar Map** shows all karren, delivery locations and distribution points on the map, optionally with the ground plan of the site.

### The year
You choose the **year** at the top, in the header. The KPI, Kar Planning, Plan a kar and Delivery Dates follow that choice. The header only lists the years that are still open.

> On every screen, **Help for this screen** at the top right opens the part of this guide about that screen. The full guide is at the bottom of the menu on the left, under **Help**.

## [overview] KPI Overview
KarTracker's start screen: the fleet, recent moves and the progress of Plan a kar for the chosen year.

- **Tiles** at the top: total karren, karren with and without a team, moves in the last 7 days and how many delivery locations are already planned.
- **Karren per status** and **Karren per transport type**.
- **Moves per day**, the last 14 days.
- **Plan a kar per festival**: how many of the active teams already have a delivery location.

![The KPI Overview](overview.png)

> If Plan a kar says "choose a year", first pick a year at the top in the header.

## [movement | kartracker.actions] Manual kar movement
Log every move of a kar: which kar, its new status and where it stands now.

1. Choose the **kar** in the list, or click **Scan QR** and point the camera at the QR code at the top right of the kar sheet.
2. Choose the new **status**.
3. Click **Use my location** to take your device's GPS location, or click the map to choose or adjust the place. Optionally switch on the **Ground plan** layer to see the site.
4. Click **Save movement**. The kar gets its new status and location.

![Manual kar movement](movement.png)

The **logged movements** are listed below. A wrong movement can be **deleted**: the kar's current status and location then stay as they are.

> Camera and GPS only work over a secure connection (https). On site, **KarScan** on the phone is the easiest (see "KarTracker on the phone").

## [kar-planning | kartracker.karplanning] Kar Planning
An overview of the whole fleet: per kar the kar number, status, team, transport type and location. For the year in the header, every active festival gets a column with the delivery location planned for the kar's team. If the team unchecked a festival in Altsien Select, an empty cell reads **Not active** and counts as planned.

1. Choose the **year** at the top.
2. Search or filter with the fields under the column titles.
3. Tick the karren you want a kar sheet for (or **Select all**).
4. Click **Print**. You get a PDF with one **kar sheet** per kar.

![Kar Planning](kar-planning.png)

The kar sheet shows the kar number, the team and per festival where and when the kar is delivered and picked up. At the top right is a QR code with the kar number (for KarScan), lower down a QR code to the form to request an intervention for that team.

> Kar Planning is view-only. Change karren in **KarManagement** and delivery locations in **Plan a kar**.

## [kar-map | kartracker.karmap] Kar Map
A map with the **karren**, **delivery locations** and **distribution points** that have a known location.

1. Switch the layers **Karren**, **Delivery locations** and **Distribution points** on or off.
2. Switch on the **Ground plan** layer to lay the site plan over the map, and choose its **opacity**.
3. Search the list on name, kar number or team and click **Show on map** to go there.
4. Click a point for its details: kar number, status and team, or name, zone and description.

![Kar Map](kar-map.png)

> Something without coordinates is in the list ("No location") but not on the map. Fill in the latitude and longitude on that item's own screen.

## [plan-kar | kartracker.plankar] Plan a kar
Choose per team the delivery location for every festival of the year.

The screen opens on an **overview of every kar** (of active teams): per kar you see how many of its team's festivals already have a delivery location (e.g. "2/3 festivals", green once everything is filled in). Delivery locations belong to the team, so all kars of the same team show the same figure. Only the festivals the team picked in Altsien Select count; if it picked none yet, every active festival counts.

1. Pick an **open year** at the top in the header.
2. Search a kar (kar number or team) and click **Plan**.
3. Choose the **delivery location** per festival (or "No delivery location").
4. Click **Save**, then **Back to overview**.

Below the table, the **delivery locations map** shows where the chosen locations are, optionally with the ground plan.

![Plan a kar](plan-kar.png)

> Altsien Kernleden fill in the same delivery locations through the Altsien Select wizard. What you save here they see there, and the other way round.

## [leveringsvolgorde | kartracker.leveringsvolgorde] Delivery order
Put the delivery locations in the order in which they are served across the ground, so karren are loaded and delivered in the right order.

On the left is the **delivery tour**, numbered 1, 2, 3, … in delivery order. On the right are the **active delivery locations not yet in the tour** (by name; each line shows the description with the name and zone below it, plus a search box).

1. Click the **left arrow** next to a location (or drag it to the left) to add it to the tour. **Add all shown** adds everything the search on the right shows.
2. Drag the lines on the left into the right order.
3. Take a location out of the tour with the **right arrow** (or drag it back to the right).
4. Click **Save**. Every location on the left gets its position as **Terreinpositie** (1, 2, 3, …); locations on the right get none.

Next to every line is its **saved terreinpositie**, so you see what changes before saving: in the tour (left) "was 3" (orange when Save changes it) or "new" (had no position yet), on the right "was 3 → cleared" (Save clears it). At the top you see how many locations change.

**Map** (top right) opens the ground plan with the tour as it is on screen now: every location shows its new number and, in brackets, the saved one (e.g. "5 (was 3)"). A dashed line follows the tour from 1 to the end, so an illogical order stands out. Hover a location to see its name.

> Nothing changes until you save: **Undo changes** brings back the last saved order. Inactive delivery locations are not on this screen and keep their terreinpositie.

## [initial-delivery | kartracker.initieleleverplanning] Initial delivery planning
The **Planning analyses** group holds analyses of what has to be organised before, during or after the festival. **Initial delivery planning** shows which karren have to be delivered at the start, and where, for the year in the header.

A kar goes to the delivery location planned in **Plan a kar** for its team at the **team's first festival** (the earliest festival the team picked in Altsien Select, or the year's first festival while it picked none). Karren without a team, or whose team hasn't planned a location for that festival yet, are not listed.

- At the top: the **total** number of karren and the number **per distribution point**.
- The list is grouped first per **distribution point** (purple header line with its number of karren). Distribution points follow the order of their first location in the delivery tour.
- Within it, per delivery location a grey header line with its **terreinpositie** (#1, #2, …), name and description, zone and number of karren. Locations follow the **Delivery order**; those without a position ("no position") come last.
- Below it the karren (by kar number) with team, transport type, status, the festival they're delivered for and the delivery date from **Delivery Dates**.

**Filtering**: a filter row sits under the column headings. Pick a status in the **Status** dropdown, or type part of a text in the other columns (the filter under **Position** searches the location's position, name, description and zone). Locations and distribution points without a matching kar disappear and the counts follow the filter. **Clear filters** resets everything. Select all, the group boxes and Shift-click only touch the karren shown; karren already ticked stay ticked (and are printed), even when a filter hides them.

**Printing the delivery planning** for the drivers:

1. Tick the karren. **Shift-click** ticks (or unticks) the whole range between your previous click and this one; the box on a distribution point or location line does all its karren at once, the box in the header everything.
2. Optionally tick **Add map**.
3. Click **Print delivery planning**. You get a landscape PDF with, per distribution point (**Pick up at**), the delivery locations in tour order, their karren and an empty **Delivered** box to tick off.

With **Add map** a **Delivery route** page is added: the ground plan with the route from 1 to the end (dashed line), the delivery locations as numbered badges, locations without a position as grey dots and the distribution points as black squares. The map zooms in on the printed locations. The legend on the right lists the tour's stops (position, description and zone). Locations outside the ground plan or without coordinates are listed under the legend.

> This screen changes nothing. Change the order on **Delivery order** and the locations on **Plan a kar**.

## [kar-moves | kartracker.karverplaatsingen] Moves between festivals
**Moves between festivals** shows which karren have to be moved on the ground between two festivals, for the year in the header. That is needed when a team has a different delivery location in **Plan a kar** at the next festival than at the previous one.

Choose **From festival** and **To festival** at the top (the year's active festivals, in date order; the screen opens on the first two). A kar is listed when:

- its team takes part in **both** festivals (the festivals the team picked in Altsien Select, or every festival while it picked none);
- a delivery location is planned for the team at **both** festivals;
- and those two locations **differ**.

Karren that stay where they are, or for which not everything is planned yet, are not listed. Next to the dropdowns is the delivery date of the **To** festival (from **Delivery dates**).

- The list is grouped per **pick-up location** (where the karren stand at the From festival): a purple heading row with the **ground position** (#1, #2, …), name, zone and number of karren, in the order of the **Delivery order** (locations without a position last).
- Below it the karren (by kar number) with team, transport type, status and the **To** column: the delivery location the kar has to go to, with its position and zone.

**Filtering** works as on the Initial delivery planning: Status through the dropdown, the other columns with a piece of text (the filters under **From** and **To** search the position, name, description and zone). **Clear filters** resets everything.

**Printing the moves** for the drivers:

1. Tick the karren (Shift-click for a range, the box on a pick-up location for all its karren, the box in the heading for everything).
2. Optionally tick **Add map**.
3. Click **Print moves**. You get a landscape PDF with, per pick-up location (**Pick up at**), the karren, where they have to go and an empty **Moved** box to tick off.

With **Add map** a map page is added: the ground plan with the pick-up locations as purple dots, the locations that only receive karren as green dots, and an **arrow per move** with its number of karren. The dots carry the position in the delivery tour; a location without a position gets a letter (A, B, …). The legend on the right lists every location.

> This screen changes nothing. Change the locations in **Plan a kar** and the order in **Delivery order**.

## [special-tour-planning | kartracker.levertoerplanning] Special delivery tours planning
**Special delivery tours planning** shows which karren a special delivery tour (for example the laundry tour or the ice cube tour) passes by at a festival and where they stand, for the year in the header.

Pick the **Festival** at the top (the screen opens on the year's first festival) and one or more **Delivery tours**. A kar is listed when:

- its team is linked to at least one chosen tour on its team fiche (MasterData > Teams, field **Delivery tours**);
- the team takes part in the festival (the festivals it picked in Altsien Select, or every festival while it picked none);
- and a delivery location is planned for the team at that festival in **Plan a kar**.

A kar of a team on two chosen tours appears only once; the **Delivery tour** column then shows both.

The list shows the tour's **stops**: the delivery locations in the order of the **Delivery order** (locations without a position after them, by name), numbered **Stop 1, 2, 3, …**, each with the karren standing there (by kar number). Distribution points aren't shown: the tour passes by the karren, nothing is picked up. Filtering and ticking (Shift-click for a range) work like in the Initial delivery planning. **Print delivery planning** makes a PDF with the stops, the tours and the festival at the top and a **Delivered** box per kar; **Add map** adds a map page with every stop as a numbered badge and the route from stop 1 to the last. Put the delivery locations in the **Delivery order** for a sensible route.

> This screen changes nothing. Link teams to a tour on their team fiche and change their location in **Plan a kar**.

## [kar-management | kartracker.karmanagement] KarManagement
The fleet: every kar with its kar number, status, team, transport type, last location and when it was last logged.

1. Click **New kar** and fill in at least the **kar number**. Choose the status, team and transport type.
2. Click **Change** on a kar to change e.g. its team or status.
3. Search or filter with the fields under the column titles.
4. **Delete** removes a kar from the fleet for good.

![KarManagement](kar-management.png)

> A kar's team decides which delivery locations it goes to (Plan a kar) and what StockMaster plans for that kar. A kar that still holds stock can't be deleted. Clicking a kar number in TagScan opens that kar's form here straight away.

## [distributiepunten | kartracker.distributiepunten] Distribution points
The organisation's distribution points: name, coordinates, site position and the responsible Altsien Kernlid.

1. Click **New distribution point** and fill in the details.
2. Click **Change** to change them, or **Delete**.

![Distribution points](distributiepunten.png)

> With a latitude and longitude, the distribution point appears on **Kar Map**.

## [zones | kartracker.zones] Zone
The delivery zones, which you choose on a delivery location.

1. Click **New zone** and give it a name.
2. Click **Change** to rename it.
3. **Delete** only works when no delivery location uses the zone any more.

![Zone](zones.png)

## [special-tours | kartracker.specialelevertoeren] Special delivery tours
The special delivery tours that regularly pass by a number of teams, for example **Small laundry tour**, **Large laundry tour** or **Ice cubes**.

1. Click **New delivery tour**, give it a name and optionally a description (what the tour checks and when).
2. Click **Change** to change the name, description or status. A tour that isn't **Active** can no longer be picked on a team fiche.
3. **Delete** only works when no team is linked to the tour any more.

The **Teams** column shows which teams are on the tour. You link them on the team fiche in MasterData (field **Delivery tours**); the planning per festival is on **Special delivery tours planning**.

## [afleverlocaties | kartracker.afleverlocaties] Delivery locations
The places karren are delivered to: name, description, zone, distribution point, coordinates, site position, Altsien Kernlid and whether the location is active.

1. Click **New delivery location** and fill in the details.
2. Click **Change** to change them, or **Delete**.
3. Set a location you no longer use to **Active: No** instead of deleting it.

The **site position** (terreinpositie) is a number: the location's place in the delivery tour (1 = served first). The easiest way to set it is the **Delivery order** screen.

![Delivery locations](afleverlocaties.png)

> Only active delivery locations can be chosen in Plan a kar.

## [kar-statuses | kartracker.karstatuses] KarStatussen
The statuses a kar can have, e.g. "Available", "Delivered" or "Picked up". You choose them in KarManagement and on a kar movement.

1. Click **New status** and give it a name.
2. Click **Change** to rename it.
3. **Delete** only works when no kar has the status any more.

![KarStatussen](kar-statuses.png)

## [delivery-dates | kartracker.leverdata] Delivery Dates
Set the **delivery date** and **pick-up date** for every active festival of the year.

1. Pick an **open year** at the top in the header.
2. Fill in the delivery date and pick-up date per festival.
3. Click **Save**.

![Delivery Dates](delivery-dates.png)

> These dates are printed on the **kar sheet** from Kar Planning.

## [data-upload | kartracker.dataupload] Data Upload/Download
Import and export KarTracker's master data in bulk with Excel, one tile per topic: Karren, KarStatussen, Distribution points, Zones, Delivery locations and Delivery Dates.

1. Click a tile, then **Download template** for an empty Excel file with the right columns.
2. Fill it in, choose the file and click **Upload**.
3. The result shows per row what was created, updated or skipped, with the reason.
4. **Download full database** exports everything of that topic.

If a line already exists (same kar number, or same name ignoring case), it is **updated** instead of a new one being created. Only filled-in cells overwrite; an empty cell keeps the current value. So you can edit an export and upload it again. Clearing a value is done on the screen itself. For KarStatussen and Zones (only a name) an existing name stays unchanged.

![Data Upload/Download](data-upload.png)

> Uploading needs the **Create** right on this screen.

## [groundplan | kartracker.groundplan] Ground plan
The ground plans of the festival site, each with an image and the coordinates of its corners. They are shown together as a layer on Kar Map and on Manual kar movement.

1. Click **New ground plan** and give it a name.
2. Choose the plan's **image**.
3. Fill in the latitude and longitude of the **south-west corner** (bottom left) and the **north-east corner** (top right), so the plan lies right on the map.
4. Click **Save**. **Change** lets you adjust the corners or choose a new image.

![Ground plan](groundplan.png)

> Is the plan a bit off on Kar Map? Adjust the corners in small steps until roads and buildings line up.

## [roles | kartracker.roles] Roles
A role decides what someone may do in KarTracker, per screen: **View**, **Create**, **Edit** and **Delete**.

1. Click **New role** and give it a name (e.g. "Logistics", "Driver").
2. Click **Permissions** on the role and tick per screen what the role may do.
3. Save the permissions.

Some examples:
- **Manual kar movement**, Create: log movements (also with KarScan on the phone).
- **Plan a kar** and **Delivery Dates**, Edit: change the planning and the dates.
- **Data Upload/Download**, Create: upload Excel files.
- **Ground plan**: whoever may see Kar Map also sees the ground plan. Adding or changing ground plans needs rights on the Ground plan screen itself.

![Roles](roles.png)

## [users | kartracker.users] Users
Everyone with access to KarTracker and their current role.

1. Choose a user's **role** in the dropdown. The change is saved immediately.
2. Click **New user** to give someone access. If the e-mail address doesn't exist yet, an account is created with the name and temporary password you enter.

![Users](users.png)

> Without a role someone only sees the KPI Overview, even with access to the module.

## [phone] KarTracker on the phone
KarTracker also has a phone version, without installing anything from an app store. Open the **Mobile App** module on the start page for the address, the QR code and the steps to add it to your home screen.

- **KarScan**: scan the QR code on the kar sheet, choose the new status and save the movement with your phone's GPS location.
- **Kar Planning**: all karren with their planned delivery locations.
- **Kar Map**: the map with karren, delivery locations and distribution points.

You log in with the same account and have the same rights as on the PC.
