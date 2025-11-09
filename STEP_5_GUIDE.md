# Step 5: Upload to CMS - Quick Reference

## Overview
Step 5 uploads finalized products to Dandomain CMS via:
1. **FTP** for images and PDFs
2. **REST API** for product data

## Prerequisites

### 1. Environment Variables
Add to your `.env` file:
```env
# Dandomain API
API_KEY=your_dandomain_api_key

# Dandomain FTP  
FTP_HOST=webshopdk.dk
FTP_USER=your_ftp_username
FTP_PASSWORD=your_ftp_password
```

### 2. Required Files
- `data/output/final_products.json` - Products with AI-generated content
- `data/images/[product_number]/` - Product images (optional)
- `data/pdfs/[product_number]/` - Product datablad PDFs (optional)

## Usage

### Command Line

**Dry Run (preview only):**
```bash
python scripts/5_upload_to_cms.py --dry-run
```

**Actual Upload:**
```bash
python scripts/5_upload_to_cms.py
```

**Custom input file:**
```bash
python scripts/5_upload_to_cms.py --input categorized_products.json
```

### Via Streamlit UI
1. Go to **Tab 1: Pipeline**
2. Select **"Step 5: Upload til Web"**
3. Choose mode:
   - Preview (dry run)
   - Upload
4. Click **"Kør Step 5"**

## What It Does

### 1. Validation
- Checks if product already exists (by `number` OR `vendorNumber`)
- Skips existing products (no duplicates)

### 2. Media Upload (FTP)
For each product:
- Uploads image: `data/images/[product_number]/*.jpg` → FTP `/images/produkt_billeder/[product_number].jpg`
- Uploads PDF: `data/pdfs/[product_number]/*.pdf` → FTP `/images/produkt_billeder/[product_number]_datablad.pdf`
- Generates public URLs

### 3. Product Creation (API)
Maps data to Dandomain schema:
```
Our Data               → Dandomain Field
────────────────────────────────────────────
PROD_NUM               → number
VendorNumber           → vendorNumber
PROD_NAME              → settings.items[0].name
DESC_SHORT             → settings.items[0].shortDescription
DESC_LONG              → settings.items[0].longDescription
ai_keywords            → settings.items[0].keyWords
primaryCategoryId      → primaryCategoryId
[uploaded image URL]   → pictureLink + media.items[]
[uploaded PDF URL]     → settings.items[0].techDocLink
```

POST to: `https://engrosrengoringsmidler.dk/admin/WebAPI/v2/products`

## Output

### Console/Logs
```
Processing: E146223 - Fremfører Ergoclean...
✓ Uploaded image: E146223.jpg
✓ Uploaded PDF: E146223_datablad.pdf  
✓ Created product: E146223

UPLOAD SUMMARY
──────────────
Total products:       3
Successfully created: 2
Skipped (existing):   1
Errors:               0
```

### Results File
`data/output/upload_results.json`:
```json
[
  {
    "product_number": "E146223",
    "status": "success",
    "message": "Product created successfully",
    "image_uploaded": true,
    "pdf_uploaded": true
  },
  {
    "product_number": "E146232",
    "status": "skipped",
    "message": "Product already exists (number: E146232)",
    "image_uploaded": false,
    "pdf_uploaded": false
  }
]
```

## Error Handling

### Common Issues

**1. FTP Connection Failed**
```
Failed to upload image via FTP: [Errno 11001] getaddrinfo failed
```
→ Check `FTP_HOST`, `FTP_USER`, `FTP_PASSWORD` in `.env`

**2. API Authentication Failed**
```
Failed to create product: 401 Unauthorized
```
→ Check `API_KEY` in `.env` (format: `:apikey` base64 encoded)

**3. Product Already Exists**
```
⚠️  Skipping - product already exists
```
→ Expected behavior - prevents duplicates

**4. Missing Category**
```
Failed to create product: primaryCategoryId is required
```
→ Make sure Step 3.5 (categorization) completed successfully

## Data Flow

```
Step 4 Output (final_products.json)
         ↓
Step 5: Upload to CMS
         ├── Upload images/PDFs (FTP)
         ├── Check if exists (API GET)
         └── Create product (API POST)
         ↓
Dandomain Webshop (live)
```

## Safety Features

1. **Dry Run Mode** - Preview before uploading
2. **Duplicate Check** - Never creates duplicates
3. **Error Logging** - All errors saved to `logs/5_upload_to_cms.log`
4. **Result Tracking** - JSON report of all operations

## API Documentation

- **Endpoint**: `https://engrosrengoringsmidler.dk/admin/WebAPI/v2/products`
- **Method**: POST
- **Auth**: Basic (`:apikey` base64 encoded)
- **Schema**: See `data/productdata_post_schema`

## FTP Structure

```
webshopdk.dk/
└── images/
    └── produkt_billeder/
        ├── E146223.jpg           ← Product images
        ├── E146223_datablad.pdf  ← Product PDFs
        ├── E146232.jpg
        └── ...
```

Public URL: `https://engrosrengoringsmidler.dk/images/produkt_billeder/[filename]`

## Tips

- Always run with `--dry-run` first to preview
- Check `upload_results.json` for detailed status
- Images/PDFs are optional - products can be created without them
- FTP uploads happen before API calls (media URLs needed for product data)
- Existing products are safely skipped (no overwrites)
