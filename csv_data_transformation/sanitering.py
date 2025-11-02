import pandas as pd
import json
import os
import numpy as np
from typing import List, Dict

class CSVSanitering:
    """Modul til databehandling og transformation af CSV-data"""
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def change_types(self):
        # Konverter relevante kolonner til korrekte typer
        type_map = {
            "NetWeight": float,
            "GreenTax": float,
            "UnitConvStockPurch": float,
            "ConvertedSystemCost": float,
            "TotalStockQty": "Int64"  # Pandas extension type for nullable integer
        }
        # Float-felter konverteres som før
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
        # Tilføj kolonne "Flerstk. pris" baseret på M kode
        if "ConvertedSystemCost" in self.df.columns:
            self.df["Flerstk. pris"] = ((self.df["ConvertedSystemCost"] / (1-0.5)) / 0.25).round(0) * 0.25
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
        Generer unikt PROD_NUM for hver række, startende fra højeste eksisterende PROD_NUM og +10 for hver.
        """
        import re
        # Generer nyt PROD_NUM for hver række
        match = re.match(r"([A-Za-z]+)(\d+)", max_prod_num)
        if match:
            prefix, num = match.groups()
            start_num = int(num)
        else:
            prefix, start_num = "E", 100000
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

    def process(self, cache_path: str = None):
        import os
        if cache_path is None:
            cache_path = os.path.join(os.path.dirname(__file__), '..', 'cache', 'products_cache.json')
            cache_path = os.path.abspath(cache_path)
        self.change_types()
        self.replace_value("ImageURL", "1XL", "processed")
        self.rename_columns()
        # Apply DataAreaID rules FIRST (before price calculations, so 10% markup affects Flerstk. pris and Retail_Price)
        self.apply_dataarea_rules()
        self.add_flerstk_pris()
        self.add_besparelse()
        self.add_retail_price()
        max_prod_num = self.get_highest_prod_num_from_cache(cache_path)
        self.add_prod_num(max_prod_num)
        self.add_img_name()
        return self.df

    def to_json(self, output_path: str = None) -> str:
        """Export processed DataFrame to JSON file. No manipulation, just the data as-is."""
        import numpy as np
        if output_path is None:
            output_path = os.path.join(os.path.dirname(__file__), '..', 'cache', 'processed_products.json')
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
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
        
        records = replace_nan(records)
        
        # Write to JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        
        return output_path

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