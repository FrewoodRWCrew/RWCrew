# Altsien Select

In Altsien Select the Altsien core members make, per team and per year, the choices the organisation builds its instructions on: at which festivals the team is, where things are delivered, who the team leads are, which products each cart gets and which special requests there are.

## [start] How Altsien Select works
1. The MasterData admin links you as **Altsien core member** to your team(s). You only see those teams here.
2. In the **Team Wizard** you go through the steps per team and complete each step.
3. The **Team sheet** shows all choices of a team on one screen, also as PDF.
4. The organisation follows up the special requests in **Request follow-up** and answers them.

### The year
At the top you choose the **year**. As long as that year's period is open (MasterData > Years), you can change your choices. After that everything can only be viewed, unless your role explicitly allows it.

### Where your choices end up
Altsien Select itself only keeps the progress and the special requests. The rest goes straight into the other modules: the festivals and team leads into **MasterData**, the delivery locations into KarTracker (**Plan a kar**) and the products into StockMaster's **Cart needs**.

> On every screen, **Help for this screen** at the top right opens the part of this guide about that screen. The full guide is at the bottom of the menu on the left.

## [overview] KPI overview
How far are the teams with their Team Wizard in the chosen year?

- **Tiles** at the top: the number of teams, how many completed their wizard, how many are still busy and how many special requests are still open.
- **Progress per step**: how many teams already completed each step.
- **Special requests per status**.

![The KPI overview](overview.png)

## [wizard | altsienselect.wizard] Team Wizard
The list of your teams with their progress ("3/6 steps") and their open requests. Click **Start** or **Continue** to open a team's wizard.

![The Team Wizard](wizard.png)

In the wizard you see the steps at the top. Fill in a step and click **Complete step & continue**. A completed step shows when and by whom it was completed; **Reopen** lets you change it again. **Previous** and **Next** browse without completing.

### 1. Festivals
Tick the year's festivals the team is active at. Removing a festival also removes its delivery location.

### 2. Delivery locations
Choose per chosen festival the **delivery location** where the goods are delivered. This ends up in KarTracker (Plan a kar).

### 3. Team leads
Add at least one team lead with name, email and phone number (**Add team lead**). These people don't have to be RWCrew users.

### 4. Products
Choose one of the team's **carts** and put together its list: which products and how many. This is the same list StockMaster loads the cart with (Cart needs). Per cart you can take over last year's list.

### 5. Special requests
Does the team need something special? Click **Add request** and describe it as clearly as possible. The organisation sets a status and can answer; you see that answer with the request. No requests? Just complete the step.

### 6. Walkie-talkies
This step follows later.

> The Delivery locations, Team leads and Special requests steps have **Copy from last year** at the top: click **Show**, tick last year's lines you want to take over and click **Copy selected**. Nothing is ever deleted, and the step isn't completed automatically.

## [ploegfiche | altsienselect.ploegfiche] Team sheet
All choices of one team on one screen: team info (location, delivery method, core members), the wizard's progress, the carts, festivals and delivery locations, team leads, products per cart and special requests.

1. Choose the year and the team.
2. Click **PDF** to print the team sheet.
3. Something to change? **Change in the wizard** opens that team's wizard.

![The Team sheet](ploegfiche.png)

## [requests | altsienselect.requests] Request follow-up
All the teams' special requests in the chosen year, for the organisation.

1. Optionally filter on **status**.
2. Click **Follow up** on a request, choose the status and write an **Organisation's answer**.
3. Click **Save**. The team sees the answer in its wizard and on the team sheet.

![Request follow-up](requests.png)

## [statuses | altsienselect.statuses] Request statuses
The statuses a special request can have, with a colour and whether they're **open** or **closed**.

1. Click **New status**, give a name, a colour and whether it's open or closed.
2. Set the **order**: the status with the lowest order is the start status of every new request.

![Request statuses](statuses.png)

## [roles | altsienselect.roles] Roles
A role decides what someone may do in Altsien Select, per screen: **View**, **Create**, **Edit** and **Delete**.

1. Click **New role** and give it a name (e.g. "Core member", "Organisation").
2. Click **Permissions** on the role and tick per screen what the role may do.
3. Save the permissions.

What the permissions mean:
- **Ploeg Wizard**: View to open the wizard, Edit to make choices.
- **All teams (organisation)** isn't a screen but a switch: View shows **all** teams instead of only your own teams; Edit allows changes after the year's period was closed.
- **Request follow-up** and **Request statuses**: for the organisation.

![Roles](roles.png)

## [users | altsienselect.users] Users
Everyone with access to Altsien Select and their current role.

1. Choose the **role** of a user in the drop-down list. The change is saved right away.
2. Click **New user** to give someone access. If the email address doesn't exist yet, an account is created with the name and temporary password you fill in.

![Users](users.png)

> Which teams a core member sees isn't chosen here but in MasterData > Teams (core members), or in bulk through MasterData > Data Upload/Download.
