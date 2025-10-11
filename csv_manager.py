import csv
from typing import List, Dict

class CSVManager:
    """Manager til at importere og bearbejde CSV data"""
    def __init__(self, filepath: str):
        self.filepath = filepath

    def load_csv(self) -> List[Dict]:
        """Importer CSV og returner som liste af dicts"""
        data = []
        with open(self.filepath, mode='r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                data.append(dict(row))
        return data

    # Her kan du tilføje flere metoder til bearbejdning og transformation

if __name__ == "__main__":
    # Eksempel på brug
    filepath = r"C:\Users\anton\OneDrive - Bunzl Continental Europe\Power BI\til_excel\Produktoprettelse-AI-pluspack.csv"
    csv_manager = CSVManager(filepath)
    rows = csv_manager.load_csv()
    print(f"Indlæst {len(rows)} rækker fra CSV.")
    print("Eksempel på data:")
    if rows:
        for key, value in list(rows[0].items()):
            print(f"  {key}: {value}")
