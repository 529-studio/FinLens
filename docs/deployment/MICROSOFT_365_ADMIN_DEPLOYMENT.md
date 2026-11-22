# Microsoft 365 Centralized Admin Deployment Guide for FinTrace Excel Add-in

This guide documents the formal enterprise deployment procedure for IT administrators rolling out the **FinTrace Excel Add-in** (`@fintrace/excel`) across enterprise finance, audit, and accounting departments via the **Microsoft 365 Admin Center**.

---

## 1. Architectural Overview & Security Model

The FinTrace Excel Add-in operates as a Microsoft Office Web Add-in powered by Office.js. It integrates directly into Excel (desktop for Windows/macOS and Excel for the Web) without installing local binary DLLs or COM add-ins, providing:
- **Zero Local Client Footprint**: Clean sandboxed execution inside WebView2 (Windows), WKWebView (macOS), or browser sandbox (Web).
- **Centralized Administrative Governance**: Controlled distribution via Microsoft 365 Centralized Deployment (`admin.microsoft.com`).
- **Encrypted Zero-Leak Transport**: All communications between the add-in and the FinTrace Core Engine / LAN Gateway use TLS 1.3 / HTTPS and WSS (WebSocket Secure).
- **Role-Based Tenant Access**: Can be deployed to specific Microsoft 365 Security Groups (e.g. `sg-finance-analysts`, `sg-audit-partners`).

---

## 2. Prerequisites & Compatibility Matrix

### Supported Client Platforms
| Platform | Supported Office Versions | Runtime Environment |
| :--- | :--- | :--- |
| **Windows** | Microsoft 365 Apps, Excel 2019/2021, Excel 2016 | Microsoft Edge WebView2 (Chromium) |
| **macOS** | Microsoft 365 for Mac, Excel 2019/2021 | Safari / WKWebView |
| **Web** | Excel for the Web (Edge, Chrome, Firefox, Safari) | Native Modern Web Browser |
| **iPad** | Excel for iPad | Safari WebView |

### Administrative Prerequisites
1. **Administrator Role**: Global Administrator or Centralized Deployment Administrator in Microsoft 365.
2. **User Mailboxes**: Target users must have active Exchange Online mailboxes and assigned Microsoft 365 Apps licenses.
3. **Firewall / Proxy Allowlist**:
   - `https://fintrace.529studio.site` (Production Add-in Host)
   - `https://*.529studio.site` (API & Support Endpoints)
   - Internal LAN Gateway (e.g. `https://fintrace-lan.corp.internal:8443` if using on-premise Docker Compose deployment).

---

## 3. Step-by-Step Centralized Deployment Procedure

### Step 1: Obtain the Production Manifest
The production manifest is located in the repository at:
```
apps/excel/manifest.appsource.xml
```
Verify the manifest integrity before deployment:
```bash
npm --prefix apps/excel run validate:manifest
```

### Step 2: Access Microsoft 365 Admin Center
1. Sign in to the [Microsoft 365 Admin Center](https://admin.microsoft.com) using administrator credentials.
2. In the left navigation menu, expand **Settings** and select **Integrated apps**.
3. At the top of the **Integrated apps** page, click **Upload custom apps**.

### Step 3: Upload the Manifest
1. In the **Upload custom app** wizard:
   - Select **App type**: `Office Add-in`.
   - Under **Upload manifest file**, select **Upload manifest file (.xml) from device** (or specify the secure HTTPS URL to `manifest.appsource.xml`).
2. Click **Choose file** and browse to `manifest.appsource.xml`.
3. The Admin Center will automatically validate the manifest schema, unique App ID (`529e0001-f187-4d7a-8f52-529529529002`), high-resolution icons, and permissions.
4. Click **Next** upon successful validation.

### Step 4: Configure User Assignment & Permissions
1. Under **Assign Users**:
   - **Specific users/groups (Recommended)**: Search for and select the designated Security Group (e.g., `Finance & Accounting Group`, `Internal Audit Department`).
   - **Entire organization**: Automatically deploys the add-in to all employees.
   - **Just me**: For staging and pre-rollout validation.
2. Select **Deployment Method**:
   - **Fixed (Default)**: The add-in is automatically installed and pinned in the users' Excel ribbon.
   - **Available**: Users can optionally install the add-in via the Office Store/Admin Managed tab.
3. Review and accept the requested permission: `ReadWriteDocument` (required to read active cell coordinates and write verified financial tables with footnote audit trails).
4. Click **Next**, review summary, and click **Finish deployment**.

---

## 4. End-User Verification & Launch

Once deployed, the add-in propagates automatically to users' Excel clients (typically within 1 to 4 hours depending on Azure AD replication):

1. **Excel Desktop (Windows / Mac)**:
   - Launch Microsoft Excel.
   - Go to the **Insert** tab on the ribbon.
   - Click **My Add-ins** (or **Get Add-ins**).
   - Select the **ADMIN MANAGED** tab.
   - Locate **FinTrace for Excel** and click **Add**.
   - The FinTrace taskpane opens docked on the right side.

2. **Excel for the Web**:
   - Open any workbook in Excel on the web (`excel.office.com`).
   - Navigate to **Home** or **Insert** -> **Office Add-ins** -> **Admin Managed**.
   - Click **FinTrace for Excel**.

---

## 5. Troubleshooting & Maintenance

### Clearing the Office Add-in Cache
If an updated manifest is not immediately visible on Windows workstations:
```powershell
# Close all Excel instances, then clear the WebView2 WEF cache:
Remove-Item -Path "$env:LOCALAPPDATA\Microsoft\Office\16.0\Wef\*" -Recurse -Force
```
On macOS:
```bash
# Clear Safari/WKWebView cache for Office:
rm -rf ~/Library/Containers/com.microsoft.Excel/Data/Documents/wef
```

### Network & CORS Verification
Ensure that the client machine can reach the FinTrace backend:
```bash
curl -I https://fintrace.529studio.site/taskpane.html
```
Expected response: HTTP 200 OK with `Content-Type: text/html`.

### Updating the Add-in
When upgrading versions (e.g. `1.0.0` to `1.1.0`):
1. In **Integrated apps**, click **FinTrace for Excel**.
2. Click **Update add-in** and upload the new manifest.
3. Centralized deployment updates all connected clients with zero client downtime.
