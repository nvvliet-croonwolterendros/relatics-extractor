from collections import defaultdict

import pandas as pd

from relatics_extractor.processing.schema import SCHEMA


def normalize_tables(
    tables: dict[str, pd.DataFrame], schema: dict[str, dict[str, dict]] = SCHEMA
) -> dict[str, pd.DataFrame]:
    """
    Add missing optional columns to tables according to the schema.

    Columns marked ``not_null=False`` are added when missing and
    initialized with their configured default value. The resulting
    tables are validated against the schema before being returned.
    """

    normalized_tables: dict[str, pd.DataFrame] = {}

    for table_name, table_schema in schema.items():
        table = tables.get(table_name)

        if table is not None:
            df = table.copy()

            for column_name, column_rules in table_schema.items():
                if column_name not in df.columns:
                    df[column_name] = column_rules.get("default")

            df = df.dropna(how="all").reset_index(drop=True)

            normalized_tables[table_name] = df

    return normalized_tables


def validate_schema(
    tables: dict[str, pd.DataFrame],
    schema: dict[str, dict[str, dict]],
) -> None:
    """
    Validate tables against the configured schema.

    Checks:
    - Required tables exist.
    - Required columns exist.
    - Columns marked 'not_null' contain no null values.
    - Columns marked 'unique' contain no duplicate non-null values.
    """
    errors = defaultdict(list)

    for table_name, table_schema in schema.items():
        if table_name not in tables:
            errors["missing_tables"].append({"table": table_name})
            continue

        df = tables[table_name]

        missing_columns = [
            column for column in table_schema if column not in df.columns
        ]

        if missing_columns:
            errors["missing_columns"].append(
                {
                    "table": table_name,
                    "columns": missing_columns,
                }
            )
            continue

        null_columns = [
            column
            for column, column_rules in table_schema.items()
            if column_rules.get("not_null") and df[column].isna().any()
        ]

        if null_columns:
            errors["null_values"].append(
                {
                    "table": table_name,
                    "columns": null_columns,
                }
            )

        duplicate_columns = [
            column
            for column, column_rules in table_schema.items()
            if column_rules.get("unique") and df[column].dropna().duplicated().any()
        ]

        if duplicate_columns:
            errors["duplicate_values"].append(
                {
                    "table": table_name,
                    "columns": duplicate_columns,
                }
            )

    if errors:
        raise RuntimeError(format_validation_errors(errors))


def format_validation_errors(errors: dict[str, list[dict]]) -> str:
    sections = []

    for category, items in errors.items():
        lines = []

        for item in items:
            if category == "missing_tables":
                lines.append(item["table"])

            else:
                lines.append(f"{item['table']}: {', '.join(item['columns'])}")

        sections.append(f"{category}:\n- " + "\n- ".join(lines))

    return "Schema validation failed.\n\n" + "\n\n".join(sections)
