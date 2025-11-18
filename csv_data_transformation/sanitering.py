import pandas as pd
import json
import os
import numpy as np
from typing import List, Dict
from pathlib import Path

class CSVSanitering:
    """Modul til databehandling og transformation af CSV-data"""
    
    # Class-level lookup tables (loaded once)
    LOOKUP_TABLES = {}
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        
        # Load lookup tables on first instantiation
        if not CSVSanitering.LOOKUP_TABLES:
            CSVSanitering._load_lookup_tables()
    
    @classmethod
    def _load_lookup_tables(cls):
        """Load all reference tables from csv_data_transformation/tabeller/"""
        tabeller_dir = Path(__file__).parent / "tabeller"
        
        tables = {
            "leverandor": "leverandor_tabel.json",
            "enheds_numerering": "enheds_numerering_tabel.json",
            "enhedskonvertering": "enhedskonvertering_tabel.json",
            "konstant": "konstant_tabel.json",
            "miljomaerke": "miljomaerke_tabel.json"
        }
        
        for key, filename in tables.items():
            table_path = tabeller_dir / filename
            if table_path.exists():
                try:
                    with open(table_path, 'r', encoding='utf-8') as f:
                        cls.LOOKUP_TABLES[key] = json.load(f)
                except Exception as e:
                    print(f"Warning: Could not load {filename}: {e}")
            else:
                print(f"Warning: Lookup table not found: {table_path}")
    
    def normalize_vendor_name(self, vendor_name: str) -> str:
        """Normalize vendor name using leverandor_tabel"""
        if not isinstance(vendor_name, str) or not vendor_name.strip():
            return vendor_name
        
        table = self.LOOKUP_TABLES.get("leverandor", {})
        # Try exact match first
        if vendor_name in table:
            return table[vendor_name]
        
        # Try case-insensitive match
        for key, normalized in table.items():
            if key.lower() == vendor_name.lower():
                return normalized
        
        # Return original if no match
        return vendor_name
    
    def decode_unit_name(self, unit_code: str) -> str:
        """Decode unit code to unit name using enheds_numerering_tabel"""
        if not isinstance(unit_code, str):
            unit_code = str(unit_code).strip() if pd.notna(unit_code) else ""
        
        if not unit_code:
            return unit_code
        
        table = self.LOOKUP_TABLES.get("enheds_numerering", {})
        return table.get(unit_code, unit_code)
    
    def convert_unit_abbreviation(self, unit_abbr: str) -> str:
        """Convert unit abbreviation using enhedskonvertering_tabel"""
        if not isinstance(unit_abbr, str) or not unit_abbr.strip():
            return unit_abbr
        
        table = self.LOOKUP_TABLES.get("enhedskonvertering", {})
        return table.get(unit_abbr.lower(), unit_abbr)
    
    def decode_certification(self, cert_code: str) -> str:
        """Decode certification code using miljomaerke_tabel"""
        if not isinstance(cert_code, str) or not cert_code.strip():
            return cert_code
        
        table = self.LOOKUP_TABLES.get("miljomaerke", {})
        return table.get(cert_code, cert_code)
    
    def get_constants(self) -> Dict:
        """Get default constants from konstant_tabel"""
        return self.LOOKUP_TABLES.get("konstant", {})

    def change_types(self):
        # Konverter relevante kolonner til korrekte typer
        type_map = {
            "NetWeight": float,
            "GreenTax": float,
            "UnitConvStockPurch": float,
            "ConvertedSystemCost": float,
            "TotalStockQty": "Int64"  # Pandas extension type for nullable integer
        }
        for col, dtype in type_map.items():
            if col in self.df.columns and col not in ["NetWeight", "PROD_WEIGHT"]:
                if dtype == float:
                    # Robust float-konvertering
                    def fix_decimal(val):
                        s = str(val)
                        if "," in s and "." in s:
                            s = s.replace('.', '').replace(',', '.')
                        elif "," in s:
                            s = s.replace(',', '.')
                        return s
                    self.df[col] = self.df[col].apply(fix_decimal).astype(float)
        # Kun NetWeight og PROD_WEIGHT skal have punktum erstattet med komma
        if "NetWeight" in self.df.columns:
            self.df["NetWeight"] = self.df["NetWeight"].astype(str).str.replace('.', ',')
        if "PROD_WEIGHT" in self.df.columns:
            self.df["PROD_WEIGHT"] = self.df["PROD_WEIGHT"].astype(str).str.replace('.', ',')
        # Int64 kolonner
        for col, dtype in type_map.items():
            if col in self.df.columns and dtype == "Int64":
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce').astype("Int64")
        return self.df

    def replace_value(self, col: str, old, new):
        # Udskift '1XL' med 'processed' i ImageURL, hvis linket indeholder 'Bunzl'
        if col in self.df.columns:
            def bunzl_replace(val):
                if isinstance(val, str) and "Bunzl" in val and old in val:
                    return val.replace(old, new)
                return val
            self.df[col] = self.df[col].apply(bunzl_replace)
        return self.df

    def add_flerstk_pris(self):
        # Tilføj kolonne "Flerstk. pris" baseret på PROD_COST_PRICE (som inkluderer 10% markup for mln)
        if "PROD_COST_PRICE" in self.df.columns:
            self.df["Flerstk. pris"] = ((self.df["PROD_COST_PRICE"] / (1-0.5)) / 0.25).round(0) * 0.25
        return self.df

    def add_besparelse(self):
        # Tilføj "Besparelse" baseret på M kode
        def besparelse(row):
            pris = row.get("Flerstk. pris", 0)
            if pris <= 10:
                return 30
            elif pris <= 100:
                return 20
            elif pris <= 500:
                return 15
            else:
                return 10
        if "Flerstk. pris" in self.df.columns:
            self.df["Besparelse"] = self.df.apply(besparelse, axis=1)
        return self.df

    def add_retail_price(self):
        # Tilføj "Retail_Price" baseret på M kode
        if "Flerstk. pris" in self.df.columns and "Besparelse" in self.df.columns:
            self.df["Retail_Price"] = ((self.df["Flerstk. pris"] / ((100-self.df["Besparelse"]) / 100)) / 0.25).round(0) * 0.25
        return self.df

    def rename_columns(self):
        # Omdøb kolonner baseret på M kode
        rename_map = {
            "ItemID": "ORIGINAL_VENDOR_NUM",
            "TotalStockQty": "STOCK_COUNT",
            "ItemName": "ORIGINAL_PROD_NAME",
            "ItemBarcode": "PROD_BARCODE_NUMBER",
            "NetWeight": "PROD_WEIGHT",
            "ConvertedSystemCost": "PROD_COST_PRICE",
            "ProductMeasures": "FIELD_20",
            "GreenTax": "FIELD_18",
            "ArticleInfoSales": "PROD_NOTES"
        }
        self.df = self.df.rename(columns=rename_map)
        return self.df

    def normalize_vendors(self):
        """Normalize vendor names using leverandor_tabel lookup"""
        if "PrimaryVendorName" in self.df.columns:
            self.df["PrimaryVendorName"] = self.df["PrimaryVendorName"].apply(self.normalize_vendor_name)
        return self.df

    def add_packing_info(self):
        """Add FIELD_17: Packing info based on DataAreaID
        - For 'cc': Use SalesUnit_PackingInfo
        - For 'mln': Use PackingInfoInStockUnit
        """
        def get_packing_info(row):
            area_id = row.get("DataAreaID", "")
            if area_id == "mln":
                return row.get("PackingInfoInStockUnit", "")
            else:  # Default to cc or any other area
                return row.get("SalesUnit_PackingInfo", "")
        
        self.df["FIELD_17"] = self.df.apply(get_packing_info, axis=1)
        return self.df

    def parse_unit_description(self):
        """Add FIELD_1: Parse unit description from FIELD_17
        Converts packing info like "4 fl", "12.5 kg", "1 set" into standardized format
        """
        import re
        
        def parse_unit(field_17):
            if not isinstance(field_17, str) or not field_17.strip():
                return "1 stk."
            
            text = field_17.lower().strip()
            
            # Check for special cases
            if text == "" or text == "1 set":
                return "1 sæt"
            if text == "1 stk" or text == "stk" or text == "1 stk.":
                return "1 stk."
            
            # Split by "/" for left and right parts
            parts = text.split("/")
            left = parts[0].strip() if parts else ""
            right = parts[1].strip() if len(parts) > 1 else ""
            
            # Extract number + unit from left side (e.g., "4 fl", "12.5 kg")
            if "x" in left:
                antal_enhed = left.split("x")[0]
            else:
                antal_enhed = left
            
            # Extract number and unit separately
            antal_raw = re.sub(r'[^0-9,.]', '', antal_enhed)
            antal_standard = antal_raw.replace(".", ",")
            
            enhed = re.sub(r'[^a-zæøå]', '', antal_enhed)
            
            # Standardize right side (unit type)
            antalstype_map = {
                "krt": "ks", "ps": "ps", "pk": "pk", "fl": "fl",
                "ds": "ds", "rl": "rl"
            }
            antalstype = antalstype_map.get(right, right if right else "stk")
            
            # Check if only unit provided
            only_unit = not antal_raw and enhed and not (text == "" or text == "1 set")
            
            # Assemble result
            if text == "1 stk" or text == "stk":
                return "1 stk."
            elif only_unit:
                return f"1 {enhed}."
            elif antal_standard and enhed and antalstype:
                return f"1 {antalstype} (á {antal_standard} {enhed})"
            else:
                return "1 stk."
        
        self.df["FIELD_1"] = self.df["FIELD_17"].apply(parse_unit)
        return self.df

    def map_unit_ids(self):
        """Add PROD_UNIT_ID: Map SalesUnitID to unit using enheds_numerering_tabel"""
        def map_unit(row):
            sales_unit_id = row.get("SalesUnitID")
            if pd.isna(sales_unit_id):
                return 1
            
            unit_id_str = str(sales_unit_id).strip()
            table = self.LOOKUP_TABLES.get("enheds_numerering", {})
            
            # Try to get the unit code and return it, or default to 1
            result = table.get(unit_id_str)
            if result:
                return result
            return unit_id_str if unit_id_str else 1
        
        self.df["PROD_UNIT_ID"] = self.df.apply(map_unit, axis=1)
        return self.df

    def convert_unit_ids(self):
        """Convert SalesUnitID and StockUnitID from text codes to numeric IDs using enheds_numerering_tabel"""
        table = self.LOOKUP_TABLES.get("enheds_numerering", {})
        
        def convert_unit(unit_text):
            if pd.isna(unit_text):
                return unit_text
            unit_str = str(unit_text).strip()
            # Look up the numeric ID from the table
            # The table maps numeric ID -> text code (e.g., "6" -> "krt")
            # We need to reverse lookup: find numeric ID where value matches unit_str
            for numeric_id, code in table.items():
                if code == unit_str:
                    return numeric_id
            return unit_text  # Return as-is if not found
        
        if "SalesUnitID" in self.df.columns:
            self.df["SalesUnitID"] = self.df["SalesUnitID"].apply(convert_unit)
        if "StockUnitID" in self.df.columns:
            self.df["StockUnitID"] = self.df["StockUnitID"].apply(convert_unit)
        return self.df

    def convert_code_to_certification(self):
        """Convert Code column from miljomaerke codes to certification names using miljomaerke_tabel"""
        table = self.LOOKUP_TABLES.get("miljomaerke", {})
        
        def lookup_certification(code):
            if pd.isna(code) or not isinstance(code, str) or not code.strip():
                return code
            code_str = code.strip()
            # Look up the certification name from the table
            result = table.get(code_str)
            return result if result else code
        
        if "Code" in self.df.columns:
            self.df["Code"] = self.df["Code"].apply(lookup_certification)
        return self.df

    def add_field_2(self):
        """Add FIELD_2: Copy the certification name from Code column
        Note: Code is already converted from code (e.g., "A02") to name (e.g., "Egnet til fødevarekontakt")
        by convert_code_to_certification() in Phase 3
        """
        if "Code" in self.df.columns:
            self.df["FIELD_2"] = self.df["Code"]
        return self.df

    def convert_unit_formats(self):
        """Apply unit conversions to FIELD_17 using enhedskonvertering_tabel
        E.g., krt → ks, set → sæt
        """
        table = self.LOOKUP_TABLES.get("enhedskonvertering", {})
        
        if "FIELD_17" in self.df.columns:
            for original, converted in table.items():
                self.df["FIELD_17"] = self.df["FIELD_17"].str.replace(
                    original, converted, regex=False, case=False
                )
        
        return self.df

    def apply_constants(self):
        """Add constant columns from konstant_tabel"""
        constants = self.get_constants()
        
        for col_name, value in constants.items():
            if col_name not in self.df.columns:
                self.df[col_name] = value
        
        return self.df

    def add_img_name(self):
        """Generate IMG_NAME from PROD_NUM_old and ORIGINAL_PROD_NAME following Excel formula logic."""
        def generate_img_name(prod_num, prod_name):
            if pd.isna(prod_num) or pd.isna(prod_name):
                return ""
            
            # Concatenate
            img_name = f"{prod_num}-{prod_name}"
            
            # Lowercase
            img_name = img_name.lower()
            
            # Replace Danish characters
            img_name = img_name.replace("å", "aa")
            img_name = img_name.replace("ø", "oe")
            img_name = img_name.replace("Ø", "oe")
            img_name = img_name.replace("æ", "ae")
            
            # Replace special characters
            img_name = img_name.replace(" ", "-")
            img_name = img_name.replace("/", "-")
            img_name = img_name.replace("%", "procent")
            img_name = img_name.replace("+", "plus")
            
            # Remove any remaining special characters that might cause issues
            img_name = img_name.replace("(", "")
            img_name = img_name.replace(")", "")
            img_name = img_name.replace(".", "-")
            img_name = img_name.replace(",", "-")
            
            # Clean up multiple hyphens
            while "--" in img_name:
                img_name = img_name.replace("--", "-")
            
            # Remove leading/trailing hyphens
            img_name = img_name.strip("-")
            
            return img_name
        
        self.df["IMG_NAME"] = self.df.apply(
            lambda row: generate_img_name(row.get("PROD_NUM_old"), row.get("ORIGINAL_PROD_NAME")),
            axis=1
        )
        return self.df

    def clean_barcode_by_area(self):
        """Clean PROD_BARCODE_NUMBER based on DataAreaID.
        - For 'cc' DataAreaID: Remove leading 'C' from barcode
        - For 'mln': Keep as-is (or apply other rules as needed)
        """
        def clean_barcode(row):
            barcode = row.get("PROD_BARCODE_NUMBER")
            area_id = row.get("DataAreaID", "")
            
            if not isinstance(barcode, str) or not barcode:
                return barcode
            
            # For 'cc' area, remove leading 'C'
            if area_id == "cc" and barcode.startswith("C"):
                return barcode[1:]
            
            # For 'mln' or other areas, return as-is
            return barcode
        
        self.df["PROD_BARCODE_NUMBER"] = self.df.apply(clean_barcode, axis=1)
        return self.df

    def apply_dataarea_rules(self):
        """
        Apply all DataAreaID-specific business rules.
        
        Rules by DataAreaID:
        
        'cc' (Continental Europe):
        - Remove leading 'C' from barcode
        - Use SalesUnitID for all unit-based calculations (prices, conversions, etc.)
        
        'mln' (MLN specific):
        - Apply 10% markup to cost prices
        - Use StockUnitID for all unit-based calculations (prices, conversions, etc.)
        """
        def apply_rules(row):
            area_id = row.get("DataAreaID", "")
            
            # MLN: Apply 10% markup to cost prices
            if area_id == "mln":
                # Apply 10% markup to ConvertedSystemCost (which becomes PROD_COST_PRICE)
                if "PROD_COST_PRICE" in row and pd.notna(row["PROD_COST_PRICE"]):
                    row["PROD_COST_PRICE"] = row["PROD_COST_PRICE"] * 1.10
                
                # Use StockUnitID for calculations
                if "StockUnitID" in row:
                    row["ACTIVE_UNIT_ID"] = row["StockUnitID"]
            
            # CC: Remove leading 'C' from barcode (handled separately for clarity)
            if area_id == "cc":
                barcode = row.get("PROD_BARCODE_NUMBER", "")
                if isinstance(barcode, str) and barcode.startswith("C"):
                    row["PROD_BARCODE_NUMBER"] = barcode[1:]
                
                # Use SalesUnitID for calculations
                if "SalesUnitID" in row:
                    row["ACTIVE_UNIT_ID"] = row["SalesUnitID"]
            
            # Default: if ACTIVE_UNIT_ID not set, use SalesUnitID
            if "ACTIVE_UNIT_ID" not in row or pd.isna(row.get("ACTIVE_UNIT_ID")):
                row["ACTIVE_UNIT_ID"] = row.get("SalesUnitID", row.get("StockUnitID", ""))
            
            return row
        
        self.df = self.df.apply(apply_rules, axis=1)
        return self.df

    def add_prod_num(self, max_prod_num: str):
        """
        Generer unikt PROD_NUM for hver række, startende fra højeste eksisterende PROD_NUM + 10 og derefter +10 for hver.
        E.g., hvis max er E146223, så starter vi fra E146230
        """
        import re
        import math
        # Generer nyt PROD_NUM for hver række
        match = re.match(r"([A-Za-z]+)(\d+)", max_prod_num)
        if match:
            prefix, num = match.groups()
            current_num = int(num)
            # Round up to next multiple of 10
            start_num = math.ceil(current_num / 10) * 10
        else:
            prefix, start_num = "E", 100000
        # Generate product numbers starting from rounded value
        prod_nums = [f"{prefix}{start_num + i*10}" for i in range(len(self.df))]
        self.df["PROD_NUM"] = [num + " - Deaktiveret" for num in prod_nums]
        self.df["PROD_NUM_old"] = prod_nums
        return self.df

    def get_highest_prod_num_from_cache(self, cache_path: str) -> str:
        """Find højeste PROD_NUM fra products_cache.json ved at lede efter 'number'"""
        import json, re
        with open(cache_path, encoding="utf-8") as f:
            products = json.load(f)
        prod_nums = []
        for prod in products:
            val = prod.get("number") or prod.get("ItemID") or ""
            match = re.match(r"([A-Za-z]+)(\d+)", val)
            if match:
                prefix, num = match.groups()
                prod_nums.append((prefix, int(num)))
        if prod_nums:
            # Find max nummer
            prefix, max_num = max(prod_nums, key=lambda x: x[1])
            print(f"Højeste PROD_NUM fundet i cache: {prefix}{max_num}")
            return f"{prefix}{max_num}"
        print("Ingen PROD_NUM fundet i cache, starter fra E100000")
        return "E100000"

    def process(self, cache_path: str):
        # Phase 1: Type conversions and basic cleanup
        self.change_types()
        self.replace_value("ImageURL", "1XL", "processed")
        
        # Phase 2: Column renames
        self.rename_columns()
        
        # Phase 3: Lookup table transformations
        self.normalize_vendors()
        self.add_packing_info()
        self.parse_unit_description()
        self.convert_unit_ids()  # Convert SalesUnitID and StockUnitID to numeric IDs
        self.convert_code_to_certification()  # Convert Code column to certification names
        self.map_unit_ids()
        self.add_field_2()
        self.convert_unit_formats()
        self.apply_constants()
        
        # Phase 4: DataAreaID rules (before price calculations so markup cascades)
        self.apply_dataarea_rules()
        
        # Phase 5: Price calculations
        self.add_flerstk_pris()
        self.add_besparelse()
        self.add_retail_price()
        
        # Phase 6: Generate product IDs and metadata
        max_prod_num = self.get_highest_prod_num_from_cache(cache_path)
        self.add_prod_num(max_prod_num)
        self.add_img_name()
        
        return self.df

    def to_records(self) -> List[Dict]:
        """Convert processed DataFrame to list of dictionaries with NaN handling."""
        import numpy as np
        
        # Convert DataFrame to list of dictionaries
        records = self.df.to_dict(orient='records')
        
        # Replace NaN and inf with None
        def replace_nan(obj):
            if isinstance(obj, dict):
                return {k: replace_nan(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_nan(v) for v in obj]
            elif isinstance(obj, float):
                if np.isnan(obj) or np.isinf(obj):
                    return None
            return obj
        
        return replace_nan(records)

if __name__ == "__main__":
    # Eksempel på brug
    import sys
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
        df = pd.read_csv(csv_path)
        sanitering = CSVSanitering(df)
        df_trans = sanitering.process()
        
        # Output to JSON
        json_file = sanitering.to_json()
        print(f"✅ Exported to: {json_file}")
    else:
        print("Angiv sti til CSV-fil som argument.")