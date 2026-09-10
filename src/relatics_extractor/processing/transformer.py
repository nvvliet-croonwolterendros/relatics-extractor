import logging
import re
import unicodedata
from typing import Literal

import pandas as pd

logger = logging.getLogger(__name__)

R1ELEMENT_COL = "R1Element"

R1INSTANCE_COL = "R1Instance"
R1INSTANCEID_COL = "R1InstanceID"

PROPERTY_COL = "Property"
PROPERTYINSTANCE_COL = "PropertyInstance"

RELATION_COL = "Relation"
RELATIONID_COL = "RelationID"
CARDINALITY_COL = "Cardinality"

R2ELEMENT_COL = "R2Element"
R2ELEMENTID_COL = "R2ElementID"

CHILDR2ELEMENT_COL = "ChildR2Element"
CHILDR2ELEMENTID_COL = "ChildR2ElementID"

R2INSTANCE_COL = "R2Instance"
R2INSTANCEID_COL = "R2InstanceID"

DEFAULT_COLUMN_MAP = {
    R1INSTANCEID_COL: "guid",
    R1INSTANCE_COL: "naam",
    "R1InstanceDescription": "description",
    "R1InstanceRichText": "rich_text",
}


def create_element_tables(
    tables: dict[str, pd.DataFrame],
    column_map: dict[str, str] = DEFAULT_COLUMN_MAP,
    inline_relations: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Create the element table and associated link tables for an element.

    The element table is built by joining:
    - property values
    - to-one relation references
    - directly resolved relation values

    Regular to-one relations are represented as <element>_guid
    columns containing the related R2 instance identifier. Relations
    listed in inline_relations are represented directly by their
    related R2 instance value.

    To-many relations are returned as separate link tables.

    Args:
        tables: Dict with the 6 raw Relatics report tables ("Element",
            "ElementInstances", "Properties", "PropertyInstances",
            "Relations", "RelationInstances").
        column_map: Mapping used to rename the final element table's
            columns.
        inline_relations: Relation names of Relations to R2 Elements
            whose values will be materialized directly in the
            resulting element tables.

    Returns:
        Mapping of table names to DataFrames containing the element table
        and any associated link tables.
    """
    element_df = tables["Element"].copy()
    element_instances_df = tables["ElementInstances"].copy()
    properties_df = tables["Properties"].copy()
    property_instances_df = tables["PropertyInstances"].copy()
    relations_df = tables["Relations"].copy()
    relation_instances_df = tables["RelationInstances"].copy()

    r1_element = _normalize_value(element_df[R1ELEMENT_COL][0])

    relations_df, relation_instances_df = _transform_relations_table(
        relations_df=relations_df, relation_instances_df=relation_instances_df
    )
    property_table = _create_property_table(
        properties_df=properties_df, property_instances_df=property_instances_df
    )
    to_one_relations_table = _create_to_one_relations_table(
        relations_df=relations_df,
        relation_instances_df=relation_instances_df,
        inline_relations=inline_relations,
    )

    sub_tables: list = [
        df
        for df in (
            property_table,
            to_one_relations_table,
        )
        if not df.columns.empty
    ]

    element_table = (
        element_instances_df.set_index(R1INSTANCEID_COL)
        .join(sub_tables, how="left")
        .reset_index()
    )
    element_table = element_table.rename(columns=column_map)

    link_tables = _create_link_tables(r1_element, relations_df, relation_instances_df)

    return {
        f"raw_relatics__{r1_element}": element_table,
        **link_tables,
    }


def _transform_relations_table(
    relations_df: pd.DataFrame, relation_instances_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Normalize and disambiguate relation target element names.

    Coalesces child R2 element data into the primary R2 columns.
    Normalizes element and relation names.
    Validates that each Relation/R2Element combination is unique.
    Renames duplicate and self-referencing R2Elements to ensure unique
    SQL-safe column names.
    Applies the same renaming to relation instances.
    """
    if (
        CHILDR2ELEMENT_COL in relations_df.columns
        and CHILDR2ELEMENTID_COL in relations_df.columns
    ):
        relations_df[R2ELEMENT_COL] = (
            relations_df[CHILDR2ELEMENT_COL]
            .replace("", None)
            .combine_first(relations_df[R2ELEMENT_COL])
        )
        relations_df[R2ELEMENTID_COL] = (
            relations_df[CHILDR2ELEMENTID_COL]
            .replace("", None)
            .combine_first(relations_df[R2ELEMENTID_COL])
        )
        relations_df = relations_df.drop(
            [CHILDR2ELEMENT_COL, CHILDR2ELEMENTID_COL], axis=1
        )

    relations_df[[R1ELEMENT_COL, RELATION_COL, R2ELEMENT_COL]] = relations_df[
        [R1ELEMENT_COL, RELATION_COL, R2ELEMENT_COL]
    ].map(_normalize_value)
    relation_instances_df[R2ELEMENT_COL] = relation_instances_df[R2ELEMENT_COL].apply(
        _normalize_value
    )

    duplicates_mask = relations_df.duplicated(
        subset=[RELATION_COL, R2ELEMENT_COL], keep=False
    )
    if duplicates_mask.any():
        logger.error("Duplicate Relation/R2Element combinations found.")
        logger.debug(relations_df[duplicates_mask].to_dict())
        raise RuntimeError(
            "relations_df cannot contain duplicated Relation + R2Element pairs."
        )

    duplicates = relations_df.loc[
        relations_df[R2ELEMENT_COL].duplicated(keep=False)
    ].copy()
    duplicates[R2ELEMENT_COL] = (
        duplicates[RELATION_COL] + "_" + duplicates[R2ELEMENT_COL]
    )

    self_references = relations_df.loc[
        relations_df[R1ELEMENT_COL] == relations_df[R2ELEMENT_COL]
    ].copy()
    self_references[R2ELEMENT_COL] = (
        self_references[RELATION_COL] + "_" + self_references[R2ELEMENT_COL]
    )

    rename_rows = pd.concat([duplicates, self_references]).drop_duplicates(
        subset=RELATIONID_COL
    )

    rename_map = rename_rows.set_index(RELATIONID_COL)[R2ELEMENT_COL].to_dict()

    relations_df[R2ELEMENT_COL] = (
        relations_df[RELATIONID_COL].map(rename_map).fillna(relations_df[R2ELEMENT_COL])
    )
    relation_instances_df[R2ELEMENT_COL] = (
        relation_instances_df[RELATIONID_COL]
        .map(rename_map)
        .fillna(relation_instances_df[R2ELEMENT_COL])
    )

    return relations_df, relation_instances_df


def _create_property_table(
    properties_df: pd.DataFrame, property_instances_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Create a property table indexed by R1 instance.

    Property names are normalized and become columns.
    A column is included for every property defined in properties_df,
    even if no property instances exist.
    """
    property_instances_df = property_instances_df.copy()

    properties = properties_df[PROPERTY_COL].apply(_normalize_value).unique().tolist()

    property_instances_df[PROPERTY_COL] = property_instances_df[PROPERTY_COL].apply(
        _normalize_value
    )

    if not properties:
        logger.warning("No properties found in properties report part.")
    if property_instances_df.empty:
        logger.warning("No property instances found in property instances report part.")

    try:
        return (
            property_instances_df.pivot(
                index=R1INSTANCEID_COL,
                columns=PROPERTY_COL,
                values=PROPERTYINSTANCE_COL,
            )
            .reindex(columns=properties)
            .rename_axis(columns=None)
        )

    except ValueError:
        logger.exception(
            "Failed to pivot property instances. "
            "Normalization may have created duplicate property names."
        )
        raise


def _create_to_one_relations_table(
    relations_df: pd.DataFrame,
    relation_instances_df: pd.DataFrame,
    inline_relations: list[str] | None = None,
) -> pd.DataFrame:
    """
    Create a table containing to-one relation data.

    For regular to-one relations, each referenced element becomes a
    <element>_guid column containing the related R2 instance
    id.

    Relations listed in inline_relations are represented by their
    resolved value instead of an R2 instance id.
    """
    inline_relations = inline_relations or []
    if inline_relations:
        inline_relations = [_normalize_value(value) for value in inline_relations]

    all_relations_one_df = _filter_cardinality(
        df=relations_df,
        cardinality="one",
    )

    relations_one_df = all_relations_one_df[
        ~all_relations_one_df[RELATION_COL].isin(inline_relations)
    ].copy()

    relation_instances_one_df = relation_instances_df[
        relation_instances_df[RELATIONID_COL].isin(relations_one_df[RELATIONID_COL])
    ].copy()

    to_one_relation_columns = [
        f"{element}_guid" for element in relations_one_df[R2ELEMENT_COL]
    ]

    relation_instances_one_df[R2ELEMENT_COL] += "_guid"

    to_one_relations_table = (
        relation_instances_one_df.pivot(
            index=R1INSTANCEID_COL,
            columns=R2ELEMENT_COL,
            values=R2INSTANCEID_COL,
        )
        .reindex(columns=to_one_relation_columns)
        .rename_axis(columns=None)
    )

    if not inline_relations:
        return to_one_relations_table

    inline_relations_df = all_relations_one_df[
        all_relations_one_df[RELATION_COL].isin(inline_relations)
    ].copy()

    inline_relations_table = _create_inline_relations_table(
        inline_relations_df=inline_relations_df,
        relation_instances_df=relation_instances_df,
    )

    return pd.concat(
        [inline_relations_table, to_one_relations_table],
        axis=1,
    )


def _create_inline_relations_table(
    inline_relations_df: pd.DataFrame,
    relation_instances_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create a table containing directly resolved property values.

    Each referenced property element becomes a column containing the
    related R2 instance value.
    """
    inline_relation_instances_df = relation_instances_df[
        relation_instances_df[RELATIONID_COL].isin(inline_relations_df[RELATIONID_COL])
    ].copy()

    property_columns = inline_relations_df[R2ELEMENT_COL].tolist()

    return (
        inline_relation_instances_df.pivot(
            index=R1INSTANCEID_COL,
            columns=R2ELEMENT_COL,
            values=R2INSTANCE_COL,
        )
        .reindex(columns=property_columns)
        .rename_axis(columns=None)
    )


def _create_link_tables(
    r1_element: str, relations_df: pd.DataFrame, relation_instances_df: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    """
    Create link tables for all to-many relations.

    Each R2Element receives its own link table containing the R1 and R2
    instance identifiers. Table and column names are normalized to match
    the downstream schema.
    """
    many_relations_df = _filter_cardinality(relations_df, "many")
    many_relation_instances_df = _filter_cardinality(relation_instances_df, "many")

    link_tables: dict[str, pd.DataFrame] = {}

    for r2_element in many_relations_df[R2ELEMENT_COL]:
        table_name = f"raw_relatics__{r1_element}_{r2_element}"

        mask = many_relation_instances_df[R2ELEMENT_COL] == str(r2_element)

        table_df = many_relation_instances_df.loc[
            mask, [R1INSTANCEID_COL, R2INSTANCEID_COL]
        ].reset_index(drop=True)

        link_tables[table_name] = table_df.rename(
            columns={
                R1INSTANCEID_COL: f"{r1_element}_guid",
                R2INSTANCEID_COL: f"{r2_element}_guid",
            }
        )

    return link_tables


def _filter_cardinality(
    df: pd.DataFrame,
    cardinality: Literal["many", "one"],
) -> pd.DataFrame:
    """
    Filter rows by relation cardinality.

    Cardinality values are normalized to either ':1' or ':n'
    before filtering.
    """
    cardinality_mask = df[CARDINALITY_COL].map(
        lambda x: ":n" if "n" in str(x).split(":")[-1] else ":1"
    )

    if cardinality == "many":
        return df[cardinality_mask == ":n"]

    if cardinality == "one":
        return df[cardinality_mask == ":1"]

    raise ValueError(f"Invalid cardinality '{cardinality}'. Expected 'one' or 'many'.")


def _normalize_value(val: str, max_length: int = 63) -> str:
    """
    Normalize text for use as SQL table and column names.
    """
    if pd.isna(val) or val is None:
        return ""

    val = str(val)

    # Replace special characters
    val = val.replace("&", "_en_").replace("€", "_euro_").replace("+", "_plus_")

    # Unicode -> ASCII
    val = unicodedata.normalize("NFKD", val)
    val = val.encode("ascii", "ignore").decode("ascii")

    # Lowercase
    val = val.lower()

    # Replace invalid characters
    val = re.sub(r"[^a-z0-9_]", "_", val)

    # Collapse underscores
    val = re.sub(r"_+", "_", val)

    # Strip leading/trailing underscores
    val = val.strip("_")

    if not val:
        return ""

    # Prevent leading digit
    if val[0].isdigit():
        val = f"no_num_{val}"

    # Trim to PostgreSQL identifier length
    return val[:max_length]
