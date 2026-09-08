import pytest
import copy
import pandas as pd
from pandas.testing import assert_frame_equal
import textwrap

from relatics_extractor.processing.validator import normalize_tables, is_valid_schema

@pytest.fixture
def tables_fixture():
    user = pd.DataFrame({
        "name": ["Oogway", "Cassian"],
        "age": ["530","35"],
        "email": ["master.oogway@kungfu.com", "k.andor@rebel-aliance.net"]
    })
    
    movie = pd.DataFrame({
        "name": ["Kungfu Panda", "Rogue One"],
        "genre": ["Animatie", "Sci-fi"]
    })
    
    return {
        "users": user,
        "movies": movie
    }

def test_valid_normalize_tables_complete(tables_fixture):
    """Test normalize_tables when all schema columns are present in input."""
    test_schema = {
        "users": {
            "name": {"required": True},
            "age": {"required": False, "default": None},
            "email": {"required": True},
        },
        "movies": {
            "name": {"required": True},
            "genre": {"required": False, "default": None},
        },
    }

    normalized_tables = normalize_tables(
        tables=tables_fixture, schema=test_schema
    )

    # 1. Verify table keys match
    assert normalized_tables.keys() == tables_fixture.keys()

    # 2. Compare individual DataFrames with rich diffs & NaN safety
    for table_name in tables_fixture:
        assert_frame_equal(
            normalized_tables[table_name],
            tables_fixture[table_name],
            check_like=True,  # Ignores column order differences if schema order varies
        )

def test_valid_normalize_tables_incomplete():
    """Test normalize_tables populates missing optional columns with defaults."""
    # Arrange: Explicitly define input lacking 'age', 'genre', and 'year'
    input_tables = {
        "users": pd.DataFrame({"name": ["Alice"], "email": ["alice@example.com"]}),
        "movies": pd.DataFrame({"name": ["Inception"]}),
    }

    test_schema = {
        "users": {
            "name": {"required": True},
            "age": {"required": False, "default": None},
            "email": {"required": True},
        },
        "movies": {
            "name": {"required": True},
            "genre": {"required": False, "default": None},
            "year": {"required": False, "default": "Test Value"},
        },
    }

    expected_tables = {
        "users": pd.DataFrame(
            {"name": ["Alice"], "age": [None], "email": ["alice@example.com"]}
        ),
        "movies": pd.DataFrame(
            {"name": ["Inception"], "genre": [None], "year": ["Test Value"]}
        ),
    }

    # Act
    normalized_tables = normalize_tables(tables=input_tables, schema=test_schema)

    # Assert
    for table_name, expected_df in expected_tables.items():
        assert_frame_equal(
            normalized_tables[table_name], expected_df, check_like=True
        )
            
def test_normalize_tables_missing_tables(tables_fixture):
    """Function should raise error when not all tables are present in the input dict."""
    test_schema = {
        "users": {
            "name": {"required": True},
            "age": {"required": False, "default": None},
            "email": {"required": True},
        },
        "movies": {
            "name": {"required": True},
            "genre": {"required": False, "default": None},
            "year": {"required": False, "default": "Test Value"},
        },
        "books": {"name": {"required": True}},
    }

    with pytest.raises(KeyError, match=r"Relatics data does not contain the table books"):
        normalize_tables(tables=tables_fixture, schema=test_schema)

def test_normalize_tables_never_add_required_column(tables_fixture):
    """If a column doesn't exist but is required, the function should never add it."""
    test_schema = {
        "users": {
            "name": {"required": True},
            "age": {"required": False, "default": None},
            "email": {"required": True},
        },
        "movies": {
            "name": {"required": True},
            "genre": {"required": False, "default": None},
            "year": {
                "required": True,
                "default": "Test Value",
            },
        },
    }

    tables_input = {key: df.copy() for key, df in tables_fixture.items()}

    normalized_tables = normalize_tables(tables=tables_input, schema=test_schema)

    assert "year" not in normalized_tables["movies"].columns

    for table_name, expected_df in tables_fixture.items():
        assert_frame_equal(normalized_tables[table_name], expected_df)

def test_normalize_tables_preserves_existing_optional_columns():
    """
    Function should preserve existing values in optional columns rather than 
    overwriting them with schema default values.
    """
    test_schema = {
        "movies": {
            "name": {"required": True},
            "genre": {"required": False, "default": "Default Genre"},
            "year": {"required": False, "default": 2026}
        }
    }

    # DataFrame already contains 'genre' with existing data, but is missing 'year'
    input_df = pd.DataFrame({
        "name": ["Kung Fu Panda", "Rogue One"],
        "genre": ["Animation", "Sci-Fi"]  # Real data that should NOT be overwritten
    })

    tables = {"movies": input_df}

    result = normalize_tables(tables=tables, schema=test_schema)

    # Assert 'genre' kept its original values instead of "Default Genre"
    assert list(result["movies"]["genre"]) == ["Animation", "Sci-Fi"]

    # Assert missing optional column 'year' was added with the default value
    assert list(result["movies"]["year"]) == [2026, 2026]

def test_is_valid_schema_input_valid(tables_fixture):
    """If input fully satisfies the schema, return None (or do nothing)."""
    test_schema = {
        "users": {
            "name": {"required": True},
            "age": {"required": False, "default": None},
            "email": {"required": True},
        },
        "movies": {
            "name": {"required": True},
            "genre": {"required": False, "default": None},
        },
    }

    report = is_valid_schema(tables=tables_fixture, schema=test_schema)

    assert report is None

def test_is_valid_schema_input_missing_columns(tables_fixture):
    """If required columns are missing from any table, raise RuntimeError with a report of missing columns."""
    test_schema = {
        "users": {
            "name": {"required": True},
            "age": {"required": False, "default": None},
            "email": {"required": True},
            "country": {"required": True},  # Changed from False
            "city": {"required": True},  # Changed from False
        },
        "movies": {
            "name": {"required": True},
            "genre": {"required": False, "default": None},
            "year": {"required": True},  # Changed from False
        },
    }

    expected_error_message = textwrap.dedent(
        """
        Schema validation failed. The following required columns are missing:

        - users: country, city
        - movies: year
        """
    ).strip()

    with pytest.raises(RuntimeError) as exc_info:
        is_valid_schema(tables=tables_fixture, schema=test_schema)

    assert str(exc_info.value).strip() == expected_error_message