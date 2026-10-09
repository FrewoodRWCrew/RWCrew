# StockMaster

StockMaster keeps the warehouse stock: what lies **free** on its fixed location and what is **in the carts** while they stand in the warehouse. Every action in the warehouse (goods arrive, a cart is loaded, leaves or comes back) is one booking in your name.

## [start] How StockMaster works
StockMaster follows the flow of the warehouse. The **Actions** menu is in that order: Book in, Load cart, Book out, Cart leaves, Cart returns, Unload cart and Stock count.

### Free stock and cart stock
- **Free stock**: lies on the product's fixed location (warehouse + location from MasterData).
- **In carts**: loaded in a cart that stands in the warehouse. One product can be free and in several carts at the same time.
- **Total** = free + in carts. A cart that is **out** no longer counts: its contents were booked out on "Cart leaves".

### The season
At the top of most screens you choose the **season**. Cart needs, To order, the KPI and the carts follow that choice. In a closed season you can no longer book, unless your role explicitly allows it.

### Nothing gets lost
- Every booking is stored in **your name**, with date and time.
- A booking is never deleted. You fix a mistake with **Undo**: a counter-booking is added and everything goes back to where it came from.
- Stock can never go negative: you can't take more from a place than lies there.

### Below minimum
Consumables with a minimum stock that drop below it show an **orange bar** at the top of every StockMaster screen. Click **View** to see only those products.

> On every screen, the **Help for this screen** button at the top right opens the part of this guide about that screen. The full guide is at the bottom of the menu on the left.

## [booking] Booking in 4 steps
All actions (Book in, Load cart, Book out, ...) use the same **booking list**: a basket you put one or more products in and confirm in one go.

1. If needed, first choose the **cart** (type a few digits of the cart number).
2. Type a few letters of a **product**. You immediately see its location and how many are free.
3. Enter the **quantity** and press **Enter**: the line is added and you can search the next product.
4. Check the **Before → after** column and click **Confirm**.

> You can do everything with the keyboard: type a product, Enter, type the quantity, Enter. **Ctrl+Enter** confirms the booking.

After confirming, a message with **Undo** appears at the bottom, in case you made a mistake. Where a document belongs to it (e.g. the departure note) you can print it right away.

## [kpi | stockmaster.kpi] KPI
StockMaster's start screen: the stock and the carts at a glance, for the chosen season.

- **Tiles** at the top: total stock, free stock, in carts, carts in the warehouse or out, fully loaded carts, products below minimum and lines still to order. Click a tile to open the screen behind it.
- **Bookings per month**, per action (undone bookings are not counted).
- **Consumption per team**: what didn't come back with the carts.
- **Most consumed products**: not returned + booked out.

![The KPI screen](kpi.png)

## [stock | stockmaster.stock] Stock overview
Per product you see how many lie **free**, how many are **in carts** and the **total**, with the location and the warehouse.

1. Search on product name or location, or filter on warehouse and category.
2. Switch on **Only below minimum** to see only the consumables below their minimum.
3. Click a line to see the split **per cart**.
4. Use the buttons on the line to open **Book in**, **Book out** or **Load in cart...** right away, with the product already filled in.

![The stock overview](stock.png)

> An orange **Below minimum** label means there is less (free + in carts) than the minimum stock set in MasterData.

## [kars | stockmaster.kars] Carts
Every cart as a card: the cart number, the team, whether it is **in the warehouse** or **out** and how far it is loaded against its needs ("18 / 20"). Green is fully loaded, orange is not yet complete.

1. Type a cart number and press **Enter** to open the cart right away, or filter on team and on in warehouse/out.
2. Click a card for the cart's **detail page**.
3. On the detail page you see per product what is **needed**, what is **in the cart**, what is **missing** and what is **free to use**.
4. The buttons **Load**, **Unload**, **Leaves**, **Returns** and **Count** open the action for this cart. **Load list** prints the list to load the cart, sorted by location.

![The carts overview](kars.png)

> A cart that is out can't be loaded, unloaded or counted. Book **Cart returns** first.

## [book-in | stockmaster.stock] 1. Book in
Goods arrive (delivery, purchase) and go to the **free stock** on their fixed location.

1. Put the products with their quantity in the booking list (see "Booking in 4 steps").
2. Fill in the **delivery note or order number** as reference.
3. Click **Confirm: book in**.

![Book in](book-in.png)

> Blocked products can't be booked in. When a whole order arrives, start from **To order**: the quantities are then already filled in.

## [kar-load | stockmaster.kars] 2. Load cart
Fill a cart from the free stock (or from another cart).

1. Choose the cart.
2. What the cart still misses according to its **needs** is already in the list. Click **Fill in what's missing** to fill the list again.
3. Change the quantities if you load fewer or more, or add other products.
4. Choose under **From** whether it comes from the free stock or from another cart.
5. Click **Confirm: load cart**.

![Load cart](kar-load.png)

> If it says "free 3 of 5 needed" in orange, there isn't enough free stock. Check **To order** for what still has to come in.

## [book-out | stockmaster.stock] 3. Book out
Used, broken or lost goods leave the stock: from the free stock or from a cart standing in the warehouse.

1. Choose under **From** the free stock or a cart.
2. Put the products with their quantity in the booking list.
3. Choose a **reason** (required), e.g. used, broken or lost.
4. Click **Confirm: book out**.

![Book out](book-out.png)

## [kar-dispatch | stockmaster.kars] 4. Cart leaves
The cart leaves the warehouse for the team and the festival. Its **whole contents** go along and are booked out of the stock.

1. Choose the cart. You see what leaves with the cart.
2. Check the **team** and the **festival** (filled in from KarTracker).
3. Click **Confirm: cart leaves**.
4. Print the **departure note** and have it signed by the warehouse and the team.

![Cart leaves](kar-dispatch.png)

> If the cart still misses part of its needs, you get a warning. You can still let it leave.

## [kar-return | stockmaster.kars] 5. Cart returns
The cart is back from the festival. What left is already filled in: you only change what is different.

1. Choose the cart. The list shows per product what **left** and what is **back**.
2. Lower the quantity for products that didn't (fully) come back. You immediately see "2 not back → used".
3. Choose per line whether it goes **back in the cart** or to the **free stock** (by default according to the product's setting).
4. Click **Confirm: cart returns**.

![Cart returns](kar-return.png)

> What doesn't come back counts as the **team's consumption**. You see it on the KPI under "Consumption per team".

## [kar-unload | stockmaster.kars] 6. Unload cart
Take goods out of a cart in the warehouse back to the free stock, for example after the season.

1. Choose the cart.
2. Put the products that come out in the list, or click **Unload everything**.
3. Click **Confirm: unload cart**.

![Unload cart](kar-unload.png)

## [count | stockmaster.count] 7. Stock count
Count the stock in one place and book only the differences.

1. Choose **Free stock** (a warehouse, optionally from location ... to location ...) or **One cart**.
2. Click **Load list**. The list is ready with what is **expected**.
3. Optionally print the **count sheet** to count on paper.
4. Under **Counted**, only fill in what is different. Found something that isn't on the list? Search it to add it.
5. Check the reason ("Count difference" by default) and click **Book differences**.

![The count](count.png)

## [requirements | stockmaster.requirements] Cart needs
What each team needs per season, **per cart**. This fills "Load cart", shows how far a cart is loaded and decides what has to be ordered.

1. Choose the season and the team.
2. Click one of the team's carts.
3. Add products with their quantity and an optional comment, or change existing lines.
4. Click **Save**.

![Cart needs](requirements.png)

> Under **Copy from last season** you see last season's lines. Tick what you want to take over and click **Copy**. Don't forget to save afterwards.

## [order-needs | stockmaster.orderneeds] To order
The needs of all carts of the season against what is in stock (free + in carts). **To order** = needed minus in stock.

1. Choose the season and optionally filter on warehouse and category.
2. Keep **Only what has to be ordered** on to see only the shortages.
3. Print the **order list** or **export** to CSV for the supplier.
4. Has the order arrived? Tick the lines and click **Book in**: the quantities are already filled in, you only correct what was delivered differently.

![To order](order-needs.png)

## [bookings | stockmaster.bookings] Bookings
All bookings, newest first, with who made them and when.

1. Filter on date, action, product, cart or user.
2. Click a booking for all its lines: from where, to where, how many and the location at that time.
3. Print the **note** (for Cart leaves that is the departure note).
4. A mistake? Click **Undo** and optionally add a comment. The original booking stays visible as "Undone".

![The bookings](bookings.png)

> Undo isn't possible once the goods have been booked further (e.g. the cart has already left). Undo that later booking first.

## [reasons | stockmaster.reasons] Reasons
The reasons you choose when booking out or counting, such as "Used", "Broken" or "Count difference".

1. Click **New reason**, give a name and choose which booking it applies to (or all bookings).
2. Set the **order** in the dropdown.
3. Set a reason you no longer use to **Inactive**. Deleting is only possible if it was never used.

![The reasons](reasons.png)

## [roles | stockmaster.roles] Roles
A role decides what someone may do in StockMaster, per screen: **View**, **Create**, **Edit** and **Delete**.

1. Click **New role** and give it a name (e.g. "Warehouse", "Team").
2. Click **Permissions** on the role and tick per screen what the role may do.
3. Save the permissions.

What the rights mean:
- **Stock**, Create: Book in and Book out.
- **Carts**, Create: Load cart, Unload cart, Cart leaves and Cart returns.
- **Stock count**, Create: book a count.
- **Bookings**, Delete: undo a booking.
- **Book in a closed season** is not a screen but a switch: Edit allows booking after the season was closed.

![The roles](roles.png)

## [users | stockmaster.users] Users
Everyone with access to StockMaster and their current role.

1. Choose a user's **role** in the dropdown. The change is saved immediately.
2. Click **New user** to give someone access. If the e-mail address doesn't exist yet, an account is created with the name and temporary password you enter.

![The users](users.png)

> Without a role someone sees nothing in StockMaster, even with access to the module.
