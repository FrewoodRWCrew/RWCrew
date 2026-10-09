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
- **Karren per status** and **Karren per team**.
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
An overview of the whole fleet: per kar the kar number, status, team, transport type and location. For the year in the header, every active festival gets a column with the delivery location planned for the kar's team.

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
Choose per team the delivery location for every active festival of the year.

1. Pick an **open year** at the top in the header.
2. Choose a **team**.
3. Choose the **delivery location** per festival (or "No delivery location").
4. Click **Save**.

Below the table, the **delivery locations map** shows where the chosen locations are, optionally with the ground plan.

![Plan a kar](plan-kar.png)

> Altsien Kernleden fill in the same delivery locations through the Altsien Select wizard. What you save here they see there, and the other way round.

## [kar-management | kartracker.karmanagement] KarManagement
The fleet: every kar with its kar number, status, team, transport type, last location and when it was last logged.

1. Click **New kar** and fill in at least the **kar number**. Choose the status, team and transport type.
2. Click **Change** on a kar to change e.g. its team or status.
3. Search or filter with the fields under the column titles.
4. **Delete** removes a kar from the fleet for good.

![KarManagement](kar-management.png)

> A kar's team decides which delivery locations it goes to (Plan a kar) and what StockMaster plans for that kar. A kar that still holds stock can't be deleted.

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

## [afleverlocaties | kartracker.afleverlocaties] Delivery locations
The places karren are delivered to: name, description, zone, distribution point, coordinates, site position, Altsien Kernlid and whether the location is active.

1. Click **New delivery location** and fill in the details.
2. Click **Change** to change them, or **Delete**.
3. Set a location you no longer use to **Active: No** instead of deleting it.

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
3. The result shows per row what was created and what was skipped, with the reason.
4. **Download full database** exports everything of that topic.

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
