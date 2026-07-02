"""
Relatics Snapshot Connector

Creates a daily snapshot of Relatics data.
Each sync performs a full extraction and writes a new snapshot
identified by snapshot_date.

Primary key strategy:
- Regular tables: guid + snapshot_date
- Link tables: all columns + snapshot_date
"""

import json
import pandas as pd
from datetime import datetime, timezone

from fivetran_connector_sdk import Connector
from fivetran_connector_sdk import Logging as log
from fivetran_connector_sdk import Operations as op

from src.services.extraction_service import extract_relatics

def validate_configuration(configuration: dict):
    required_configs = [
        "client_id",
        "client_secret",
        "environment",
    ]

    for config in required_configs:
        if not configuration.get(config):
            raise ValueError(
                f"Missing required configuration value: {config}"
            )


def infer_primary_key(df: pd.DataFrame) -> list:
    """
    Determine the primary key columns.

    If table contains guid:
        PK = guid + snapshot_date

    Otherwise assume link table and use all columns
    + snapshot_date.
    """

    if "guid" in df.columns:
        return ["guid", "workspace_id", "snapshot_date"]

    return list(df.columns) + ["snapshot_date"]


def build_schema_from_tables(
    tables: dict[str, pd.DataFrame]
) -> list:
    """
    Dynamically generate schema definitions.
    """

    schema_def = []

    for table_name, df in tables.items():

        columns = {
            "snapshot_date": "STRING",            
        }

        for column in df.columns:
            columns[column] = "STRING"

        schema_def.append(
            {
                "table": table_name,
                "primary_key": infer_primary_key(df),
                "columns": columns,
            }
        )

    log.info(f"Schema: {schema_def}")
    
    return schema_def


def schema(configuration: dict):
    """
    Dynamically generate schema from Relatics.
    """

    validate_configuration(configuration)

    log.info("Loading Relatics metadata for schema generation")

    tables = extract_relatics(
        client_id=configuration["client_id"],
        client_secret=configuration["client_secret"],
        environment=configuration["environment"],
    )

    return build_schema_from_tables(tables)


def update(configuration: dict, state: dict):
    """
    Perform a full snapshot sync.
    """

    validate_configuration(configuration)

    client_id = configuration["client_id"]
    client_secret = configuration["client_secret"]
    environment = configuration["environment"]

    snapshot_date = (
        datetime.now(timezone.utc)
        .date()
        .isoformat()
    )

    log.info(
        f"Starting Relatics snapshot sync "
        f"for snapshot_date={snapshot_date}"
    )

    try:

        tables = extract_relatics(
            client_id=client_id,
            client_secret=client_secret,
            environment=environment,
        )

        log.info(f"Found {len(tables)} tables")
        
        total_rows = 0

        for table_name, df in tables.items():

            log.info(
                f"Processing {table_name}: {len(df)} rows"
                f"with {len(df)} records"
            )
            
            log.info(
                f"Colums: {df.columns}"
            )

            df = df.copy()

            df["snapshot_date"] = snapshot_date

            for record in df.to_dict("records"):

                op.upsert(
                    table=table_name,
                    data=record,
                )

                total_rows += 1

            log.info(
                f"Finished table '{table_name}'"
            )

        op.checkpoint(
            {
                "last_snapshot_date": snapshot_date
            }
        )

        log.info(
            f"Sync complete. "
            f"Processed {total_rows} records."
        )

    except Exception as exc:
        log.error(
            f"Sync failed: {str(exc)}"
        )
        raise


connector = Connector(
    update=update,
    schema=schema,
)


if __name__ == "__main__":

    with open(
        "configuration.json",
        "r",
        encoding="utf-8"
    ) as file:
        configuration = json.load(file)

    connector.debug(
        configuration=configuration
    )