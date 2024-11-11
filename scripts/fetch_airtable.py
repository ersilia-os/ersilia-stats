#!/usr/bin/env python3

import os
import sys
import argparse
import csv
from pyairtable import Api
from pyairtable.formulas import match

airtable_api_key = sys.argv[1]
BASE_ID = "app1iYv78K6xbHkmL"
TABLE_ID = "tbluZtI3W9pseCSPH"

def fetch_table(api_key, base_id, table_id):
    """
    Fetch data from an Airtable table.

    Args:
        api_key (str): API key for Airtable.
        base_id (str): ID of the Airtable base.
        table_id (str): ID of the table to fetch.

    Returns:
        list: List of records from the table.

    Raises:
        SystemExit: If an exception occurs when fetching data from Airtable.
    """
    try:
        api = Api(api_key)
        table = api.table(base_id, table_id)
        records = table.all()
        print(f"Fetched {len(records)} records from table '{table_id}'.")
        return records
    except Exception as e:
        print(f"Error: Failed to fetch data from Airtable. Exception: {e}")
        sys.exit(1)

def convert_to_csv(records, output_file):
    """
    Convert a list of Airtable records to a CSV file.

    Args:
        records (list): List of records to write to CSV.
        output_file (str): Path to output CSV file.

    Returns:
        None

    Raises:
        SystemExit: If an exception occurs when writing data to CSV.
    """
    if not records:
        print("No records found to write to CSV.")
        return

    # Extract all unique field names across records
    field_names = set()
    for record in records:
        fields = record.get('fields', {})
        field_names.update(fields.keys())
    
    # Define CSV headers: id, createdTime, followed by sorted field names
    headers = ['id', 'createdTime'] + sorted(field_names)
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            for record in records:
                row = {
                    'id': record.get('id', ''),
                    'createdTime': record.get('createdTime', '')
                }
                fields = record.get('fields', {})
                for field in field_names:
                    row[field] = fields.get(field, '')
                writer.writerow(row)
        print(f"Data successfully written to '{output_file}'.")
    except Exception as e:
        print(f"Error: Failed to write data to CSV. Exception: {e}")
        sys.exit(1)

def main():
    # Fetch data from Airtable
    records = fetch_table(airtable_api_key, BASE_ID, TABLE_ID)

    # Determine output file name
    output_file = f"{TABLE_ID}.csv"

    # Convert fetched data to CSV
    convert_to_csv(records, output_file)

if __name__ == "__main__":
    main()
