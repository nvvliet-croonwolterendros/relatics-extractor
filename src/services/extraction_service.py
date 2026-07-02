import pandas as pd
from typing import Dict

from src.ingestion.relatics_client import RelaticsClient
from src.ingestion.xml_parser import parse_xml
from src.processing.extractor import RelaticsExtractor

WORKSPACE_IDS = [
    "210b2918-b359-4892-a23b-bf96ad23d82f"
]
ELEMENT_OPERATION = "dip_elements"
ELEMENT_REPORT_PART = "Elements"
DATA_MODEL_OPERATION = "dip_data_model_2"

def extract_relatics(
    client_id: str,
    client_secret: str,
    environment: str,
) -> Dict[str, pd.DataFrame]:
    """
    Extract all Relatics data and combine tables from all workspaces.

    If multiple workspaces contain the same table, the rows are appended
    into a single DataFrame. The workspace_id column preserves the origin
    of each record.

    Returns:
        Dict[str, pd.DataFrame]
    """

    client = RelaticsClient(
        client_id,
        client_secret,
        environment,
    )

    tables: Dict[str, pd.DataFrame] = {}

    for workspace_id in WORKSPACE_IDS:

        elements_root = client.get_request(
            workspace_id,
            ELEMENT_OPERATION,
        )

        elements_df = parse_xml(
            elements_root,
            ELEMENT_REPORT_PART,
        )

        for _, row in elements_df.iterrows():

            element = row["Element"]
            element_id = row["ElementID"]

            parameters = {
                "ConfigurationOfRef": element_id,
            }

            element_root = client.get_request(
                workspace_id,
                DATA_MODEL_OPERATION,
                parameters,
            )

            extractor = RelaticsExtractor(
                element_root,
                workspace_id,
            )

            extracted_tables = extractor.create_element_tables()

            for table_name, df in extracted_tables.items():

                if table_name in tables:

                    tables[table_name] = pd.concat(
                        [tables[table_name], df],
                        ignore_index=True,
                    )

                else:

                    tables[table_name] = df

    return tables