import pandas as pd
import logging
from typing import Dict

from src.processing.schema import SCHEMA

logger = logging.getLogger(__name__)

def normalize_tables(
    tables: Dict[str, pd.DataFrame],
    schema: Dict[str, dict] = SCHEMA
) -> Dict[str, pd.DataFrame]:
    """ 
    Function that takes a dict of tables and adds to each 
    table the unrequired columns according to the schema, 
    if they are not present.
    """
    logger.info(f"Parsing {len(tables.keys())} tables.")
    parsed_tables = {}
    for tablename, table_schema in schema.items():
        logger.debug(f"Parsing table: {tablename}")
        if tablename not in tables:
            raise KeyError(f'Relatics data does not contain the table {tablename}')
        
        # Work on a copy to avoid mutating the input fixture/dict
        df = tables[tablename].copy()

        # First check if all cols are present.
        all_cols = set(table_schema.keys())
        if all_cols.issubset(set(df.columns)):
            parsed_tables[tablename] = df
            logger.debug(f"{tablename} has all columns, moving to the next.")
            continue

        optional_cols = {column:columnrestrictions['default'] for column, columnrestrictions in table_schema.items() if columnrestrictions['required'] == False}
        for columnname, defaultvalue in optional_cols.items():
            if columnname not in df.columns:
                logger.debug(f"Add missing column: {columnname} in table: {tablename}")
                df[columnname] = defaultvalue
        parsed_tables[tablename] = df
    return parsed_tables

def is_valid_schema(
    tables: Dict[str, pd.DataFrame], schema: Dict[str, dict]
) -> None:
    """Checks tables against schema and returns validation report.

    Raises:
        RuntimeError: when required columns are missing from any table.
    """
    logger.info("Validating schema for %d table(s)...", len(tables))
    missing_report = {}

    for table_name, table_schema in schema.items():
        if table_name not in tables:
            logger.warning(f"Table '{table_name}' specified in schema was not found in input tables.")
            continue

        df = tables[table_name]
        missing_cols = [
            col_name
            for col_name, col_config in table_schema.items()
            if col_config.get("required", False) and col_name not in df.columns
        ]

        if missing_cols:
            missing_report[table_name] = missing_cols

    if missing_report:
        lines = [
            "Schema validation failed. The following required columns are missing:",
            "",
        ]
        for table_name, cols in missing_report.items():
            lines.append(f"- {table_name}: {', '.join(cols)}")
        error_msg = "\n".join(lines)

        raise RuntimeError(error_msg)

    logger.info("Schema validation passed successfully.")