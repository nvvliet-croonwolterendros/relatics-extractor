import pytest
import copy
import pandas as pd

from src.processing.validator import normalize_tables, is_valid_schema

@pytest.fixture
def tables_fixture():
    user_table = pd.DataFrame({
        "name": ["Oogway", "Cassian"],
        "age": ["530","35"],
        "email": ["master.oogway@kungfu.com", "k.andor@rebel-aliance.net"]
    })
    
    movie_table = pd.DataFrame({
        "name": ["Kungfu Panda", "Rogue One"],
        "genre": ["Animatie", "Sci-fi"]
    })
    
    return {
        "users": user_table,
        "movies": movie_table
    }

def test_valid_normalize_tables_complete(tables_fixture):
    """
    Test normalize_tables function in situation where
    all columns are present in the input tables.
    """
    test_schema = {
        "users": {
            "name": {"required": True},
            "age": {"required": False, "default": None},
            "email": {"required": True}
        },
        "movies": {
            "name": {"required": True},
            "genre": {"required": False, "default": None}
        }
    }
    
    normalized_tables = normalize_tables(
        tables=tables_fixture,
        schema=test_schema
    )
    
    assert normalized_tables == tables_fixture

def test_valid_normalize_tables_incomplete(tables_fixture):
    """
    Test normalize_tables function in situation where
    not all columns are present in the input tables.
    """
    test_schema = {
        "users": {
            "name": {"required": True},
            "age": {"required": False, "default": None},
            "email": {"required": True}
        },
        "movies": {
            "name": {"required": True},
            "genre": {"required": False, "default": None},
            "year": {"required": False, "default": "Test Value"}
        }
    }
    
    normalized_tables = normalize_tables(
        tables=tables_fixture,
        schema=test_schema
    )
    
    updated_fixture = copy.deepcopy(tables_fixture)
    updated_fixture["movies"]["year"] = "Test Value"
    
    for k, table in normalized_tables.items():
        assert (table.columns == updated_fixture[k].columns).all()
        
        for column in table.columns:
            assert (table[column] == updated_fixture[k][column]).all()
            
def test_normalize_tables_missing_tables():
    """
    Function should raise error when not all tables are present in the input dict.
    """
    
def test_normalize_tables_never_add_required_column():
    """
    If a column doesn't exist but is required, the function should never add it.
    """
    
def test_is_valid_schema_input_valid(tables_fixture):
    """
    Als input volledig voeldoet -> doe niks
    """
    test_schema = {
        "users": {
            "name": {"required": True},
            "age": {"required": False, "default": None},
            "email": {"required": True}
        },
        "movies": {
            "name": {"required": True},
            "genre": {"required": False, "default": None}
        }
    }

    report = is_valid_schema(tables=tables_fixture, schema=test_schema)
    
    assert report == None

def test_is_valid_schema_input_missing_columns():
    """
    Als column mist bij tenminste een van de tabelen raise error.
    Genereer rapport (dict) met tabel naam als key en lijst missend kolommen als waarde
    """
    
