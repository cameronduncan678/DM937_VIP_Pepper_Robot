import csv
import ast

def search_product_by_name(product_name, csv_file="database/products.csv"):
    with open(csv_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Name"].lower() == product_name.lower():
                coords = ast.literal_eval(row["Location"])
                return coords
    return None
