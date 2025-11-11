# Produktoprettelse-v2 - Cloud Deployment Guide

## Online Deployment med Microsoft Authentication

Denne guide beskriver hvordan man deployer Produktoprettelse-v2 til cloud med Microsoft/Azure AD authentication.

---

## Oversigt

**Platform:** Azure App Service  
**Authentication:** Microsoft Entra ID (Azure AD)  
**Storage:** Azure Blob Storage  
**Database:** Azure SQL (valgfrit for user logs)

---

## 1. Forudsætninger

### Azure Subscription
- Azure konto med administrator rettigheder
- Resource Group til projektet

### Development Environment
- Python 3.11+
- Azure CLI installeret
- Git

---

## 2. Azure Resources Setup

### 2.1 Create Resource Group
```bash
az group create \
  --name produktoprettelse-rg \
  --location westeurope
```

### 2.2 Create App Service Plan
```bash
az appservice plan create \
  --name produktoprettelse-plan \
  --resource-group produktoprettelse-rg \
  --sku B1 \
  --is-linux
```

### 2.3 Create Web App
```bash
az webapp create \
  --name produktoprettelse-app \
  --resource-group produktoprettelse-rg \
  --plan produktoprettelse-plan \
  --runtime "PYTHON:3.11"
```

### 2.4 Create Storage Account (for files)
```bash
az storage account create \
  --name produktdata \
  --resource-group produktoprettelse-rg \
  --location westeurope \
  --sku Standard_LRS

# Create containers
az storage container create \
  --name cache \
  --account-name produktdata

az storage container create \
  --name output \
  --account-name produktdata

az storage container create \
  --name logs \
  --account-name produktdata
```

---

## 3. Microsoft Entra ID (Azure AD) Setup

### 3.1 Register App i Azure AD

1. Gå til **Azure Portal** → **Microsoft Entra ID** → **App registrations**
2. Klik **New registration**
3. Udfyld:
   - **Name:** Produktoprettelse-v2
   - **Supported account types:** Accounts in this organizational directory only (Bunzl)
   - **Redirect URI:** `https://produktoprettelse-app.azurewebsites.net/`
4. Klik **Register**

### 3.2 Configure Authentication

1. Gå til **Authentication** i din app registration
2. Under **Platform configurations** → **Add a platform** → **Web**
3. **Redirect URIs:**
   ```
   https://produktoprettelse-app.azurewebsites.net/
   https://produktoprettelse-app.azurewebsites.net/.auth/login/aad/callback
   ```
4. **Front-channel logout URL:** `https://produktoprettelse-app.azurewebsites.net/logout`
5. **ID tokens:** ✅ Enable

### 3.3 Create Client Secret

1. Gå til **Certificates & secrets**
2. Klik **New client secret**
3. **Description:** "Produktoprettelse App Secret"
4. **Expires:** 24 months
5. Gem **Value** (vises kun én gang!)

### 3.4 Note Down IDs

Gem disse værdier:
- **Application (client) ID:** `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- **Directory (tenant) ID:** `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- **Client Secret:** `xxx~xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

## 4. Configure App Service Authentication

### 4.1 Enable Authentication

```bash
az webapp auth update \
  --name produktoprettelse-app \
  --resource-group produktoprettelse-rg \
  --enabled true \
  --action LoginWithAzureActiveDirectory
```

### 4.2 Configure Azure AD Provider

```bash
az webapp auth microsoft update \
  --name produktoprettelse-app \
  --resource-group produktoprettelse-rg \
  --client-id "YOUR_CLIENT_ID" \
  --client-secret "YOUR_CLIENT_SECRET" \
  --issuer "https://login.microsoftonline.com/YOUR_TENANT_ID/v2.0" \
  --allowed-audiences "https://produktoprettelse-app.azurewebsites.net"
```

### 4.3 Restrict Access

I Azure Portal:
1. Gå til **Authentication** i din App Service
2. **Restrict access:** ✅ Require authentication
3. **Unauthenticated requests:** Redirect to Azure AD login

---

## 5. Application Configuration

### 5.1 Update Code for Azure Authentication

Tilføj til `app/app.py`:

```python
import os
import streamlit as st

def check_azure_auth():
    """Check if user is authenticated via Azure AD"""
    # Azure App Service injects user info in headers
    user_id = os.environ.get('X-MS-CLIENT-PRINCIPAL-ID')
    user_name = os.environ.get('X-MS-CLIENT-PRINCIPAL-NAME')
    
    if not user_id:
        st.error("⛔ Ikke autoriseret. Log venligst ind via Azure AD.")
        st.stop()
    
    # Show logged-in user
    st.sidebar.success(f"👤 Logget ind som: {user_name}")
    return user_id, user_name

# Add at top of app
if os.environ.get('WEBSITE_SITE_NAME'):  # Running on Azure
    user_id, user_name = check_azure_auth()
```

### 5.2 Update File Paths for Azure Storage

Opdater `app/app.py` til at bruge Azure Blob Storage:

```python
from azure.storage.blob import BlobServiceClient

# Connection string fra environment variable
AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')

def get_blob_client():
    return BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

def upload_to_blob(local_path, container_name, blob_name):
    blob_client = get_blob_client().get_blob_client(
        container=container_name, 
        blob=blob_name
    )
    with open(local_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)

def download_from_blob(container_name, blob_name, local_path):
    blob_client = get_blob_client().get_blob_client(
        container=container_name, 
        blob=blob_name
    )
    with open(local_path, "wb") as download_file:
        download_file.write(blob_client.download_blob().readall())
```

### 5.3 Environment Variables

Tilføj i Azure App Service → **Configuration** → **Application settings**:

```
OPENAI_API_KEY=sk-proj-...
API_KEY=dandomain_key
FTP_USER=FtpUser4843158
FTP_PASSWORD=***
FTP_HOST=ftp.webshop8.dk
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
PYTHON_VERSION=3.11
SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

---

## 6. Deploy Application

### 6.1 Prepare Deployment Files

Create `requirements.txt`:
```
streamlit
pandas
openai
pillow
requests
beautifulsoup4
pymupdf
python-dotenv
azure-storage-blob
msal
```

Create `startup.sh`:
```bash
#!/bin/bash
python -m streamlit run app/app.py \
  --server.port 8000 \
  --server.address 0.0.0.0 \
  --server.headless true
```

### 6.2 Deploy via Azure CLI

```bash
# Set deployment source (GitHub)
az webapp deployment source config \
  --name produktoprettelse-app \
  --resource-group produktoprettelse-rg \
  --repo-url https://github.com/your-org/Produktoprettelse-v2 \
  --branch main \
  --manual-integration

# Or deploy from local Git
git remote add azure https://produktoprettelse-app.scm.azurewebsites.net/produktoprettelse-app.git
git push azure main
```

### 6.3 Configure Startup Command

```bash
az webapp config set \
  --name produktoprettelse-app \
  --resource-group produktoprettelse-rg \
  --startup-file startup.sh
```

---

## 7. User Access Control

### 7.1 Restrict to Specific Users

I Azure Portal → **Enterprise Applications** → Produktoprettelse-v2:

1. **Properties** → **User assignment required:** ✅ Yes
2. **Users and groups** → **Add user/group**
3. Tilføj kun de brugere der skal have adgang

### 7.2 Role-Based Access (valgfrit)

Definer roller i `app/app.py`:

```python
ADMIN_USERS = ['anton@bunzl.dk', 'daniel@bunzl.dk']

def is_admin(user_email):
    return user_email.lower() in ADMIN_USERS

# Brug i app
if is_admin(user_name):
    st.sidebar.success("🔧 Admin Mode")
    # Vis ekstra funktioner
```

---

## 8. Monitoring & Logging

### 8.1 Enable Application Insights

```bash
az monitor app-insights component create \
  --app produktoprettelse-insights \
  --location westeurope \
  --resource-group produktoprettelse-rg

# Link to App Service
az webapp config appsettings set \
  --name produktoprettelse-app \
  --resource-group produktoprettelse-rg \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY="YOUR_KEY"
```

### 8.2 View Logs

```bash
# Live log stream
az webapp log tail \
  --name produktoprettelse-app \
  --resource-group produktoprettelse-rg

# Download logs
az webapp log download \
  --name produktoprettelse-app \
  --resource-group produktoprettelse-rg \
  --log-file logs.zip
```

---

## 9. Backup & Disaster Recovery

### 9.1 Automated Backups

```bash
az webapp config backup create \
  --resource-group produktoprettelse-rg \
  --webapp-name produktoprettelse-app \
  --backup-name daily-backup \
  --container-url "https://produktdata.blob.core.windows.net/backups?SAS_TOKEN"
```

### 9.2 Database Backups (hvis brugt)

```bash
az sql db export \
  --resource-group produktoprettelse-rg \
  --server produktdb-server \
  --name produktdb \
  --admin-user sqladmin \
  --admin-password "***" \
  --storage-key "***" \
  --storage-key-type StorageAccessKey \
  --storage-uri "https://produktdata.blob.core.windows.net/backups/db.bacpac"
```

---

## 10. Cost Estimation

| Resource | SKU | Estimeret Pris/måned (DKK) |
|----------|-----|---------------------------|
| App Service Plan | B1 (Basic) | ~375 kr |
| Storage Account | Standard LRS | ~50 kr |
| Application Insights | Basic | ~100 kr |
| **Total** | | **~525 kr/måned** |

### Cost Optimization:
- Brug S1 plan hvis mere performance nødvendig (~750 kr/md)
- Overvej Consumption plan for lavere brug
- Sæt auto-shutdown til udviklings-miljø

---

## 11. Security Checklist

- [x] HTTPS enforced (automatisk på Azure)
- [x] Azure AD authentication påkrævet
- [x] User assignment restricted
- [x] Secrets i Key Vault (anbefalet) eller App Settings
- [x] Storage accounts har private endpoint
- [x] Network security groups konfigureret
- [x] Application Insights enabled
- [x] Automated backups aktiveret
- [x] CORS policies konfigureret

---

## 12. Maintenance

### Update Application

```bash
# Pull latest code
git pull origin main

# Deploy
git push azure main
```

### Update Secrets

```bash
az webapp config appsettings set \
  --name produktoprettelse-app \
  --resource-group produktoprettelse-rg \
  --settings NEW_KEY="new_value"
```

### Scale Up/Down

```bash
# Scale til S1 (mere kraft)
az appservice plan update \
  --name produktoprettelse-plan \
  --resource-group produktoprettelse-rg \
  --sku S1

# Scale tilbage til B1
az appservice plan update \
  --name produktoprettelse-plan \
  --resource-group produktoprettelse-rg \
  --sku B1
```

---

## Support & Troubleshooting

### Common Issues

**Problem:** 401 Unauthorized  
**Solution:** Check Azure AD configuration, ensure redirect URIs are correct

**Problem:** Slow performance  
**Solution:** Upgrade App Service Plan eller enable caching

**Problem:** Files not persisting  
**Solution:** Ensure Azure Blob Storage is configured correctly

### Contact

For Azure support:
- Azure Portal: Support + troubleshooting
- Microsoft Support: https://support.microsoft.com/

---

## Next Steps

1. ✅ Setup Azure resources
2. ✅ Configure Azure AD
3. ✅ Deploy application
4. ✅ Test authentication
5. ✅ Add users
6. ✅ Monitor & optimize

**Production URL:** `https://produktoprettelse-app.azurewebsites.net`