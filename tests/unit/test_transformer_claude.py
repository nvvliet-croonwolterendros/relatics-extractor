"""
Tests for empty-input handling in transform.py.

Two "empty" table shapes are covered, per how the Relatics export actually
behaves:
  - a genuine zero-row DataFrame (0 rows), and
  - a single placeholder row where every value is None (the shape the export
    returns when there is no data), e.g.:
        {'R1Instance': {0: None}, 'R1InstanceID': {0: None}, ...}

Two scenarios are covered end to end:
  1. No relations at all are defined for the element (Relations is empty).
     -> No link tables should be created.
  2. Relations are defined, but no relation instances exist yet
     (RelationInstances is empty).
     -> Link tables should still be created, but empty.
"""
import pandas as pd
import pytest

from relatics_connector.processing.transformer import (
    create_element_tables,
    _transform_relations_table,
    _is_placeholder_empty,
)

R1_ELEMENT = "test_element"

RELATIONS_COLUMNS = [
    "RelationID",
    "Relation",
    "R2Element",
    "R2ElementID",
    "ChildR2Element",
    "ChildR2ElementID",
    "Cardinality",
]

RELATION_INSTANCES_COLUMNS = [
    "R1Instance",
    "R1InstanceID",
    "R1Element",
    "RelationInstanceID",
    "RelationID",
    "Cardinality",
    "R2Instance",
    "R2InstanceID",
    "R2Element",
    "R2ElementID",
    "Relation",
]


# --------------------------------------------------------------------------
# Helpers to build fixture tables
# --------------------------------------------------------------------------

def make_placeholder_row_df(columns):
    """A single row with every value None, matching what the source system
    returns when there is no data (as opposed to a genuine 0-row frame)."""
    return pd.DataFrame({col: [None] for col in columns})


def make_zero_row_df(columns):
    """A genuine 0-row frame with the expected columns."""
    return pd.DataFrame(columns=columns)


def make_element_instances_df(ids):
    return pd.DataFrame({
        "R1InstanceID": ids,
        "R1Instance": [f"instance_{i}" for i in ids],
    })


def make_properties_df(names):
    return pd.DataFrame({"Property": names})


def make_property_instances_df(rows):
    """rows: list of (R1InstanceID, Property, PropertyInstance) tuples."""
    return pd.DataFrame(rows, columns=["R1InstanceID", "Property", "PropertyInstance"])


def make_relations_df(rows):
    """rows: list of dicts with keys matching RELATIONS_COLUMNS (missing keys default to '')."""
    df = pd.DataFrame(rows)
    for col in RELATIONS_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[RELATIONS_COLUMNS]


def make_relation_instances_df(rows):
    """rows: list of dicts with keys matching RELATION_INSTANCES_COLUMNS."""
    df = pd.DataFrame(rows)
    for col in RELATION_INSTANCES_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[RELATION_INSTANCES_COLUMNS]


def base_tables():
    """A minimal, non-empty ElementInstances/Properties/PropertyInstances set,
    reused across scenarios since the tests focus on Relations/RelationInstances."""
    return {
        "ElementInstances": make_element_instances_df(["e1", "e2"]),
        "Properties": make_properties_df(["Name"]),
        "PropertyInstances": make_property_instances_df([
            ("e1", "Name", "Element One"),
            ("e2", "Name", "Element Two"),
        ]),
    }


# --------------------------------------------------------------------------
# _is_placeholder_empty
# --------------------------------------------------------------------------

@pytest.mark.parametrize("columns", [RELATIONS_COLUMNS, RELATION_INSTANCES_COLUMNS])
def test_is_placeholder_empty_detects_zero_rows(columns):
    assert _is_placeholder_empty(make_zero_row_df(columns)) is True


@pytest.mark.parametrize("columns", [RELATIONS_COLUMNS, RELATION_INSTANCES_COLUMNS])
def test_is_placeholder_empty_detects_all_none_row(columns):
    assert _is_placeholder_empty(make_placeholder_row_df(columns)) is True


def test_is_placeholder_empty_false_for_real_data():
    df = make_relations_df([{"RelationID": "r1", "Relation": "Heeft property", "R2Element": "Name", "R2ElementID": "p1", "Cardinality": ":1"}])
    assert _is_placeholder_empty(df) is False


# --------------------------------------------------------------------------
# _transform_relations_table - unit tests
# --------------------------------------------------------------------------

@pytest.mark.parametrize("relations_empty_shape", ["zero_row", "placeholder_row"])
def test_transform_relations_table_no_relations_at_all(relations_empty_shape):
    """Relations is empty -> both outputs come back as genuine zero-row
    frames, and no exception is raised."""
    if relations_empty_shape == "zero_row":
        relations_df = make_zero_row_df(RELATIONS_COLUMNS)
        relations_instances_df = make_zero_row_df(RELATION_INSTANCES_COLUMNS)
    else:
        relations_df = make_placeholder_row_df(RELATIONS_COLUMNS)
        relations_instances_df = make_placeholder_row_df(RELATION_INSTANCES_COLUMNS)

    out_relations_df, out_relations_instances_df = _transform_relations_table(
        relations_df, relations_instances_df
    )

    assert len(out_relations_df) == 0
    assert len(out_relations_instances_df) == 0
    assert "ChildR2Element" not in out_relations_df.columns
    assert "ChildR2ElementID" not in out_relations_df.columns
    assert "Relation" not in out_relations_instances_df.columns
    assert "R2Element" in out_relations_instances_df.columns


@pytest.mark.parametrize("instances_empty_shape", ["zero_row", "placeholder_row"])
def test_transform_relations_table_relations_exist_no_instances(instances_empty_shape):
    """Relations are defined, but RelationInstances is empty -> relations_df
    is fully processed and normalized; relations_instances_df comes back as
    a genuine zero-row frame with a resolved R2Element column."""
    relations_df = make_relations_df([
        {"RelationID": "r1", "Relation": "Heeft property", "R2Element": "Name", "R2ElementID": "p1", "Cardinality": ":1"},
        {"RelationID": "r2", "Relation": "Heeft link element", "R2Element": "Link Element", "R2ElementID": "l1", "Cardinality": ":n"},
    ])

    if instances_empty_shape == "zero_row":
        relations_instances_df = make_zero_row_df(RELATION_INSTANCES_COLUMNS)
    else:
        relations_instances_df = make_placeholder_row_df(RELATION_INSTANCES_COLUMNS)

    out_relations_df, out_relations_instances_df = _transform_relations_table(
        relations_df, relations_instances_df
    )

    # relations_df is still processed: R2Element normalized, child cols dropped
    assert len(out_relations_df) == 2
    assert "ChildR2Element" not in out_relations_df.columns
    assert set(out_relations_df["R2Element"]) == {"name", "link_element"}

    # relations_instances_df is a genuine empty frame with the R2Element column
    assert len(out_relations_instances_df) == 0
    assert "Relation" not in out_relations_instances_df.columns
    assert "R2Element" in out_relations_instances_df.columns


def test_transform_relations_table_normal_path_still_works():
    """Sanity check: normal (non-empty) inputs still process without error."""
    relations_df = make_relations_df([
        {"RelationID": "r1", "Relation": "Heeft property", "R2Element": "Name", "R2ElementID": "p1", "Cardinality": ":1"},
    ])
    relations_instances_df = make_relation_instances_df([
        {"R1InstanceID": "e1", "R1Element": R1_ELEMENT, "RelationID": "r1", "R2ElementID": "p1",
         "R2InstanceID": "p1_e1", "R2Instance": "some value", "Cardinality": ":1"},
    ])

    out_relations_df, out_relations_instances_df = _transform_relations_table(
        relations_df, relations_instances_df
    )

    assert len(out_relations_df) == 1
    assert len(out_relations_instances_df) == 1
    assert out_relations_instances_df.loc[0, "R2Element"] == "name"


# --------------------------------------------------------------------------
# create_element_tables - integration tests
# --------------------------------------------------------------------------

@pytest.mark.parametrize("empty_shape", ["zero_row", "placeholder_row"])
def test_create_element_tables_no_relations_at_all(empty_shape):
    """When there are no relations at all for the element, no link tables
    should be created - only the element table itself."""
    tables = base_tables()
    if empty_shape == "zero_row":
        tables["Relations"] = make_zero_row_df(RELATIONS_COLUMNS)
        tables["RelationInstances"] = make_zero_row_df(RELATION_INSTANCES_COLUMNS)
    else:
        tables["Relations"] = make_placeholder_row_df(RELATIONS_COLUMNS)
        tables["RelationInstances"] = make_placeholder_row_df(RELATION_INSTANCES_COLUMNS)

    result = create_element_tables(tables, r1_element=R1_ELEMENT)

    assert list(result.keys()) == [f"raw_relatics__{R1_ELEMENT}"]
    element_table = result[f"raw_relatics__{R1_ELEMENT}"]
    assert len(element_table) == 2
    assert "name" in element_table.columns


@pytest.mark.parametrize("empty_shape", ["zero_row", "placeholder_row"])
def test_create_element_tables_relations_exist_no_instances(empty_shape):
    """When relations are defined but no relation instances exist yet, link
    tables should still be created for every :n relation, just empty, and
    :1 relation/property columns should exist but be empty."""
    tables = base_tables()
    tables["Relations"] = make_relations_df([
        {"RelationID": "r1", "Relation": "Heeft property", "R2Element": "Extra Property", "R2ElementID": "p1", "Cardinality": ":1"},
        {"RelationID": "r2", "Relation": "Heeft to-one link", "R2Element": "To One Element", "R2ElementID": "o1", "Cardinality": ":1"},
        {"RelationID": "r3", "Relation": "Heeft link elements", "R2Element": "Link Element", "R2ElementID": "l1", "Cardinality": ":n"},
    ])
    if empty_shape == "zero_row":
        tables["RelationInstances"] = make_zero_row_df(RELATION_INSTANCES_COLUMNS)
    else:
        tables["RelationInstances"] = make_placeholder_row_df(RELATION_INSTANCES_COLUMNS)

    result = create_element_tables(tables, r1_element=R1_ELEMENT)

    link_table_name = f"raw_relatics__{R1_ELEMENT}_link_element"
    assert link_table_name in result
    link_table = result[link_table_name]
    assert len(link_table) == 0
    assert set(link_table.columns) == {f"{R1_ELEMENT}_guid", "link_element_guid"}

    element_table = result[f"raw_relatics__{R1_ELEMENT}"]
    assert len(element_table) == 2
    # :1 non-property relation column exists but is empty
    assert "to_one_element_guid" in element_table.columns
    assert element_table["to_one_element_guid"].isna().all()
    # property-relation column exists but is empty
    assert "extra_property" in element_table.columns
    assert element_table["extra_property"].isna().all()


def test_create_element_tables_normal_path_still_works():
    """Sanity check: a fully populated set of tables still produces the
    expected element table and link table."""
    tables = base_tables()
    tables["Relations"] = make_relations_df([
        {"RelationID": "r1", "Relation": "Heeft link elements", "R2Element": "Link Element", "R2ElementID": "l1", "Cardinality": ":n"},
    ])
    tables["RelationInstances"] = make_relation_instances_df([
        {"R1InstanceID": "e1", "R1Element": R1_ELEMENT, "RelationID": "r1", "R2ElementID": "l1",
         "R2InstanceID": "link_1", "R2Instance": "Link One", "Cardinality": ":n"},
    ])

    result = create_element_tables(tables, r1_element=R1_ELEMENT)

    link_table_name = f"raw_relatics__{R1_ELEMENT}_link_element"
    assert link_table_name in result
    link_table = result[link_table_name]
    assert len(link_table) == 1
    assert link_table.iloc[0][f"{R1_ELEMENT}_guid"] == "e1"
    assert link_table.iloc[0]["link_element_guid"] == "link_1"