from src.ingestion.relatics_client import RelaticsClient
from src.ingestion.xml_parser import parse_xml
from src.processing.extractor import RelaticsExtractor

WORKSPACE_IDS = [
    "210b2918-b359-4892-a23b-bf96ad23d82f"
]
ELEMENT_OPERATION = "dip_elements"
ELEMENT_REPORT_PART = "Elements"
DATA_MODEL_OPERATION = "dip_data_model_2"

class RelaticsExtractorService():
    
    def __init__(
        self, 
        client_id: str,
        client_secret: str,
        environment: str
    ) -> None:
        self.client = RelaticsClient(client_id,client_secret,environment)

    def extract_relatics(self): 
        tables = {}
        
        for workspace_id in WORKSPACE_IDS:
            elements_root = self.client.get_request(workspace_id,ELEMENT_OPERATION)
            elements_df = parse_xml(elements_root,ELEMENT_REPORT_PART)
            
            for idx in elements_df.index:             
                element = elements_df["Element"][idx]
                element_id = elements_df["ElementID"][idx]
                parameters = {
                    "ConfigurationOfRef": element_id
                }
                
                print(f"retrieving data for {element}")
                
                element_root = self.client.get_request(
                    workspace_id,
                    DATA_MODEL_OPERATION,
                    parameters
                )
                
                extractor = RelaticsExtractor(
                    element_root,
                    workspace_id 
                )
                
                tables.update(extractor.create_element_tables())
                
        return tables