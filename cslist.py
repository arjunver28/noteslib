#!/usr/bin/env python3
"""
cslist.py - Excel to JSON Converter for Student Roster

Reads 'cslist.xlsx', deletes any existing 'cslist.json', and generates
a fresh, usable 'cslist.json' for the Notes Library application.
"""

import os
import sys
import json

def convert_cslist_to_json():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    xlsx_path = os.path.join(base_dir, 'cslist.xlsx')
    json_path = os.path.join(base_dir, 'cslist.json')

    print("=" * 60)
    print("  Notes Library - Student Roster (XLSX -> JSON) Converter")
    print("=" * 60)

    # 1. Verify Excel file exists
    if not os.path.exists(xlsx_path):
        print(f"[ERROR] Excel source file not found at: {xlsx_path}")
        sys.exit(1)

    # 2. Check for openpyxl
    try:
        import openpyxl
    except ImportError:
        print("[ERROR] 'openpyxl' library is required to read Excel files.")
        print("Please install it using: pip install openpyxl")
        sys.exit(1)

    print(f"[INFO] Reading Excel source: {xlsx_path}...")
    try:
        wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
        sheet = wb.active

        roster = {}
        row_count = 0
        skipped_count = 0

        for row in sheet.iter_rows(values_only=True):
            if not row or len(row) < 2:
                continue

            roll_raw = row[0]
            name_raw = row[1]

            if roll_raw is None or name_raw is None:
                continue

            roll_str = str(roll_raw).strip()
            name_str = str(name_raw).strip()

            # Skip table header rows
            if "roll" in roll_str.lower() or not roll_str or not name_str:
                skipped_count += 1
                continue

            # Normalize roll number (remove trailing .0 from floats and uppercase)
            if roll_str.endswith('.0'):
                roll_str = roll_str[:-2]
            roll_str = roll_str.upper()

            roster[roll_str] = name_str
            row_count += 1

        wb.close()

    except Exception as e:
        print(f"[ERROR] Failed to read '{xlsx_path}': {e}")
        sys.exit(1)

    # 3. Delete previous json file if it exists
    if os.path.exists(json_path):
        try:
            os.remove(json_path)
            print(f"[INFO] Deleted previous '{os.path.basename(json_path)}'.")
        except Exception as e:
            print(f"[WARN] Could not delete previous file: {e}")

    # 4. Write fresh JSON file
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(roster, f, indent=2, ensure_ascii=False)

        file_size_kb = os.path.getsize(json_path) / 1024
        print(f"[SUCCESS] Saved {len(roster)} student records to '{json_path}'.")
        print(f"[INFO] File size: {file_size_kb:.2f} KB")

        # Display preview of first 3 records
        print("\nPreview of first 3 records:")
        for idx, (roll, name) in enumerate(list(roster.items())[:3], 1):
            print(f"  {idx}. Roll: {roll} -> Name: {name}")

        print("=" * 60)
        return roster

    except Exception as e:
        print(f"[ERROR] Failed to write '{json_path}': {e}")
        sys.exit(1)

if __name__ == '__main__':
    convert_cslist_to_json()
