# from relatics_connector.processing.transformer import create_element_tables
# import pandas as pd

# table_dict = {}

# file_name = "Element"
# path = f"tests/unit/fixtures/test_transformer/{file_name}.parquet"
# table_dict[file_name] = pd.read_parquet(path)

# file_name = "ElementInstances"
# path = f"tests/unit/fixtures/test_transformer/{file_name}.parquet"
# table_dict['element_instances'] = pd.read_parquet(path)

# file_name = "Properties"
# path = f"tests/unit/fixtures/test_transformer/{file_name}.parquet"
# table_dict['properties'] = pd.read_parquet(path)

# file_name = "PropertyInstances"
# path = f"tests/unit/fixtures/test_transformer/{file_name}.parquet"
# table_dict['property_instances'] = pd.read_parquet(path)

# file_name = "RelationInstances"
# path = f"tests/unit/fixtures/test_transformer/{file_name}.parquet"
# table_dict['relation_instances'] = pd.read_parquet(path)

# file_name = "Relations"
# path = f"tests/unit/fixtures/test_transformer/{file_name}.parquet"
# table_dict['relations'] = pd.read_parquet(path)

# result_dict = create_element_tables(tables=table_dict)

# for name,table in result_dict.items():
#     table.to_csv(f'output/{name}.csv', index=False)



import json
import logging
from relatics_connector import RelaticsClient
from relatics_connector.ingestion.xml_parser import parse_xml

logging.basicConfig(level=logging.DEBUG)

with open(
    "configuration.json",
    "r",
    encoding="utf-8"
) as file:
    configuration = json.load(file)

    # set element
elements = {
    "eis": "4dfa1495-7a2f-e911-a2d5-00155d641103"
    # "ontwerpprincipe": "b95be017-7a8d-ec11-b687-001dd8d702bc"
}

element = elements["eis"]

client = RelaticsClient(
    client_id=configuration["client_id"],
    client_secret=configuration["client_secret"],
    environment=configuration["environment"]
)

# configuration of ref for Eis
parameters = {
    "ConfigurationOfRef": element
}

root = client.get_request(
    workspace_id="210b2918-b359-4892-a23b-bf96ad23d82f",
    operation="dip_data_model_3",
    parameters=parameters
)

df = parse_xml(
    root=root,
    report_part='Relations'
)

print(df.shape)

print(df.head())