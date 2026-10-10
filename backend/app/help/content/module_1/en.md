# TagScan

TagScan processes the CSV files of the RFID scanners. Every file arrives in the **Unreaded Tags** folder, is scanned and logged, and every tag read (EPC) is linked to the register in **TagManagement**. Actions in the file, such as **Assignment**, then create tags for a product.

## [start] How TagScan works
A scanned file always follows the same path:

1. A scanner (e.g. a Raspberry Pi) sends its CSV file over HTTPS to TagScan. It lands in the **Unreaded Tags** folder.
2. **Scan** logs the file in **Tag Headerdata**, reads every line into **Tag Linedata** and moves the file to the **Read Tags** folder. This also happens automatically in the background (see Settings).
3. Every line is linked to the tag with the same EPC in **TagManagement** and to the scanner from the **Scanners** register.
4. Lines with an action TagScan knows (today **Assignment**) wait to be processed. You process them through the blue bar at the top.

### Two kinds of status
- **Match status** (on a line): was the EPC found in TagManagement? Converted, No match or Cancelled.
- **Processing** (on a line and a file): was the action carried out? **New** (orange), **Loaded** (green) or **Cancelled** (red). The table rows get that colour.

### The blue "waiting to be processed" bar
When scanned lines with an action are waiting, a **blue bar** with their number shows at the top of every TagScan screen. Click **Review** to process them (see "Processing waiting actions").

> On every screen, **Help for this screen** at the top right opens the part of this guide about that screen. The full guide is at the bottom of the menu on the left.

## [overview] TagScan Overview
TagScan's start screen: the tags at a glance.

- **Tiles** at the top: total tags, unread CSVs (still in Unreaded Tags), assigned and unassigned tags, lost or damaged tags and the number of tags registered this month.
- **Tags per status**: how all tags are spread.
- **Registrations over time**: new tags per week, the last 12 weeks.
- **Top products**: the 5 products with the most tags.

![The TagScan overview](overview.png)

> Many **unread CSVs** means nothing was scanned yet. Check under Settings whether the automatic scan is on, or click **Scan** in Tag Headerdata.

## [pending | tagscan.tag-linedata] Processing waiting actions
Scanned lines with an action (e.g. **Assignment**: create tags for a product) wait until someone processes them.

1. Click **Review** in the blue bar at the top. You see the waiting lines, grouped per file.
2. Choose the **product** for each file (required). Each file also shows what the scanner itself sent as product or comment.
3. Click **Process file** for one file, or **Process all** for every file.
4. The result shows per line what happened: **Created** (new tag), **Product assigned** (existing tag without a product), **Already assigned** or **Error**.

- A line you don't want to process is **cancelled** with a reason (required). It then gets the status Cancelled.
- A tag that already has a product is never changed.
- Processing needs the **Edit** right on Tag Linedata and **Create** on TagManagement (tags are created). Cancelling needs Edit on Tag Linedata.

## [files | tagscan.dashboard] CSV Source Files
The folders and files on the server as the scanners deliver them, with a preview of their contents.

1. Click a folder on the left, e.g. **Unreaded Tags** (still to scan) or **Read Tags** (already scanned).
2. Click a file to see its contents. For a large file only the first part is shown.
3. **Refresh** reloads the list.
4. Want to clean up files? Tick them and click **Delete**.

![CSV Source Files](files.png)

> Deleting removes the file from the server for good. A file that was already logged stays in Tag Headerdata. You need the **Delete** right on this screen.

## [header-data | tagscan.tag-headerdata] Tag Headerdata
Every scanned CSV file on one line: the file name, when it was logged, the number of lines, the scanner (name, type, location, technology), the mode, the action and the processing status.

1. Click **Scan** to process the new files in Unreaded Tags right away. The scan log shows per file: **Logged**, **Already logged** or **Error**.
2. Search with the filters under the column titles, e.g. on file name, scanner or processing status.
3. Click the PDF icon of a file for a **PDF summary** of the file and its lines.
4. A file read in by mistake? **Delete** removes the registration and all its lines in Tag Linedata. The CSV file itself stays.

![Tag Headerdata](header-data.png)

> Scanning needs the **Create** right on this screen, deleting the **Delete** right.

## [line-data | tagscan.tag-linedata] Tag Linedata
Every scanned CSV line, completed with the tag from TagManagement: EPC, RSSI, antenna, count, last seen, product, serial number, kar number, manufacturer, batch number, match status and processing.

1. Search with the filters under the column titles, e.g. on EPC, product, scanner or status.
2. Click **Group by Product** to see a subtotal per file and product.
3. Were TagManagement or the scanner register completed in the meantime? Click **Synchro**: every line is linked again to today's tags and scanners.
4. A line that is wrong can be **cancelled**.

![Tag Linedata](line-data.png)

> **No match** means the EPC isn't (yet) in TagManagement. Add the tag in TagManagement or through an Assignment, then click **Synchro**.

## [tag-management | tagscan.tag-management] TagManagement
The register of all RFID tags: EPC / UID, status, assigned product and serial number, kar number (the KarTracker kar the tag is mounted on), dates, last read and location, manufacturer, batch number and five note fields.

1. Click **New tag** to register a tag. Fill in at least the **EPC / UID**.
2. Click **Change** on a tag to change e.g. the product, the serial number, the kar number or the **status** (Active, Inactive, Lost, Damaged, Retired).
3. Search with the filters under the column titles, e.g. on status or product.
4. Tick tags and click **Delete** to delete several at once.

![TagManagement](tag-management.png)

> Registering or changing many tags at once? Use an Excel file in **Data Upload/Download**.

## [scanners | tagscan.scanners] Scanners
The register of the physical RFID scanners that make the CSV files: name, type, technology, location, description and three info fields.

1. Click **New scanner** and fill in at least the name, exactly as the scanner writes it in its CSV.
2. Click **Change** on a scanner to change its details.
3. Click **API key** to create a key for the device. Copy the key and the upload URL straight into the device's configuration.

![Scanners](scanners.png)

> The API key is shown only **once**. Creating a new key makes the previous one invalid right away, and a key only works on the environment (test or production) it was made on.

## [data-upload | tagscan.dataupload] Data Upload/Download
Import and export tags and scanners in bulk with Excel, one tile per table.

1. Click **Download template** for an empty Excel file with the right columns.
2. Fill it in and choose it under **Excel file**. Click **Upload**.
3. The result shows per row: **Created**, **Updated** or **Error** (with the reason).
4. **Download tags** or **Download scanners** exports the full list.

![Data Upload/Download](data-upload.png)

> An existing EPC / UID or scanner name is **updated**, not created twice. A scanner's API key is kept. Uploading needs the **Create** right on this screen.

## [roles | tagscan.roles] Roles
A role decides what someone may do in TagScan, per screen: **View**, **Create**, **Edit** and **Delete**.

1. Click **New role** and give it a name (e.g. "Scanner operator", "Administrator").
2. Click **Permissions** on the role and tick per screen what the role may do.
3. Save the permissions.

What the rights mean:
- **CSV Source Files**, Delete: delete files from the server.
- **Tag Headerdata**, Create: scan. Delete: remove a registration with its lines.
- **Tag Linedata**, Edit: Synchro, process waiting actions (together with Create on TagManagement) and cancel lines.
- **TagManagement** and **Scanners**: create, edit and delete in the register.
- **Data Upload/Download**, Create: upload Excel files.

![Roles](roles.png)

## [users | tagscan.users] Users
Everyone with access to TagScan and their current role.

1. Choose a user's **role** in the dropdown. The change is saved immediately.
2. Click **New user** to give someone access. If the e-mail address doesn't exist yet, an account is created with the name and temporary password you enter.

![Users](users.png)

> Without a role someone only sees the TagScan Overview, even with access to the module.

## [settings | tagscan.settings] Settings
How TagScan receives and scans the devices' CSV files.

- **Receive folder**: the folder on the server where files arrive, in the "Unreaded Tags" subfolder. Keep the default, unless the server's administrator asks otherwise.
- **Device upload URL**: the address a scanner sends its files to, together with its own API key (see Scanners). Click **Copy** and paste it into the device's configuration.
- **Automatic scan**: scans Unreaded Tags in the background, just like the Scan button. Switch it on and choose the **interval** in seconds (60 by default). You also see when the last automatic scan ran and what it found.

![Settings](settings.png)

> A change applies right away, without restarting the server.
