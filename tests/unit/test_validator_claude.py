import pytest
import pandas as pd
from pandas.testing import assert_frame_equal
import textwrap

from src.processing.validator import normalize_tables, is_valid_schema


# ---------------------------------------------------------------------------
# normalize_tables — edge cases
# ---------------------------------------------------------------------------

def test_normalize_tables_empty_input():
    """Empty tables + empty schema should return an empty dict, not raise."""
    result = normalize_tables(tables={}, schema={})
    assert result == {}


def test_normalize_tables_schema_table_with_no_columns():
    """
    If schema[table] is an empty dict (no columns declared at all), the
    input DataFrame should be returned unchanged.
    """
    input_df = pd.DataFrame({"name": ["Alice"], "age": [30]})
    tables = {"users": input_df}
    schema = {"users": {}}

    result = normalize_tables(tables=tables, schema=schema)

    assert_frame_equal(result["users"], input_df, check_like=True)


def test_normalize_tables_does_not_mutate_input():
    """
    normalize_tables should not mutate the caller's original DataFrame
    in place (e.g. by adding default columns directly onto it). The
    original object passed in should remain untouched after the call.
    """
    input_df = pd.DataFrame({"name": ["Alice"]})
    original_columns = list(input_df.columns)
    tables = {"users": input_df}

    schema = {
        "users": {
            "name": {"required": True},
            "age": {"required": False, "default": 99},
        }
    }

    result = normalize_tables(tables=tables, schema=schema)

    # Input DataFrame must be unaffected by the call.
    assert list(input_df.columns) == original_columns
    assert "age" not in input_df.columns

    # Output must actually contain the new default column.
    assert "age" in result["users"].columns


def test_normalize_tables_returns_new_dict_object():
    """The returned dict should be a distinct object from the input dict."""
    tables = {"users": pd.DataFrame({"name": ["Alice"]})}
    schema = {"users": {"name": {"required": True}}}

    result = normalize_tables(tables=tables, schema=schema)

    assert result is not tables


def test_normalize_tables_empty_dataframe_gets_default_column():
    """
    An input DataFrame with zero rows should still get missing optional
    columns added (as an empty column), without raising or fabricating rows.
    """
    input_df = pd.DataFrame({"name": pd.Series([], dtype="object")})
    tables = {"movies": input_df}
    schema = {
        "movies": {
            "name": {"required": True},
            "genre": {"required": False, "default": "Unknown"},
        }
    }

    result = normalize_tables(tables=tables, schema=schema)

    assert "genre" in result["movies"].columns
    assert len(result["movies"]) == 0


def test_normalize_tables_preserves_columns_not_in_schema():
    """
    Columns present in the input DataFrame but not declared anywhere in
    the schema should be passed through untouched rather than dropped.
    """
    input_df = pd.DataFrame({
        "name": ["Alice"],
        "internal_id": ["xyz-123"],  # not part of schema at all
    })
    tables = {"users": input_df}
    schema = {"users": {"name": {"required": True}}}

    result = normalize_tables(tables=tables, schema=schema)

    assert "internal_id" in result["users"].columns
    assert result["users"]["internal_id"].iloc[0] == "xyz-123"


def test_normalize_tables_numeric_and_boolean_defaults():
    """Non-string default values (int, float, bool) should broadcast correctly."""
    input_df = pd.DataFrame({"name": ["Alice", "Bob"]})
    tables = {"users": input_df}
    schema = {
        "users": {
            "name": {"required": True},
            "score": {"required": False, "default": 0},
            "active": {"required": False, "default": True},
            "rating": {"required": False, "default": 4.5},
        }
    }

    result = normalize_tables(tables=tables, schema=schema)

    assert list(result["users"]["score"]) == [0, 0]
    assert list(result["users"]["active"]) == [True, True]
    assert list(result["users"]["rating"]) == [4.5, 4.5]



def test_normalize_tables_required_column_present_with_nulls_is_untouched():
    """
    normalize_tables is only responsible for filling in MISSING optional
    columns. A required column that is present but contains null values
    should be passed through as-is (validating nulls is is_valid_schema's
    job, not normalize_tables').
    """
    input_df = pd.DataFrame({
        "name": ["Alice", None],
        "email": ["alice@example.com", "bob@example.com"],
    })
    tables = {"users": input_df}
    schema = {
        "users": {
            "name": {"required": True},
            "email": {"required": True},
        }
    }

    result = normalize_tables(tables=tables, schema=schema)

    assert result["users"]["name"].isna().sum() == 1


def test_normalize_tables_multiple_tables_independent_defaults():
    """
    Defaults filled into one table's missing columns must not leak into
    or affect a sibling table's columns/values.
    """
    tables = {
        "users": pd.DataFrame({"name": ["Alice"]}),
        "movies": pd.DataFrame({"name": ["Inception"]}),
    }
    schema = {
        "users": {
            "name": {"required": True},
            "age": {"required": False, "default": "N/A"},
        },
        "movies": {
            "name": {"required": True},
            "genre": {"required": False, "default": "N/A"},
        },
    }

    result = normalize_tables(tables=tables, schema=schema)

    assert "age" not in result["movies"].columns
    assert "genre" not in result["users"].columns
    assert list(result["users"]["age"]) == ["N/A"]
    assert list(result["movies"]["genre"]) == ["N/A"]


# ---------------------------------------------------------------------------
# is_valid_schema — edge cases
# ---------------------------------------------------------------------------

def test_is_valid_schema_empty_schema_and_tables():
    """No tables and no schema should trivially be valid (returns None)."""
    report = is_valid_schema(tables={}, schema={})
    assert report is None


def test_is_valid_schema_all_required_columns_missing_for_one_table():
    """
    When every required column in a table is missing (not just some),
    the report should still list them all, comma-separated, in schema order.
    """
    tables = {
        "users": pd.DataFrame({"unrelated_col": ["x", "y"]}),
    }
    schema = {
        "users": {
            "name": {"required": True},
            "email": {"required": True},
        }
    }

    expected_error_message = textwrap.dedent(
        """
        Schema validation failed. The following required columns are missing:

        - users: name, email
        """
    ).strip()

    with pytest.raises(RuntimeError) as exc_info:
        is_valid_schema(tables=tables, schema=schema)

    assert str(exc_info.value).strip() == expected_error_message


def test_is_valid_schema_required_column_present_with_nulls_still_passes():
    """
    is_valid_schema checks for column PRESENCE, not for null/empty values
    within a present column. A required column full of nulls should not
    trigger a missing-column error.
    """
    tables = {
        "users": pd.DataFrame({
            "name": [None, None],
            "email": ["a@example.com", "b@example.com"],
        }),
    }
    schema = {
        "users": {
            "name": {"required": True},
            "email": {"required": True},
        }
    }

    report = is_valid_schema(tables=tables, schema=schema)
    assert report is None


def test_is_valid_schema_extra_columns_not_in_schema_are_ignored():
    """Columns in the DataFrame that aren't declared in the schema should
    have no bearing on validity — only declared required columns matter."""
    tables = {
        "users": pd.DataFrame({
            "name": ["Alice"],
            "email": ["alice@example.com"],
            "some_extra_column": ["whatever"],
        }),
    }
    schema = {
        "users": {
            "name": {"required": True},
            "email": {"required": True},
        }
    }

    report = is_valid_schema(tables=tables, schema=schema)
    assert report is None


def test_is_valid_schema_optional_columns_missing_does_not_raise():
    """Missing OPTIONAL columns should never trigger a RuntimeError."""
    tables = {
        "movies": pd.DataFrame({"name": ["Inception"]}),
    }
    schema = {
        "movies": {
            "name": {"required": True},
            "genre": {"required": False, "default": None},
        }
    }

    report = is_valid_schema(tables=tables, schema=schema)
    assert report is None


def test_is_valid_schema_missing_columns_preserve_schema_order():
    """
    The list of missing columns per table in the error report should
    follow the order columns are declared in the schema, not alphabetical
    or insertion order of anything else.
    """
    tables = {
        "users": pd.DataFrame({"name": ["Alice"]}),
    }
    schema = {
        "users": {
            "name": {"required": True},
            "zeta": {"required": True},
            "alpha": {"required": True},
        }
    }

    with pytest.raises(RuntimeError) as exc_info:
        is_valid_schema(tables=tables, schema=schema)

    # Order must match schema declaration order: zeta before alpha.
    message = str(exc_info.value)
    assert message.index("zeta") < message.index("alpha")