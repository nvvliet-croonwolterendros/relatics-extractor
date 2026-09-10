import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from relatics_extractor.ingestion.relatics_client import RelaticsClient
from relatics_extractor.ingestion.xml_parser import parse_xml
from relatics_extractor.processing.schema import SCHEMA
from relatics_extractor.processing.transformer import create_element_tables
from relatics_extractor.processing.validator import is_valid_schema, normalize_tables

logger = logging.getLogger(__name__)


def extract_elements(
    client: RelaticsClient,
    workspace_config: dict[str, list[str]],
    operation: str,
    parallel: bool = False,
    max_workers: int | None = None,
    property_relations: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Extracts and transforms Relatics elements into normalized tables.

    For each configured workspace and element combination, retrieves the
    corresponding Relatics XML payload, validates the extracted schema,
    normalizes the resulting tables, and applies business transformations.

    Processing can be executed sequentially or in parallel.

    Args:
        client: Configured Relatics API client.
        workspace_config: Mapping of workspace IDs to lists of element IDs
            that should be extracted.
        operation: Relatics operation name used to retrieve the
            element data.
        parallel: Whether element extraction should be executed in
            parallel.
        max_workers: Maximum number of worker threads used when
            run_parallel is True. If None, the ThreadPoolExecutor
            default is used.
        property_relations: Relation names of Relations to R2 Elements
            whose values should be materialized directly in the
            resulting element tables.

    Returns:
        Dictionary mapping table names to transformed pandas DataFrames.

    Raises:
        Exception: Any exception raised during retrieval, validation,
            normalization, or transformation of element data.
    """
    jobs = [
        (workspace_id, element_id)
        for workspace_id, element_ids in workspace_config.items()
        for element_id in element_ids
    ]

    logger.info(
        "Starting extraction for %s elements (parallel=%s)",
        len(jobs),
        parallel,
    )

    tables: dict[str, pd.DataFrame] = {}

    if parallel:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(
                    _process_element,
                    element_id=element_id,
                    client=client,
                    workspace_id=workspace_id,
                    operation=operation,
                    property_relations=property_relations,
                ): (workspace_id, element_id)
                for workspace_id, element_id in jobs
            }

            for future in as_completed(future_map):
                workspace_id, element_id = future_map[future]

                try:
                    _merge_tables(tables, future.result())
                except Exception:
                    logger.exception(
                        "Failed processing workspace_id=%s element_id=%s",
                        workspace_id,
                        element_id,
                    )
                    raise
    else:
        for workspace_id, element_id in jobs:
            try:
                _merge_tables(
                    tables,
                    _process_element(
                        element_id=element_id,
                        client=client,
                        workspace_id=workspace_id,
                        operation=operation,
                        property_relations=property_relations,
                    ),
                )
            except Exception:
                logger.exception(
                    "Failed processing workspace_id=%s element_id=%s",
                    workspace_id,
                    element_id,
                )
                raise

    logger.info(
        "Extraction completed successfully. Generated %s tables.",
        len(tables),
    )

    return tables


def _process_element(
    element_id: str,
    client: RelaticsClient,
    workspace_id: str,
    operation: str,
    schema: dict[str, dict] = SCHEMA,
    property_relations: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Processes a Relatics element with its first order relations and properties.
    """
    parameters = {"ConfigurationOfRef": element_id}

    element_data = client.get_request(
        workspace_id=workspace_id,
        operation=operation,
        parameters=parameters,
    )

    tables = {table_name: parse_xml(element_data, table_name) for table_name in schema}
    is_valid_schema(tables=tables, schema=schema)
    normalized_tables = normalize_tables(tables=tables, schema=schema)
    transformed_tables = create_element_tables(
        tables=normalized_tables, property_relations=property_relations
    )

    for table in transformed_tables.values():
        table["workspace_id"] = workspace_id

    return transformed_tables


def _merge_tables(
    tables: dict[str, pd.DataFrame],
    element_tables: dict[str, pd.DataFrame],
) -> None:
    for table_name, df in element_tables.items():
        if table_name in tables:
            tables[table_name] = pd.concat(
                [tables[table_name], df],
                ignore_index=True,
            )
        else:
            tables[table_name] = df
