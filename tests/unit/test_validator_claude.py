import pytest
import pandas as pd
from pandas.testing import assert_frame_equal
import textwrap

from src.processing.validator import normalize_tables, is_valid_schema
from src.processing.transformer import _transform_relations_table


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

MODULE_PATH = "src.processing.transformer"

@pytest.fixture(autouse=True)
def _identity_normalize(monkeypatch):
    monkeypatch.setattr(f"{MODULE_PATH}._normalize_value", lambda x: x)


def make_relations_df(rows):
    defaults = {"ChildR2Element": "", "ChildR2ElementID": ""}
    full_rows = [{**defaults, **row} for row in rows]
    return pd.DataFrame(full_rows, columns=[
        "Relation", "Cardinality", "RelationID", "R2Element",
        "R2ElementID", "ChildR2Element", "ChildR2ElementID",
    ])


def make_instances_df(rows):
    return pd.DataFrame(rows, columns=[
        "R1Instance", "R1InstanceID", "RelationInstanceID", "R2Instance",
        "R2InstanceID", "R2Element", "R2ElementID", "Cardinality",
        "RelationID", "R1Element",
    ])


def test_ai_self_reference_is_renamed():
    """
    When R1Element equals the resolved R2Element for a relation instance
    (e.g. a 'ReportsTo' relation where a Person reports to a Person), the
    R2Element should be prefixed with the Relation name in both output
    tables, per the docstring's explicit self-reference requirement.
    """
    relations_df = make_relations_df([
        {"Relation": "ReportsTo", "Cardinality": "N:1", "RelationID": 1,
         "R2Element": "Person", "R2ElementID": 100},
    ])
    instances_df = make_instances_df([
        {"R1Instance": "Alice", "R1InstanceID": 1, "RelationInstanceID": 1,
         "R2Instance": "Bob", "R2InstanceID": 2, "R2Element": "Person",
         "R2ElementID": 100, "Cardinality": "N:1", "RelationID": 1,
         "R1Element": "Person"},
    ])

    result_relations, result_instances = _transform_relations_table(relations_df, instances_df)

    assert result_relations.loc[0, "R2Element"] == "ReportsTo_Person"
    assert result_instances.loc[0, "R2Element"] == "ReportsTo_Person"


def test_ai_self_reference_downstream_collision_raises():
    """
    A self-reference rename can produce a name that collides with another
    R2Element already used for the same relation elsewhere in the
    instances table. This should be (and currently is) caught by the
    final duplicate check on relations_instances_df.
    """
    relations_df = make_relations_df([
        {"Relation": "ReportsTo", "Cardinality": "N:1", "RelationID": 1,
         "R2Element": "Person", "R2ElementID": 100},
        {"Relation": "ReportsTo", "Cardinality": "N:1", "RelationID": 1,
         "R2Element": "ReportsTo_Person", "R2ElementID": 200},
    ])
    instances_df = make_instances_df([
        {"R1Instance": "Alice", "R1InstanceID": 1, "RelationInstanceID": 1,
         "R2Instance": "Bob", "R2InstanceID": 2, "R2Element": "Person",
         "R2ElementID": 100, "Cardinality": "N:1", "RelationID": 1,
         "R1Element": "Person"},
        {"R1Instance": "Carol", "R1InstanceID": 3, "RelationInstanceID": 2,
         "R2Instance": "Dave", "R2InstanceID": 4, "R2Element": "ReportsTo_Person",
         "R2ElementID": 200, "Cardinality": "N:1", "RelationID": 1,
         "R1Element": "Person"},
    ])

    with pytest.raises(RuntimeError):
        _transform_relations_table(relations_df, instances_df)


def test_ai_self_reference_rename_duplicate_in_relations_df_raises():
    """
    FIX VERIFICATION: previously, a self-reference rename that produced a
    name colliding with another, instance-less, R2Element already defined
    for the same relation would leave relations_df with an undetected
    duplicate Relation + R2Element pair, since only relations_instances_df
    was re-checked after the self-reference merge. relations_df is now
    re-validated after that merge, so this should raise a RuntimeError.
    """
    relations_df = make_relations_df([
        {"Relation": "ReportsTo", "Cardinality": "N:1", "RelationID": 1,
         "R2Element": "Person", "R2ElementID": 100},
        {"Relation": "ReportsTo", "Cardinality": "N:1", "RelationID": 1,
         "R2Element": "ReportsTo_Person", "R2ElementID": 200},
    ])
    instances_df = make_instances_df([
        {"R1Instance": "Alice", "R1InstanceID": 1, "RelationInstanceID": 1,
         "R2Instance": "Bob", "R2InstanceID": 2, "R2Element": "Person",
         "R2ElementID": 100, "Cardinality": "N:1", "RelationID": 1,
         "R1Element": "Person"},
    ])

    with pytest.raises(RuntimeError):
        _transform_relations_table(relations_df, instances_df)


def test_ai_unmatched_instance_row_raises():
    """
    FIX VERIFICATION: previously, if a relations_instances_df row's
    RelationID + R2ElementID had no matching row in relations_df, the
    left-merge left New_R2Element as NaN, which was written straight into
    the row's R2Element column with no validation or error raised.
    Unmatched rows are now checked right after the merge, so this should
    raise a RuntimeError instead of silently producing NaN.
    """
    relations_df = make_relations_df([
        {"Relation": "Owns", "Cardinality": "1:N", "RelationID": 1,
         "R2Element": "Car", "R2ElementID": 100},
    ])
    instances_df = make_instances_df([
        {"R1Instance": "Alice", "R1InstanceID": 1, "RelationInstanceID": 1,
         "R2Instance": "Ghost", "R2InstanceID": 999, "R2Element": "Unknown",
         "R2ElementID": 999, "Cardinality": "1:N", "RelationID": 1,
         "R1Element": "Person"},
    ])

    with pytest.raises(RuntimeError):
        _transform_relations_table(relations_df, instances_df)


def test_ai_duplicate_relationid_r2element_in_instances_raises():
    """
    Sanity check for the final duplicate guard: two instance rows that
    resolve to the same RelationID + R2Element (without any self-reference
    involved) should raise a RuntimeError.
    """
    relations_df = make_relations_df([
        {"Relation": "Owns", "Cardinality": "1:N", "RelationID": 1,
         "R2Element": "Car", "R2ElementID": 100},
    ])
    instances_df = make_instances_df([
        {"R1Instance": "Alice", "R1InstanceID": 1, "RelationInstanceID": 1,
         "R2Instance": "Tesla", "R2InstanceID": 1000, "R2Element": "Car",
         "R2ElementID": 100, "Cardinality": "1:N", "RelationID": 1,
         "R1Element": "Person"},
        {"R1Instance": "Bob", "R1InstanceID": 2, "RelationInstanceID": 2,
         "R2Instance": "Honda", "R2InstanceID": 1001, "R2Element": "Car",
         "R2ElementID": 100, "Cardinality": "1:N", "RelationID": 1,
         "R1Element": "Person"},
    ])

    with pytest.raises(RuntimeError):
        _transform_relations_table(relations_df, instances_df)


def test_ai_inconsistent_self_reference_across_same_relation_element_raises():
    """
    FIX VERIFICATION: if two instance rows share the same RelationID +
    R2ElementID but disagree on whether R1Element == R2Element (one is a
    self-reference, the other is not), the self-reference rename would be
    applied inconsistently for the same relations_df row, which previously
    risked duplicating rows on merge-back. This is now caught explicitly.
    """
    relations_df = make_relations_df([
        {"Relation": "ReportsTo", "Cardinality": "N:1", "RelationID": 1,
         "R2Element": "Person", "R2ElementID": 100},
    ])
    instances_df = make_instances_df([
        {"R1Instance": "Alice", "R1InstanceID": 1, "RelationInstanceID": 1,
         "R2Instance": "Alice", "R2InstanceID": 1, "R2Element": "Person",
         "R2ElementID": 100, "Cardinality": "N:1", "RelationID": 1,
         "R1Element": "Person"},
        {"R1Instance": "Bob", "R1InstanceID": 2, "RelationInstanceID": 2,
         "R2Instance": "Carol", "R2InstanceID": 3, "R2Element": "Person",
         "R2ElementID": 100, "Cardinality": "N:1", "RelationID": 1,
         "R1Element": "Manager"},
    ])

    with pytest.raises(RuntimeError):
        _transform_relations_table(relations_df, instances_df)