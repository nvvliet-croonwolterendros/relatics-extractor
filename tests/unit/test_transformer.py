import pytest
import logging
import pandas as pd
from src.processing import transformer

@pytest.fixture
def property_instances():
    return pd.read_parquet('tests/unit/fixtures/test_transformer/PropertyInstances.parquet')

@pytest.fixture
def properties():
    return pd.read_parquet('tests/unit/fixtures/test_transformer/Properties.parquet')

def test_create_property_table_complete_properties():
    """
    Test whether a df with all a column for each property is returned
    in the case all properties exist in the Property column of the input df.
    Also test if each R1InstanceID only appears once.
    """
    data_property_instance = [{'R1Instance': 'AB010', 'R1InstanceID': 'cb14a391-7f6e-ee11-b6a1-001dd8d702bc', 'Property': 'ID', 'PropertyInstance': 'REQ-1233'}, {'R1Instance': 'AB010', 'R1InstanceID': 'cb14a391-7f6e-ee11-b6a1-001dd8d702bc', 'Property': 'ID OG', 'PropertyInstance': 'MAS-0051'}, {'R1Instance': 'AB100', 'R1InstanceID': 'f0ed48e5-7f6e-ee11-b6a1-001dd8d702bc', 'Property': 'ID', 'PropertyInstance': 'REQ-1389'}, {'R1Instance': 'AB100', 'R1InstanceID': 'f0ed48e5-7f6e-ee11-b6a1-001dd8d702bc', 'Property': 'ID OG', 'PropertyInstance': 'MAS-0347'}, {'R1Instance': 'AB110', 'R1InstanceID': '4ab472c1-7f6e-ee11-b6a1-001dd8d702bc', 'Property': 'ID', 'PropertyInstance': 'REQ-1337'}, {'R1Instance': 'AB110', 'R1InstanceID': '4ab472c1-7f6e-ee11-b6a1-001dd8d702bc', 'Property': 'ID OG', 'PropertyInstance': 'MAS-0241'}, {'R1Instance': 'AB200', 'R1InstanceID': '5adf5bd3-7f6e-ee11-b6a1-001dd8d702bc', 'Property': 'ID', 'PropertyInstance': 'REQ-1360'}, {'R1Instance': 'AB200', 'R1InstanceID': '5adf5bd3-7f6e-ee11-b6a1-001dd8d702bc', 'Property': 'ID OG', 'PropertyInstance': 'MAS-0282'}, {'R1Instance': 'AB210', 'R1InstanceID': 'ce4d8da9-7f6e-ee11-b6a1-001dd8d702bc', 'Property': 'ID', 'PropertyInstance': 'REQ-1281'}, {'R1Instance': 'AB210', 'R1InstanceID': 'ce4d8da9-7f6e-ee11-b6a1-001dd8d702bc', 'Property': 'ID OG', 'PropertyInstance': 'MAS-0145'}]
    df_property_instance = pd.DataFrame(data_property_instance)

    data_property = [{'Property': 'ID', 'PropertyID': 'fbe697dc-2a31-e911-a2d5-00155d641103'}, {'Property': 'ID OG', 'PropertyID': '03e797dc-2a31-e911-a2d5-00155d641103'}]
    df_property = pd.DataFrame(data_property)

    all_properties = df_property["Property"].apply(transformer._normalize_value).dropna().unique().tolist()
    transformed_table = transformer._create_property_table(properties_df=df_property, property_instances_df=df_property_instance)

    assert set(transformed_table.columns) == set(all_properties)
    assert len(transformed_table.columns.tolist()) == len(all_properties) # Order is irrelevant so a == operator will yield unwanted result. The set + len will ensure the list is the same
    assert 'R1InstanceID' not in transformed_table.columns.tolist()
    assert transformed_table.index.unique().shape[0] == transformed_table.index.shape[0]
    assert transformed_table.index.name == "R1InstanceID"
    
def test_create_property_table_incomplete_properties(properties, property_instances):
    """
    Test whether a df with all a column for each property is returned
    in the case not all properties exist in the Property column of the input df.
    Also test if each R1InstanceID only appears once.
    """
    all_properties = properties["Property"].apply(transformer._normalize_value).dropna().unique().tolist()
    transformed_table = transformer._create_property_table(properties_df=properties, property_instances_df=property_instances)

    assert set(transformed_table.columns) == set(all_properties)
    assert len(transformed_table.columns.tolist()) == len(all_properties) # Order is irrelevant so a == operator will yield unwanted result. The set + len will ensure the list is the same
    assert 'R1InstanceID' not in transformed_table.columns.tolist()
    assert transformed_table.index.unique().shape[0] == transformed_table.index.shape[0]
    assert transformed_table.index.name == "R1InstanceID"

def test_create_property_table_no_properties(caplog):
    """
    Test whether the input dataframe is empty or contains no properties.
    Should give an info logging and return an empty df.
    """
    empty_properties = pd.DataFrame({'Property': {}, 'PropertyID': {}})
    empty_propertyelements = pd.DataFrame({'R1Instance': {}, 'R1InstanceID': {}, 'Property': {}, 'PropertyInstance': {}})

    transformed_table = transformer._create_property_table(properties_df=empty_properties, property_instances_df=empty_propertyelements)

    assert transformed_table.index.shape[0] == 0
    assert transformed_table.index.name == 'R1InstanceID'
    assert "No properties found in properties report part." in caplog.text
    assert "No property instanes found in property instances report part." in caplog.text

def test_create_property_table_no_propertyinstances(caplog):
    """
    Test whether the input dataframe is empty or contains no property instances while th eproperty dataframe is not empty.
    Should give an info logging and return an empty df.
    """
    empty_properties = pd.DataFrame({'Property': ["ID"], 'PropertyID': ["123-456"]})
    empty_propertyelements = pd.DataFrame({'R1Instance': {}, 'R1InstanceID': {}, 'Property': {}, 'PropertyInstance': {}})

    transformed_table = transformer._create_property_table(properties_df=empty_properties, property_instances_df=empty_propertyelements)

    assert transformed_table.index.shape[0] == 0
    assert transformed_table.index.name == 'R1InstanceID'
    assert set(transformed_table.columns.tolist()) == set(['id'])
    assert "No property instanes found in property instances report part." in caplog.text

def test_create_property_table_pivot_fails(caplog):
    """
    Test wether an exception is thrown and logging happens in case a diplicate R1InstanceID is present
    """
    properties = pd.DataFrame({'Property': ["ID"], 'PropertyID': ["123-456"]})
    propertyelements = pd.DataFrame({'R1Instance': ["Actie1", "Actie2"], 'R1InstanceID': ["1", "1"], 'Property': ["ID", "ID"], 'PropertyInstance': ["ID1", "ID2"]})

    with pytest.raises(ValueError):
        transformer._create_property_table(properties_df=properties, property_instances_df=propertyelements)
    assert "Failed to pivot table, likely due to duplicates property names." in caplog.text

def test_create_property_table_drops_undeclared_properties():
    properties = pd.DataFrame({'Property': ["ID"], 'PropertyID': ["1"]})
    property_instances = pd.DataFrame({
        'R1Instance': ["A", "A"],
        'R1InstanceID': ["x", "x"],
        'Property': ["ID", "Undeclared"],
        'PropertyInstance': ["V1", "V2"],
    })
    result = transformer._create_property_table(properties_df=properties, property_instances_df=property_instances)
    assert 'undeclared' not in result.columns.tolist()
    assert set(result.columns.tolist()) == {"id"}
 
def test_create_property_table_does_not_mutate_input():
    properties = pd.DataFrame({'Property': ["ID"], 'PropertyID': ["1"]})
    property_instances = pd.DataFrame({
        'R1Instance': ["A"],
        'R1InstanceID': ["x"],
        'Property': ["ID"],
        'PropertyInstance': ["V1"],
    })
    original_property_values = property_instances['Property'].copy()
    transformer._create_property_table(properties_df=properties, property_instances_df=property_instances)
    pd.testing.assert_series_equal(property_instances['Property'], original_property_values)
    
def test_create_property_elements_table_complete_properties():
    """
    Test whether a df with a column for each property R2Element is returned
    for all R2Elements that exist in the Property column of the relations df.
    In case all Relations exist in the RelationInstances df.
    Also test if the columns are filled in with R2Instance.
    """
    relations_data = {'Relation': {28: 'Heeft property', 29: 'Heeft property', 30: 'Heeft property', 31: 'Heeft property', 32: 'Heeft property'}, 'Cardinality': {28: '0:1', 29: '0:1', 30: '0:1', 31: '0:1', 32: '0:1'}, 'RelationID': {28: '108e6382-9747-f011-b6c2-001dd8d702bc', 29: '25e40114-69d5-ea11-a2f0-00155d641104', 30: '44b531ee-9aae-ec11-b688-001dd8d702bf', 31: '458f8a61-75f5-e911-a2e5-00155d641104', 32: '488f8a61-75f5-e911-a2e5-00155d641104'}, 'R2Element': {28: 'SRA Thema', 29: 'SMART-analyse', 30: 'Type', 31: 'Geldig tot en met', 32: 'Geldig vanaf'}, 'R2ElementID': {28: 'fe4a0331-9547-f011-b6c2-001dd8d702bc', 29: '9dc8ef06-69d5-ea11-a2f0-00155d641104', 30: 'fa7e60d4-9aae-ec11-b688-001dd8d702bf', 31: '2ecb4ecc-d1f4-e911-a2e5-00155d641104', 32: '8f4ecdda-d1f4-e911-a2e5-00155d641104'}}
    
    
def test_create_property_elements_table_incomplete_properties():
    """
    Test whether a df with a column for each property R2Element is returned
    for all R2Elements that exist in the Property column of the relations df.
    In case not all Relations exist in the RelationInstances df.
    Also test if the columns are filled with R2Instance for the existing relations and empty for not existing relations.
    """

def test_create_property_elements_table_empty_properties():
    """
    Test whether a df with a column for each property R2Element is returned
    for all R2Elements that exist in the Property column of the relations df.
    In case no Relations exist in the RelationInstances df.
    Also test if the columns are empty.
    """
    
def test_create_property_elements_table_only_uses_to_one():
    """
    Test whether the function only uses the relations with a :1 cardinality.
    :1 relation includes 0/n/1:1 or 0/n/1:1|1.
    This filters out the :1|n or :n|1 possibility.
    """
    
def test_create_property_elements_table_only_uses_property_elements():
    """
    Test whether the function only uses the relations with name 'Heeft property'.
    Also throw an exception if the combination Relation + R2InstanceID is not unique
    i.e. 'Heeft' relation with 'Status' element twice.
    """
    
def test_create_property_elements_table_false_cardinality_to_one():
    """
    Test whether the function give an error when the a :1 cardinality is not 
    truly a :1 cardinality
    """

def test_create_to_one_relations_table_complete_properties():
    """
    Test whether a df with a column for each property R2Element is returned
    for all R2Elements that exist in the Property column of the relations df.
    In case all Relations exist in the RelationInstances df.
    Also test if the columns are filled in with R2InstanceID and the column name is the R2Element + _guid suffix.
    """
    
def test_create_to_one_relations_table_incomplete_properties():
    """
    Test whether a df with a column for each property R2Element is returned
    for all R2Elements that exist in the Property column of the relations df.
    In case not all Relations exist in the RelationInstances df.
    Also test if the columns are filled with R2InstanceID for the existing relations and empty for not existing relations
    and the column name is the R2Element + _guid suffix.
    """

def test_create_to_one_relations_table_empty_properties():
    """
    Test whether a df with a column for each property R2Element is returned
    for all R2Elements that exist in the Property column of the relations df.
    In case no Relations exist in the RelationInstances df.
    Also test if the columns are empty and the column name is the R2Element + _guid suffix.
    """


# Bij link table toevoegen :1 relation icm heeft property relation name