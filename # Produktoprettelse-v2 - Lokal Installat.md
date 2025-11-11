# Produktoprettelse-v2 - Lokal Installation Guide

## Desktop Setup via OneDrive Synkronisering

Denne guide beskriver hvordan man installerer Produktoprettelse-v2 lokalt på hver PC med automatisk synkronisering via OneDrive.

---

## Oversigt

**Platform:** Windows 10/11  
**Storage:** OneDrive for Business (Bunzl)  
**Authentication:** Windows login (ingen ekstra login nødvendig)  
**Sync:** Automatisk mellem alle PC'er

---

## Fordele vs. Ulemper

### ✅ Fordele
- Ingen cloud hosting costs
- Ingen authentication setup nødvendig
- Fuld kontrol over data lokalt
- Hurtig lokal adgang
- Automatisk backup via OneDrive
- Delte filer mellem PC'er (produkter, cache, logs)
- Nemt at opdatere (automatisk sync)

### ❌ Ulemper
- Skal installeres på hver PC
- Ingen remote access udefra kontoret
- Virtual environment skal oprettes på hver PC
- Kræver Python installation på hver PC

---

## 1. Forudsætninger

### På Hver PC:
- ✅ Windows 10 eller 11
- ✅ OneDrive for Business (Bunzl konto)
- ✅ Internet forbindelse
- ✅ Administrator rettigheder (til Python installation)

### Download Links:
- **Python 3.11+:** https://www.python.org/downloads/
- **Git:** https://git-scm.com/download/win (valgfrit, hvis du bruger GitHub)

---

## 2. OneDrive Setup (Kun én gang)

### 2.1 Opret Projekt Mappe i OneDrive

**PC 1 (Anton):**

1. Åben File Explorer
2. Naviger til: `C:\Users\anton\OneDrive - Bunzl Continental Europe\Konsulent Daniel\`
3. Check at `Produktoprettelse-v2` mappen allerede findes
4. Vent på at OneDrive synkroniserer (grøn checkmark ikon)

### 2.2 Ekskluder `.venv/` Fra Synkronisering

**Vigtigt:** Virtual environment skal IKKE synkroniseres!

**Metode 1: OneDrive Settings (Anbefalet)**

1. Højreklik på OneDrive ikon i taskbar
2. Vælg **Settings** → **Backup** → **Manage backup**
3. Under **Folders**, find `Produktoprettelse-v2\.venv`
4. Fjern flueben (disable sync for denne mappe)

**Metode 2: PowerShell (Automatisk)**

Kør i PowerShell (som Administrator):

```powershell
Set-Location "C:\Users\$env:USERNAME\OneDrive - Bunzl Continental Europe\Konsulent Daniel\Produktoprettelse-v2"

# Set folder to "Free up space" (only online)
attrib +U .venv /S /D
```

---

## 3. Installation - PC 1 (Første Gang)

### 3.1 Installer Python

1. Download Python 3.11+ fra https://www.python.org/downloads/
2. **Vigtigt:** ✅ Vælg "Add Python to PATH" under installation
3. Installer med default settings
4. Verificer installation:

```powershell
python --version
# Output: Python 3.11.x
```

### 3.2 Naviger til Projekt Mappen

```powershell
cd "C:\Users\$env:USERNAME\OneDrive - Bunzl Continental Europe\Konsulent Daniel\Produktoprettelse-v2"
```

### 3.3 Opret Virtual Environment (LOKAL)

```powershell
# Opret .venv mappe (IKKE synkroniseret)
python -m venv .venv

# Aktiver virtual environment
.venv\Scripts\activate

# Installér dependencies
pip install -r requirements.txt
```

### 3.4 Opret `.env` Fil

**Vigtigt:** `.env` filen SKAL synkroniseres via OneDrive (indeholder passwords kun til intern brug).

Opret filen: `Produktoprettelse-v2\.env`

```env
# OpenAI API
OPENAI_API_KEY=sk-proj-...

# Dandomain API
API_KEY=your_dandomain_api_key

# FTP Credentials
FTP_USER=FtpUser4843158
FTP_PASSWORD=your_ftp_password
FTP_HOST=ftp.webshop8.dk
```

**Gem filen** - den synkroniseres automatisk til andre PC'er! ✅

### 3.5 Test Installation

```powershell
# Start app
streamlit run app/app.py
```

App åbner automatisk i browser på `http://localhost:8501`

---

## 4. Installation - PC 2, 3, 4... (Efter OneDrive Sync)

### 4.1 Vent På OneDrive Synkronisering

1. Log ind på OneDrive med Bunzl konto
2. Åben OneDrive indstillinger
3. Under **Account** → **Choose folders**, sørg for at:
   - ✅ `Konsulent Daniel\Produktoprettelse-v2` er valgt
4. Vent på synkronisering (grøn checkmark på mappen)

### 4.2 Installer Python (Samme Som PC 1)

Følg **Step 3.1** fra forrige sektion.

### 4.3 Naviger til Synkroniseret Mappe

```powershell
cd "C:\Users\$env:USERNAME\OneDrive - Bunzl Continental Europe\Konsulent Daniel\Produktoprettelse-v2"
```

### 4.4 Opret LOKAL Virtual Environment

```powershell
# Opret .venv (lokal per PC)
python -m venv .venv

# Aktiver
.venv\Scripts\activate

# Installér packages
pip install -r requirements.txt
```

**Bemærk:** `.env` filen er allerede synkroniseret! ✅ Ingen manuel kopiering nødvendig.

### 4.5 Test Installation

```powershell
streamlit run app/app.py
```

---

## 5. Daglig Brug

### 5.1 Start App

**Metode 1: Batch Script (Nemmest)**

Dobbeltklik på: `start_app.bat`

**Metode 2: PowerShell**

```powershell
cd "C:\Users\$env:USERNAME\OneDrive - Bunzl Continental Europe\Konsulent Daniel\Produktoprettelse-v2"
.venv\Scripts\activate
streamlit run app/app.py
```

### 5.2 Stop App

- Luk browser tab
- Tryk **Ctrl+C** i PowerShell vinduet
- Eller luk PowerShell vinduet

---

## 6. Automatiske Scripts

### 6.1 `setup.bat` - Første Gang Setup

````batch
@echo off
echo ========================================
echo Produktoprettelse-v2 Setup
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo FEJL: Python er ikke installeret!
    echo Download fra: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Create venv if missing
if not exist .venv (
    echo [1/3] Opretter virtual environment...
    python -m venv .venv
) else (
    echo [1/3] Virtual environment findes allerede
)

:: Activate and install
echo [2/3] Installerer pakker...
call .venv\Scripts\activate
pip install -r [requirements.txt](http://_vscodecontentref_/0)

:: Check .env
echo [3/3] Tjekker .env fil...
if not exist .env (
    echo.
    echo ADVARSEL: .env fil mangler!
    echo Vent på at OneDrive synkroniserer filen,
    echo eller opret den manuelt (se .env.template)
    echo.
)

echo.
echo ========================================
echo Setup faerdig!
echo Start app med: start_app.bat
echo ========================================
pause