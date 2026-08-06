"""
Relatics Snapshot Connector
"""

import json
import pandas as pd
from datetime import datetime, timezone

from fivetran_connector_sdk import Connector
from fivetran_connector_sdk import Logging as log
from fivetran_connector_sdk import Operations as op

from extraction_service import extract_relatics

_tables_cache = None


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


def get_tables(configuration: dict) -> dict[str, pd.DataFrame]:
    """
    Extract Relatics data once per process and cache it,
    so schema() and update() don't both call the API.
    """
    global _tables_cache

    if _tables_cache is None:
        log.info("Extracting Relatics data (not cached yet)")
        _tables_cache = extract_relatics(
            client_id=configuration["client_id"],
            client_secret=configuration["client_secret"],
            environment=configuration["environment"],
        )
    else:
        log.info("Using cached Relatics data")

    return _tables_cache


def infer_primary_key(df: pd.DataFrame) -> list:
    """
    Infer primary key columns from Relatics tables.
    """

    if "guid" in df.columns:
        return ["guid", "workspace_id"]

    guid_columns = [
        col
        for col in df.columns
        if col.endswith("_guid")
    ]

    if guid_columns:
        return (
            guid_columns
            + ["workspace_id"]
        )

    raise ValueError(
        f"Unable to infer primary key. "
        f"Columns found: {list(df.columns)}"
    )


def build_schema_from_tables(
    tables: dict[str, pd.DataFrame]
) -> list:
    """
    Dynamically generate schema definitions.
    """

    schema_def = []

    for table_name, df in tables.items():

        columns = {
            "workspace_id": "STRING"            
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
    
    return schema_def


def schema(configuration: dict):
    """
    Dynamically generate schema from Relatics.
    """

    validate_configuration(configuration)

    log.info("Loading Relatics metadata for schema generation")

    tables = get_tables(configuration)

    return build_schema_from_tables(tables)


def update(configuration: dict, state: dict):
    """
    Perform a full sync.
    """

    validate_configuration(configuration)

    log.info(
        f"Starting Relatic sync"
    )

    try:

        tables = get_tables(configuration)

        log.info(f"Found {len(tables)} tables")
        
        total_rows = 0

        for table_name, df in tables.items():

            log.info(
                f"Processing {table_name}: {len(df)} rows"
                f"with {len(df)} records"
            )

            for record in df.to_dict("records"):

                op.upsert(
                    table=table_name,
                    data=record,
                )

                total_rows += 1

            log.info(
                f"Finished table '{table_name}'"
            )
            
            sync_timestamp = datetime.now(
                timezone.utc
            ).isoformat()

            op.checkpoint(
                {
                    "last_sync": sync_timestamp
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