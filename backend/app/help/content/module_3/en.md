# Interventions

Interventions registers and follows up the associations' intervention requests: a team needs something for its cart or at its stand, and TeamKar goes over. Each request gets a number, a status and (optionally) someone who handles it.

## [start] How Interventions works
A request comes in in three ways, and then always follows the same path:

1. **Public form**: someone from the team scans the QR code on the cart and fills in the form, without logging in.
2. **Intervention requests**: someone from the organisation registers the request, e.g. after a phone call.
3. **Phone app**: in the phone app (Interventions > Actions) you create a request on the move.

Every new request automatically gets a **request number** and is emailed (with the delivery note as PDF) to everyone on the **Mailing list**. Then you assign someone to **handle** it and a **Team cart**, and set the **status** until the request is closed.

> On every screen, **Help for this screen** at the top right opens the part of this guide about that screen. The full guide is at the bottom of the menu on the left.

## [overview] KPI overview
The start screen of Interventions: the requests at a glance.

- **Tiles** at the top: the total number of requests, how many are still open and how many are closed.
- **Requests per status**: how many requests each status has now.
- **Requests per team**: how many requests each team submitted.

![The KPI overview](overview.png)

## [requests | interventionrequests.requests] Intervention requests
Every request with its number, when it was submitted, the team, the cart number, the question, the staff member and their mobile number, the preferred delivery, the delivery place and zone, the status, who handles it and the Team cart.

1. Click **New request** to register a request. Choose the team (or **Other** and type the name) and fill in at least the question.
2. Click **Change** on a request to choose the **status**, who **handles** it or the **Team cart**, or to change its details.
3. **Group by Preferred Delivery** lists the requests per delivery day (on by default). **Show All Interventions** also shows the closed requests; **Show Open Interventions** only shows what's still open.
4. Search with the filters under the column titles, e.g. on team, cart number or status.
5. The PDF icon downloads a request's **delivery note**.

![Intervention requests](requests.png)

> The link **Test: open the public request form** opens the form the teams see through the QR code, so you can try it out. Changing a request doesn't send a new email.

## [statuses | interventionrequests.statuses] Intervention statuses
The statuses a request can have, e.g. "New", "On the way" or "Done".

1. Click **New status** and give it a name.
2. Mark whether the status is **Open** or **Closed**: a request with a closed status counts as closed and disappears from **Show Open Interventions**.
3. Choose a **colour**: so you recognise the status straight away in the list.

![Intervention statuses](statuses.png)

## [teamkar | interventionrequests.teamkar] TeamKar
Who is a member of TeamKar: the people you can choose as **Team cart** on a request.

1. Tick or untick **TeamKar member** for a user.
2. The change is saved right away.

![TeamKar](teamkar.png)

## [mailing-list | interventionrequests.mailinglist] Mailing list
Everyone who is active here gets an email with the delivery note as PDF as soon as a new request comes in, through whichever channel.

1. Click **New address** and fill in the email address (and optionally a name).
2. Someone temporarily doesn't want mails? Click **Change** and set the address to **Paused**.
3. **Delete** removes an address from the list for good.

![Mailing list](mailing-list.png)

## [roles | interventionrequests.roles] Roles
A role decides what someone may do in Interventions, per screen: **View**, **Create**, **Edit** and **Delete**.

1. Click **New role** and give it a name (e.g. "TeamKar", "Admin").
2. Click **Permissions** on the role and tick per screen what the role may do.
3. Save the rights.

What the rights mean:
- **Intervention requests**: create, change (status, who handles it, Team cart) and delete requests. The same rights apply in the phone app.
- **Intervention statuses**, **TeamKar** and **Mailing list**: manage the lists on those screens.

![Roles](roles.png)

## [users | interventionrequests.users] Users
Everyone with access to Interventions and their current role.

1. Choose the **role** of a user in the drop-down list. The change is saved right away.
2. Click **New user** to give someone access. If the email address doesn't exist yet, an account is created with the name and temporary password you fill in.

![Users](users.png)

> Without a role, someone only sees the KPI overview, even with access to the module.

## [phone] Interventions on the phone
In the phone app (see the **Mobile App** module for installing it) Interventions has two tabs:

- **Actions**: the requests, by default only the open ones (**Open** / **All**), with a search field. Tap a request to view or change it, or create a new one.
- **KPI overview**: the same figures as on the PC.

> On the phone you can't delete anything or make PDFs. Someone who may view a request but not change it only sees it.
