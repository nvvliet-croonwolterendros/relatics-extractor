import json
import os
import sqlite3
from pathlib import Path

import pandas as pd

from relatics_extractor import RelaticsClient, extract_element_tables, parse_xml


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

    workspace_elements = {}

    elements_root = client.get_request(
        workspace_id="210b2918-b359-4892-a23b-bf96ad23d82f",
        operation="dip_elements",
    )

    elements_df = parse_xml(elements_root, "Elements")

    workspace_elements["210b2918-b359-4892-a23b-bf96ad23d82f"] = elements_df[
        "ElementID"
    ].tolist()

    operation = "dip_data_model_3"

    tables = extract_element_tables(
        client=client,
        workspace_elements=workspace_elements,
        operation=operation,
        parallel=True,
        max_workers=None,
        inline_relations=["Heeft property"],
    )

    for key, table in tables.items():
        for column in table.columns:
            if column == "":
                print(key)
                print(table)

    db_dir = "data"
    db_path = "data/relatics.sqlite"

    _write_to_sqlite(tables=tables, db_dir=db_dir, db_path=db_path)
