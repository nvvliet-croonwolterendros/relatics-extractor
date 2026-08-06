from pathlib import Path
from typing import Dict
import os
import sqlite3
import json
import pandas as pd

from extraction_service import extract_relatics

def _write_to_sqlite(
    tables: Dict[str, pd.DataFrame],
    db_dir: str | Path,
    db_path: str | Path,
) -> None:
    db_dir = Path(db_dir)
    db_path = Path(db_path)

    # create directory
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    # Remove existing database
    if db_path.exists():
        db_path.unlink()

    # Create new database and write tables
    with sqlite3.connect(db_path) as conn:
        for table_name, df in tables.items():
            df.to_sql(
                name=table_name,
                con=conn,
                index=False,
                if_exists="replace",
            )

        conn.commit()
        
if __name__ == "__main__":

    # load configuration
    with open(
        "configuration.json",
        "r",
        encoding="utf-8"
    ) as file:
        configuration = json.load(file)
        
    # extract relatics 
    tables = extract_relatics(
        configuration["client_id"],
        configuration["client_secret"],
        configuration["environment"]
    )

    # write to sqlite
    _write_to_sqlite(
        tables=tables,
        db_dir="data",
        db_path="data/relatics.sqlite",
    )