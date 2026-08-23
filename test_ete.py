from src.processing.transformer import create_element_tables
import pandas as pd

table_dict = {}

file_name = "Element"
path = f"tests/unit/fixtures/test_transformer/{file_name}.parquet"
table_dict[file_name] = pd.read_parquet(path)

file_name = "ElementInstances"
path = f"tests/unit/fixtures/test_transformer/{file_name}.parquet"
table_dict['element_instances'] = pd.read_parquet(path)

file_name = "Properties"
path = f"tests/unit/fixtures/test_transformer/{file_name}.parquet"
table_dict['properties'] = pd.read_parquet(path)

file_name = "PropertyInstances"
path = f"tests/unit/fixtures/test_transformer/{file_name}.parquet"
table_dict['property_instances'] = pd.read_parquet(path)

file_name = "RelationInstances"
path = f"tests/unit/fixtures/test_transformer/{file_name}.parquet"
table_dict['relation_instances'] = pd.read_parquet(path)

file_name = "Relations"
path = f"tests/unit/fixtures/test_transformer/{file_name}.parquet"
table_dict['relations'] = pd.read_parquet(path)

result_dict = create_element_tables(tables=table_dict)

for name,table in result_dict.items():
    table.to_csv(f'output/{name}.csv', index=False)