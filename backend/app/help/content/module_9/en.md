# MasterData

MasterData holds the base data every other module uses: the years, festivals, teams and their team leads, and the products with their type, warehouse, category and limit.

## [start] How MasterData works
The other modules read this data; they don't keep their own copy:

- **Years** and **Festivals**: the season Altsien Select, KarTracker and StockMaster work in.
- **Teams**: the associations, with their location, delivery method, tasks and Altsien core members. Which teams a core member sees in Altsien Select is decided here.
- **Products**: everything in the warehouse and in the carts. Their properties decide how StockMaster handles them (blocking, limit, minimum stock, ...).
- The small lists (Type, Warehouses, Categories, Limits, Team Location, Delivery Method, Team Tasks) are the choices in the Products and Teams forms.

> On every screen, **Help for this screen** at the top right opens the part of this guide about that screen. The full guide is at the bottom of the menu on the left.

## [overview] Masterdata Overview
The start screen of MasterData: the products at a glance.

- **Tiles** at the top: the number of products and years, and how many products are blocked, consumable or logistics products, and how many have an incomplete classification (no type, warehouse or category).
- **Products per type**, **per category** and **per warehouse**.

![The Masterdata Overview](overview.png)

## [season | masterdata.season] Years
The years (seasons) the app works in.

1. Click **New year** and give the name, e.g. "2027".
2. Turn **Period Open** on as long as the Altsien core members may still change their choices for that year. Turn it off to freeze the choices.

![Years](season.png)

> In StockMaster, booking in a closed year needs an explicit right.

## [festival | masterdata.festival] Festivals
The festivals per year, with their start and end date.

1. Click **New festival**: name, start date, end date and year.
2. Set a festival that doesn't take place to not **Active**: it can then no longer be chosen in the Team Wizard.

![Festivals](festival.png)

## [teams | masterdata.teams] Teams
The associations that work with a cart: name, location, delivery method, description and whether they're active.

1. Click **New team** and fill in at least the name.
2. Choose the team's **Tasks** and **Core members**: the Altsien core members who see and fill in this team in Altsien Select.
3. A team that no longer takes part is set to not **Active**.

![Teams](teams.png)

> Only users marked as Altsien core member appear in the Core members list.

## [team-responsibles | masterdata.team-responsibles] Team leads
The responsible people per team and per year, with their email, phone number and comments. They don't have to be RWCrew users.

1. Optionally choose a team and a year to narrow the list.
2. Click **New team lead**: team, year, name, email and phone number are required.

![Team leads](team-responsibles.png)

> This is the same list as step 3 of the Team Wizard in Altsien Select: what the core members enter there shows up here, and the other way round.

## [team-location | masterdata.team-location] Team Location
The locations you can choose for a team. Click **New team location** to add one, or **Change** to rename one.

![Team Location](team-location.png)

## [delivery-method | masterdata.delivery-method] Delivery Method
The delivery methods you can choose for a team. Click **New delivery method** to add one.

![Delivery Method](delivery-method.png)

## [team-tasks | masterdata.team-tasks] Team Tasks
The tasks a team can have. Click **New team task** to add one; on the team you tick which tasks it has.

![Team Tasks](team-tasks.png)

## [products | masterdata.products] Products
All products with their picture, type, warehouse, category and properties.

1. Click **New product**. Name, type, warehouse, category and limit are required. Also fill in the **Warehouse location**: that's where the free stock lies in StockMaster.
2. Optionally add a **Picture**: you see it in StockMaster and Altsien Select.
3. Choose the properties:
   - **Consumable**: used up. Only for these the **minimum stock** counts (orange banner in StockMaster).
   - **Blocked**: can no longer be booked in or delivered.
   - **Is logistics product**: always gets what's asked in Load cart.
   - **Tag Managed (RFID)**: the product carries an RFID tag (TagScan).
   - **StockMaster: after 'Cart returns'**: does it go back into the cart or to the free stock?
4. Choose the **Limit** (Ongelimiteerd, Automatisch, Percentage, Toegewezen aantal) and, for Percentage, the **Limit value**. **Maximum initial stock** caps what a cart gets as long as it isn't delivered in KarTracker. Together they decide what StockMaster may deliver in Load cart.
5. **Cost (€)** is optional.

![Products](products.png)

> A product with stock or bookings in StockMaster can't be deleted: block it instead.

## [product-types | masterdata.product-types] Type
The product types, a choice on the product form. Click **New type** to add one.

![Type](product-types.png)

## [warehouses | masterdata.warehouses] Warehouses
The warehouses where products are kept. Click **New warehouse** to add one.

![Warehouses](warehouses.png)

## [product-categories | masterdata.product-categories] Categories
The product categories, to group and filter products. Click **New category** to add one.

![Categories](product-categories.png)

## [product-limits | masterdata.product-limits] Limits
The limits you choose on a product. StockMaster recognises them by their **name**: Ongelimiteerd, Automatisch, Percentage and Toegewezen aantal.

![Limits](product-limits.png)

> Don't rename these limits: StockMaster knows them by name, and a different name no longer counts in the Load cart calculation.

## [data-upload | masterdata.dataupload] Data Upload/Download
Import and export all MasterData tables in bulk with Excel, one tile per table.

1. Click a tile, e.g. **Products**.
2. **Download template** gives an empty Excel file with the right columns.
3. Fill it in, choose it under **Excel file** and click **Upload**. The result shows per row: **Created**, **Updated**, **Already there** or **Error** (with the reason).
4. The button at the bottom exports the full list.

![Data Upload/Download](data-upload.png)

- **Changing in bulk**: export the list, edit it and upload it again. A row with an **id** (the export's first column) changes that record; a row without an id creates a new one. Columns left out of your file stay unchanged.
- Lists (type, warehouse, team, ...) are given by **name**; upper or lower case doesn't matter.
- Yes/no columns accept yes/no, ja/nee, true/false and 1/0.
- **Tasks per team**, **Core members per team** and **Festivals per team** only add links: a link that already exists gets "Already there". Core members are given by their account's email address. Removing is done on the screen itself.

> Uploading needs the **Create** right on this screen; downloading templates and exports needs **View**.

## [roles | masterdata.roles] Roles
A role decides what someone may do in MasterData, per screen: **View**, **Create**, **Edit** and **Delete**.

1. Click **New role** and give it a name (e.g. "Warehouse", "Admin").
2. Click **Permissions** on the role and tick per screen what the role may do.
3. Save the permissions.

![Roles](roles.png)

## [users | masterdata.users] Users
Everyone with access to MasterData and their current role.

1. Choose the **role** of a user in the drop-down list. The change is saved right away.
2. Click **New user** to give someone access. If the email address doesn't exist yet, an account is created with the name and temporary password you fill in.

![Users](users.png)
