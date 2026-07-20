#!/usr/bin/env python3
"""
Script to run extraction_service and output only one table to CSV for inspection.
"""

import sys
import os
import json
import pandas as pd
from datetime import datetime

# Add the src directory to Python path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.extraction_service import extract_relatics

def main():
    print("Relatics Extraction Service - Single Table Export")
    print("=" * 50)
    
    # Get credentials from user input
    client_id = input("Enter your Client ID: ").strip()
    client_secret = input("Enter your Client Secret: ").strip() 
    environment = input("Enter your Environment (e.g., 'prod', 'test'): ").strip()
    
    if not all([client_id, client_secret, environment]):
        print("Error: All credentials must be provided.")
        return
    
    # Run extraction service
    print("\nExtracting Relatics data...")
    
    try:
        tables = extract_relatics(
            client_id=client_id,
            client_secret=client_secret,
            environment=environment
        )
        
        print(f"Extraction complete. Found {len(tables)} tables:")
        
        # List all table names
        table_names = list(tables.keys())
        for i, name in enumerate(table_names):
            print(f"{i+1}. {name}")
        
        if not table_names:
            print("No tables found!")
            return
        
        # Select first table to output (you can modify this logic as needed)
        selected_table_name = table_names[0]
        selected_table = tables[selected_table_name]
        
        print(f"\nSelected table: {selected_table_name}")
        print(f"Shape: {selected_table.shape}")
        print("\nColumns:")
        for col in selected_table.columns:
            print(f"  - {col}")
            
        # Get current timestamp for unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Write to CSV
        output_filename = f"extracted_table_{selected_table_name}_{timestamp}.csv"
        
        # Write the table in a way that handles any potential issues with special characters
        selected_table.to_csv(output_filename, index=False)
        
        print(f"\nSuccessfully wrote table '{selected_table_name}' to {output_filename}")
        print(f"Table has {len(selected_table)} rows and {len(selected_table.columns)} columns")
        
        # Show a preview of the data (first 5 rows)
        print("\nPreview of data:")
        print(selected_table.head())
        
    except Exception as e:
        print(f"Error during extraction: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()