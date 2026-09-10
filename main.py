import json
import os
import sqlite3
from pathlib import Path

import pandas as pd

from relatics_extractor import RelaticsClient, extract_elements


def _write_to_sqlite(
    tables: dict[str, pd.DataFrame],
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
    with open("configuration.json", encoding="utf-8") as file:
        configuration = json.load(file)

    client = RelaticsClient(
        configuration["client_id"],
        configuration["client_secret"],
        configuration["environment"],
    )

    workspace_config = {
        "210b2918-b359-4892-a23b-bf96ad23d82f": [
            "abdc7184-9b2e-e911-a2d5-00155d641103",
            "aa982e98-7b2f-e911-a2d5-00155d641103",
            "test_element_id",
        ]
    }

    operation = "dip_data_model_3"

    tables = extract_elements(
        client=client, workspace_config=workspace_config, operation=operation
    )

    db_dir = "data"
    db_path = "data/relatics.sqlite"

    _write_to_sqlite(tables=tables, db_dir=db_dir, db_path=db_path)
