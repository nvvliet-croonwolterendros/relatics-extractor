import os
from pathlib import Path
import pandas as pd

def encodebase64(zipfile):
    """
    This function should intake the pandas dataframe from xml_parser.py and thebae64 Documents.
    After this it should unpack the base64 to a zip and extract to memory.
    After that you get a bunsh of guid filenames. The actual files need to be encoded back to base64 and a df should be created with column [elementName, RelaticsIconBase64, hash].
    After that the hash should be calculated and the full df be prepared.
    """
    # Target folder
    folder = Path("extracted_files")

    for row in df.itertuples():
        old_filename = getattr(row, "RelaticsIconFilename")
        new_icon = getattr(row, "icon")

        # Skip if missing values exist in the row
        if pd.isna(old_filename) or pd.isna(new_icon):
            continue

        # Clean up the new name:
        # 1. Path(new_icon).stem removes the extension from df["icon"]
        # 2. replace(" ", "_") replaces spaces
        clean_stem = Path(new_icon).stem.replace(" ", "_")
        
        # Preserve the original file's extension
        ext = Path(old_filename).suffix

        old_path = folder / old_filename
        new_path = folder / f"{clean_stem}{ext}"

        try:
            old_path.rename(new_path)
        except FileNotFoundError:
            print(f"File not found: {old_path}")
        except Exception as e:
        print(f"Error renaming {old_filename} -> {new_path.name}: {e}")