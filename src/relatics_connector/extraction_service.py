from typing import Dict, Tuple
import logging
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from relatics_connector.ingestion.relatics_client import RelaticsClient
from relatics_connector.ingestion.xml_parser import parse_xml
from relatics_connector.processing.validator import normalize_tables, is_valid_schema
from relatics_connector.processing.schema import SCHEMA
from relatics_connector.processing.transformer import create_element_tables

logger = logging.getLogger(__name__)

class Extractor():
    """Extractor class that handles the entire ETL pipeline for relatics extraction.

    This class handles the Relatics API call, parsing of the tables into multiple pandas dataframes and finally the transformation into tables.
    The tables this extractor returns are made to be able to use in databases, the tables are all deduplicated.

    Args:
        client_id: The Client ID from Relatics' OAUTH implementation.
        client_secret: The Client secret from Relatics' OAUTH implementation.
        environment: the environment where the relatics workspaces are hosted -> environment.relaticsonline.com
    """
    def __init__(self, client_id: str, client_secret: str, environment: str) -> None:
        self.clientid = client_id
        self.clientsecret = client_secret
        self.environment = environment

        self.client = RelaticsClient(client_id=self.clientid,
                                client_secret=self.clientsecret,
                                environment=self.environment)

    def run_etl_fast(self, workspaces: Tuple[str, ...], element_operation: str, datamodel_operation: str, element_report_part: str = "Elements") -> Dict[str, pd.DataFrame]:
        """Main entrypoint for ETL process.

        Executes the ETL process in the right order for a list of workspaces.
        Uses multithreading to speed up the process.
        The ETL process wil first validate the input data to match a predefined schema, if columns are missing, they are silently added.
        After the validation is done, the data is transformed so that each element will get its :1 relation in the element table and :n relation in a link table.
        The workspaceID is added to each table, and after the transformation is completed a final dict is made if a table is present the workspace data is appended otherwise a new key is made with a pd.DataFrame as value.

        Args:
            workspaces (list): A list of workspace id's to iterate over.
            element_operation (str): The Relatics webservice operation name to retrieve the elements with their ConfiguratioOfRef to extract.
            datamodel_operation (str): The Relatics webservice operation name to retrieve the relatics datamodel.
            element_report_part (str): The Report part containing the Elements with ConfigurationOfRef. The default should be good if the documentation is followed. Default: 'Element'

        Returns:
            tables: A dictionary with table names as keys and the corresponding pd.DataFrame as value.
        """

        tables = {}

        for workspace_id in workspaces:
            logger.info(f"Start processing workspaceID: {workspace_id}")
            elements_to_extract_root = self.client.get_request(workspace_id=workspace_id,
                                                          operation=element_operation)

            elements_to_extract_df = parse_xml(root=elements_to_extract_root,
                                               report_part=element_report_part)

            with ThreadPoolExecutor() as executor:
                futures = [
                    executor.submit(self.process_element,
                                    elementid=row["ElementID"],
                                    elementname=row['Element'],
                                    client=self.client,
                                    workspaceid=workspace_id,
                                    schema=SCHEMA,
                                    datamodel_operation=datamodel_operation
                    )
                    for _, row in elements_to_extract_df.iterrows()
                ]
                for future in as_completed(futures):
                    try:
                        element_tables_result = future.result()
                    except Exception:
                        logger.exception("Failed to process element")
                        continue
                        # raise

                    for table_name, df in element_tables_result.items():
                        if table_name in tables:
                            tables[table_name] = pd.concat([tables[table_name], df], ignore_index=True)
                        else:
                            tables[table_name] = df

        return tables

    def run_etl_slow(self, workspaces: Tuple[str, ...], element_operation: str, datamodel_operation: str, element_report_part: str = "Elements") -> Dict[str, pd.DataFrame]:
        """Main entrypoint for ETL process.

        Executes the ETL process in the right order for a list of workspaces.
        The ETL process wil first validate the input data to match a predefined schema, if columns are missing, they are silently added.
        After the validation is done, the data is transformed so that each element will get its :1 relation in the element table and :n relation in a link table.
        The workspaceID is added to each table, and after the transformation is completed a final dict is made if a table is present the workspace data is appended otherwise a new key is made with a pd.DataFrame as value.

        Args:
            workspaces (list): A list of workspace id's to iterate over.
            element_operation (str): The Relatics webservice operation name to retrieve the elements with their ConfiguratioOfRef to extract.
            datamodel_operation (str): The Relatics webservice operation name to retrieve the relatics datamodel.
            element_report_part (str): The Report part containing the Elements with ConfigurationOfRef. The default should be good if the documentation is followed. Default: 'Element'

        Returns:
            Dict[str, pd.DataFrame]: A dictionary with table names as keys and the corresponding pd.DataFrame as value.
        """

        tables = {}
        self.failed_elements = []

        for workspace_id in workspaces:
            logger.info(f"Start processing workspaceID: {workspace_id}")
            elements_to_extract_root = self.client.get_request(workspace_id=workspace_id,
                                                        operation=element_operation)

            elements_to_extract_df = parse_xml(root=elements_to_extract_root,
                                            report_part=element_report_part)

            for _, row in elements_to_extract_df.iterrows():
                try:
                    logger.info(f"\n==========================================\n Start processing element: {row['Element']}")
                    element_tables_result = self.process_element(
                        elementid=row["ElementID"],
                        elementname=row['Element'],
                        client=self.client,
                        workspaceid=workspace_id,
                        schema=SCHEMA,
                        datamodel_operation=datamodel_operation
                    )
                except Exception:
                    logger.exception(f"Failed to process element: {row['Element']}. skipping.")
                    self.failed_elements.append(row['Element'])
                    continue
                    # raise # Normally this is a raise just for now lets keep going and just continue

                for table_name, df in element_tables_result.items():
                    if table_name in tables:
                        tables[table_name] = pd.concat([tables[table_name], df], ignore_index=True)
                    else:
                        tables[table_name] = df
        if self.failed_elements:
            logger.error(f'There are {len(self.failed_elements)} failed elements namely: {self.failed_elements}')
        return tables

    @staticmethod
    def process_element(elementid: str, elementname:str, client: RelaticsClient, workspaceid: str, datamodel_operation: str, schema: Dict[str, Dict]=SCHEMA,
                        report_parts: Tuple = ('ElementInstances', 'Properties', 'PropertyInstances', 'Relations', 'RelationInstances')) -> Dict[str, pd.DataFrame]:
        """Processes a Relatics element with its first order relations and properties.

        This function takes the ConfigurationOfRef of an element and does a relatics API call to retrieve all the element information, 
        verifies the schema and transforms the tables to ensure all :1 relations are in the same table as the element and all :n relation are in a link table.
        Note: the main reason this function is not just a for loop is to enable the use of the ThreadPoolExecutor. As most of the time this function sits idle waiting for IO operations.

        Args:
            elementid (str): The ConfigurationOfRef of the element.
            client (RelaticsClient): RelaticsClient with valid credentials.
            workspaceid (str): The workspaceid of the workspace used for extraction, also used to add a workspaceid column for multi workspace extractions.
            datamodel_operation (str): The Relatics webservice operation name used for the datamodel, see documentation for specifics.
            schema (Dict[str, Dict]): The expected schema returned by the datamodel webservice. Used to add missing columns the Relatics webservice might drop.
            report_parts (Tuple): A tuple of the report parts required for transformation. Tuple is mainly present for documentation purposes as the create_element_tables function requries these names.

        Returns:
            transformed_tables: A Dictionary with pandas dataframes as values. The keys are raw_relatics__{R1Element}_{R2Element} for link tables and raw_relatics__{R1Element} for element tables.
        """
        logger.info(f"Start processing Element {elementid}")

        # Get data and parse it for further use.
        parameters = {"ConfigurationOfRef": elementid}
        element_data = client.get_request(workspace_id=workspaceid,
                                          operation=datamodel_operation,
                                          parameters=parameters)
        tables_parsed = {report_part: parse_xml(element_data, report_part) for report_part in report_parts}

        # Check validity, will raise error if not valid.
        is_valid_schema(tables=tables_parsed, schema=schema) # Will raise error if invalid
        normalized_tables = normalize_tables(tables=tables_parsed, schema=schema)

        # Transform the dict of raw dataframes to a dict of transformed dataframes, keys will be sanatized sql table names with their corresponding df as value.
        # Also add the current workspaceid as a column.
        transformed_tables = create_element_tables(tables=normalized_tables, r1_element=elementname)
        for table in transformed_tables.values():
            table['workspaceid'] = workspaceid

        return transformed_tables
