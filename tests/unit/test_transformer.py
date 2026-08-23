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

@pytest.fixture
def relations():
    return pd.read_parquet("tests/unit/fixtures/test_transformer/Relations.parquet")

@pytest.fixture
def relation_instances():
    return pd.read_parquet("tests/unit/fixtures/test_transformer/RelationsInstances.parquet")

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
    when all relations exist in relation_instances_df.
    """
    relations_df = pd.DataFrame({
        'Relation': ['Heeft property', 'Heeft property'],
        'Cardinality': ['0:1', '0:1'],
        'R2Element': ['SRA status', 'Geaccepteerd door ON']
    })
    
    relations_instances_df = pd.DataFrame({
        'R1InstanceID': ['id_1', 'id_1'],
        'R2Element': ['SRA status', 'Geaccepteerd door ON'],
        'R2Instance': ['Overeengekomen OG/ON', 'Niet behandeld']
    })

    result = transformer._create_property_elements_table(relations_df, relations_instances_df)

    assert list(result.columns) == ['SRA status', 'Geaccepteerd door ON']
    assert len(result) == 1
    assert result.loc['id_1', 'SRA status'] == 'Overeengekomen OG/ON'
    assert result.loc['id_1', 'Geaccepteerd door ON'] == 'Niet behandeld'


def test_create_property_elements_table_incomplete_properties():
    """
    Test whether all property columns are present even if some relations
    are missing from relation_instances_df, filling missing cells with NaN.
    """
    relations_df = pd.DataFrame({
        'Relation': ['Heeft property', 'Heeft property'],
        'Cardinality': ['0:1', '0:1'],
        'R2Element': ['SRA status', 'SMART-analyse OG']
    })
    
    # Missing 'SMART-analyse OG' in instance data
    relations_instances_df = pd.DataFrame({
        'R1InstanceID': ['id_1'],
        'R2Element': ['SRA status'],
        'R2Instance': ['Overeengekomen OG/ON']
    })

    result = transformer._create_property_elements_table(relations_df, relations_instances_df)

    assert list(result.columns) == ['SRA status', 'SMART-analyse OG']
    assert result.loc['id_1', 'SRA status'] == 'Overeengekomen OG/ON'
    assert pd.isna(result.loc['id_1', 'SMART-analyse OG'])


def test_create_property_elements_table_empty_properties():
    """
    Test whether empty DataFrame with the expected columns is returned
    when no instances match the relations.
    """
    relations_df = pd.DataFrame({
        'Relation': ['Heeft property', 'Heeft property'],
        'Cardinality': ['0:1', '0:1'],
        'R2Element': ['SRA status', 'SMART-analyse OG']
    })
    
    relations_instances_df = pd.DataFrame(columns=['R1InstanceID', 'R2Element', 'R2Instance'])

    result = transformer._create_property_elements_table(relations_df, relations_instances_df)

    assert list(result.columns) == ['SRA status', 'SMART-analyse OG']
    assert len(result) == 0


def test_create_property_elements_table_only_uses_to_one():
    """
    Test whether relations with non-to-one cardinality (e.g., 0:n) are excluded.
    Also test the piped cardinality patterns: '0:1|1' should count as to-one,
    while '0:1|n' should not.
    """
    relations_df = pd.DataFrame({
        'Relation': ['Heeft property', 'Heeft property', 'Heeft property', 'Heeft property'],
        'Cardinality': ['0:1', '0:n', '0:1|1', '0:1|n'],
        'R2Element': ['SRA status', 'Eis', 'SMART-analyse OG', 'Geldig tot en met']
    })

    relations_instances_df = pd.DataFrame({
        'R1InstanceID': ['id_1', 'id_1', 'id_1', 'id_1'],
        'R2Element': ['SRA status', 'Eis', 'SMART-analyse OG', 'Geldig tot en met'],
        'R2Instance': ['Overeengekomen OG/ON', 'B-AB500', 'Analyse Y', 'Datum Z']
    })

    result = transformer._create_property_elements_table(relations_df, relations_instances_df)

    assert 'SRA status' in result.columns
    assert 'Eis' not in result.columns
    assert 'SMART-analyse OG' in result.columns
    assert 'Geldig tot en met' not in result.columns


def test_create_property_elements_table_only_uses_property_elements():
    """
    Test whether non-'Heeft property' relations are excluded, and throws
    a ValueError if duplicate R1InstanceID + R2Element pairs exist.
    """
    relations_df = pd.DataFrame({
        'Relation': ['Heeft property', '[WEG] Heeft'],
        'Cardinality': ['0:1', '0:1'],
        'R2Element': ['SRA status', 'Commentaar OG']
    })
    
    relations_instances_df = pd.DataFrame({
        'R1InstanceID': ['id_1', 'id_1'],
        'R2Element': ['SRA status', 'Commentaar OG'],
        'R2Instance': ['Overeengekomen OG/ON', 'Some comment']
    })

    result = transformer._create_property_elements_table(relations_df, relations_instances_df)
    
    assert 'SRA status' in result.columns
    assert 'Commentaar OG' not in result.columns

    # Test Exception trigger on duplicate R1InstanceID + R2Element
    duplicate_instances_df = pd.DataFrame({
        'R1InstanceID': ['id_1', 'id_1'],
        'R2Element': ['SRA status', 'SRA status'],
        'R2Instance': ['Val1', 'Val2']
    })

    with pytest.raises(ValueError):
        transformer._create_property_elements_table(relations_df, duplicate_instances_df)

# Start of AI generated tests:
def test_create_property_elements_table_multiple_instances():
    """
    Test that values are correctly aligned per R1InstanceID when multiple
    entities are present, not just per column.
    """
    relations_df = pd.DataFrame({
        'Relation': ['Heeft property', 'Heeft property'],
        'Cardinality': ['0:1', '0:1'],
        'R2Element': ['SRA status', 'Geaccepteerd door ON']
    })

    relations_instances_df = pd.DataFrame({
        'R1InstanceID': ['id_1', 'id_1', 'id_2', 'id_2'],
        'R2Element': ['SRA status', 'Geaccepteerd door ON', 'SRA status', 'Geaccepteerd door ON'],
        'R2Instance': ['Overeengekomen OG/ON', 'Niet behandeld', 'Afgewezen', 'Behandeld']
    })

    result = transformer._create_property_elements_table(relations_df, relations_instances_df)

    assert len(result) == 2
    assert result.loc['id_1', 'SRA status'] == 'Overeengekomen OG/ON'
    assert result.loc['id_1', 'Geaccepteerd door ON'] == 'Niet behandeld'
    assert result.loc['id_2', 'SRA status'] == 'Afgewezen'
    assert result.loc['id_2', 'Geaccepteerd door ON'] == 'Behandeld'

def test_create_property_elements_table_column_order_follows_relations_df():
    """
    Test that output column order matches the order of R2Element in
    relations_df, even when relations_instances_df rows are in a
    different order.
    """
    relations_df = pd.DataFrame({
        'Relation': ['Heeft property', 'Heeft property', 'Heeft property'],
        'Cardinality': ['0:1', '0:1', '0:1'],
        'R2Element': ['SRA status', 'Type', 'SMART-analyse OG']
    })

    # Instance rows deliberately out of order relative to relations_df
    relations_instances_df = pd.DataFrame({
        'R1InstanceID': ['id_1', 'id_1', 'id_1'],
        'R2Element': ['SMART-analyse OG', 'SRA status', 'Type'],
        'R2Instance': ['Analyse Y', 'Overeengekomen OG/ON', 'Type X']
    })

    result = transformer._create_property_elements_table(relations_df, relations_instances_df)

    assert list(result.columns) == ['SRA status', 'Type', 'SMART-analyse OG']

def test_create_property_elements_table_clears_columns_axis_name():
    """
    Test that the resulting columns Index has no name, since pivot()
    otherwise leaves the columns axis named 'R2Element'.
    """
    relations_df = pd.DataFrame({
        'Relation': ['Heeft property'],
        'Cardinality': ['0:1'],
        'R2Element': ['SRA status']
    })

    relations_instances_df = pd.DataFrame({
        'R1InstanceID': ['id_1'],
        'R2Element': ['SRA status'],
        'R2Instance': ['Overeengekomen OG/ON']
    })

    result = transformer._create_property_elements_table(relations_df, relations_instances_df)

    assert result.columns.name is None

# Einde AI gen tests
    
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

def test_create_to_one_relations_table_duplicateR2_Elements():
    """
    Test whether the function correctly handles multiple R2Elements with the same name.
    This can heppen if for example 'Rol' is used in multiple ways. The relation name should be prefixing the R2 element.
    """

# Bij link table toevoegen :1 relation icm heeft property relation name
    
def test_create_link_tables_only_to_many_cardinality():
    """
    Test whether link tables are created for every :n relation
    and only for relations with cardinality :n
    and are named according to raw_relatics__{R1Element}_{R2Element}
    and the columns are named according to:
    {R1Element}_guid for fist column, {R2Element}_guid for second column
    :n relation includes the :1|n or :n|1 possibility.
    """
    relations_df = pd.DataFrame({
        'Relation': ['bevat_s', 'heeft', 'heeft', 'heeft'],
        'Cardinality': ['0:n', '0:1', '0:n|1', '0:1|n'],
        'RelationID': [
            '1731cf9e-0239-e911-a2d7-00155d641104',
            'e1ecc874-0759-ee11-b6a0-001dd8d702bf',
            '1a160899-b699-ea11-a2ec-00155d641103',
            '73d4bcc7-f731-e911-a2d5-00155d641103',
        ],
        'R2Element': [
            'bevat_s_eis',
            'honorering',
            'toelichting',
            'commentaar'
        ],
        'R2ElementID': [
            '4dfa1495-7a2f-e911-a2d5-00155d641103',
            '2d821dd9-0259-ee11-b6a0-001dd8d702bf',
            'ae962581-b699-ea11-a2ec-00155d641103',
            '275a8d8a-852f-e911-a2d5-00155d641103'
        ]
    })
    
    relation_instances_df = pd.DataFrame({
        'R1Element': ['eis', 'eis', 'eis', 'eis'],
        'R1Instance': ['AB010', 'AB010', 'AB010', 'AB010'],
        'R1InstanceID': [
            'cb14a391-7f6e-ee11-b6a1-001dd8d702bc',
            'cb14a391-7f6e-ee11-b6a1-001dd8d702bc',
            'cb14a391-7f6e-ee11-b6a1-001dd8d702bc',
            'cb14a391-7f6e-ee11-b6a1-001dd8d702bc'
        ],
        'RelationInstanceID': [
            '25de6afe-149f-ee11-b6a6-001dd8d702bf',
            '41766704-159f-ee11-b6a6-001dd8d702bf',
            '6559790b-ab7f-ee11-b6a5-001dd8d702bf',
            '77be6fc2-34ce-ee11-b6a8-001dd8d702bf'
        ],
        'Cardinality': ['0:n', '0:1', '0:n|1', '0:1|n'],
        'R2Element': [
            'bevat_s_eis',
            'honorering',
            'toelichting',
            'commentaar'
        ],
        'R2Instance': ['AB200','B-AB300','Contractmanager','ME-Eis-Bedrijfsproces'],
        'R2InstanceID': [
            '5adf5bd3-7f6e-ee11-b6a1-001dd8d702bc',
            '1ed53ef1-7f6e-ee11-b6a1-001dd8d702bc',
            '5aa573e8-e961-ee11-b6a0-001dd8d702bf',
            '63be6fc2-34ce-ee11-b6a8-001dd8d702bf'
        ]
    }) 
    
    expected_output = {
        "raw_relatics__eis_bevat_s_eis": pd.DataFrame({
            "eis_guid": ['cb14a391-7f6e-ee11-b6a1-001dd8d702bc'],
            "bevat_s_eis_guid": ['5adf5bd3-7f6e-ee11-b6a1-001dd8d702bc']    
        }),
        "raw_relatics__eis_toelichting": pd.DataFrame({
            "eis_guid": ['cb14a391-7f6e-ee11-b6a1-001dd8d702bc'],
            "toelichting_guid": ['5aa573e8-e961-ee11-b6a0-001dd8d702bf']
        }),
        "raw_relatics__eis_commentaar": pd.DataFrame({
            "eis_guid": ['cb14a391-7f6e-ee11-b6a1-001dd8d702bc'],
            "commentaar_guid": ['63be6fc2-34ce-ee11-b6a8-001dd8d702bf']
        }),
    }
    
    output = transformer._create_link_tables(
        r1_element="eis",
        relations_df=relations_df,
        relations_instances_df=relation_instances_df
    )
    
    assert output.keys() == expected_output.keys()
    
    for key in output:
        pd.testing.assert_frame_equal(
            output[key],
            expected_output[key]
        )

def test_create_link_tables_incomplete_relation_instances():
    """
    Test whether a link table is created for a :n relation
    even if there exist no relation instance
    """
    relations_df = pd.DataFrame({
        'Relation': ['bevat_s'],
        'Cardinality': ['0:n'],
        'RelationID': [
            '1731cf9e-0239-e911-a2d7-00155d641104'
        ],
        'R2Element': ['bevat_s_eis'],
        'R2ElementID': [
            '4dfa1495-7a2f-e911-a2d5-00155d641103'
        ]
    })
    
    relation_instances_df = pd.DataFrame({
        'R1Element': [],
        'R1Instance': [],
        'R1InstanceID': [],
        'RelationInstanceID': [],
        'Cardinality': [],
        'R2Element': [],
        'R2Instance': [],
        'R2InstanceID': []
    }) 
    
    expected_output = {
        "raw_relatics__eis_bevat_s_eis": pd.DataFrame({
            "eis_guid": [],
            "bevat_s_eis_guid": []    
        })
    }
    
    output = transformer._create_link_tables(
        r1_element="eis",
        relations_df=relations_df,
        relations_instances_df=relation_instances_df
    )
    
    assert output.keys() == expected_output.keys()

    for key in output:
        pd.testing.assert_frame_equal(
            output[key],
            expected_output[key]
        )
    
def test_transform_relations_table_returns_sql_safe_only():
    """
    Test whether all R2Element names returned are sql safe.
    """
    import re
    relations_df = pd.DataFrame()
    relations_instances_df = pd.DataFrame()

    pattern = r"^[a-zA-Z_][a-zA-Z0-9_]{0,127}$"
    relations_df_safe = relations_df["my_column"].str.match(pattern).all()

    assert relations_df_safe == True



def test_transform_relations_table_no_duplicate_names():
    """
    Test whether R2Element    
    """    

def test_transform_relations_table_duplicate_names():
    """
    Test whether duplicate R2Element are renamed to {Relation}_{R2Element}    
    """    
    
def test_transform_relations_table_duplicate_name_and_relation():
    """
    Test whether a error is raised when the Relations table contains a
    duplicate R2Element and Relation combination
    """
    
def test_transform_relations_table_no_children():
    """
    Test whether the output contains the same R2Elements as the input in 
    case no children Elements are present
    """
    
def test_tranform_relations_table_children():
    """
    Test whether the output contains the Children R2Elements instead of the
    R2Elements in case children Elements are present
    """
    

