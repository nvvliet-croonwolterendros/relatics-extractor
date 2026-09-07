import pandas as pd
from typing import Dict, Literal, Tuple
import unicodedata
import re
import logging

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

COLUMN_MAP = {
    R1INSTANCEID_COL: "guid",
    R1INSTANCE_COL: "naam",
    "R1InstanceDescription": "description",
    "R1InstanceRichText": "rich_text"
}

def create_element_tables(
    tables: Dict[str, pd.DataFrame],
    r1_element: str,
    column_map: Dict[str, str] = COLUMN_MAP,
) -> Dict[str, pd.DataFrame]:
    """Main function to create element and link tables.

    Takes the 6 input tables for a given element.
    Transform the relations table.
    Create the property_table, property_elements_table and to_one_relations_table.
    Set R1InstanceID as the index on element_instances_df.
    Merge property_table, property_elements_table and to_one_relations_table on element_instances_df on R1InstanceID as index.
    Rename columns of the element table using the COLUMN_MAP.
    Create the link tables.

    Args:
        tables: dict with the 6 raw Relatics report tables ("ElementInstances",
            "Properties", "PropertyInstances", "Relations", "RelationInstances").
        r1_element: the name of the element being processed. This is passed in
            explicitly rather than derived from RelationInstances, since
            RelationInstances can legitimately be empty (no relation instances
            yet exist for this element), in which case there is no data to
            derive the element name from.
        column_map: mapping used to rename the final element table's columns.

    Returns:
        Dict: the element table and required link tables for the element.
    """
    # normalize r1 element name 
    r1_element = _normalize_value(r1_element)
    
    # retrive dataframes
    element_instances_df = tables["ElementInstances"].copy()
    properties_df = tables["Properties"].copy()
    property_instances_df = tables["PropertyInstances"].copy()
    relations_df = tables["Relations"].copy()
    relations_instances_df = tables["RelationInstances"].copy()

    # transform the relations table(s)
    relations_df, relations_instances_df = _transform_relations_table(
        relations_df, relations_instances_df
    )
    
    # build the three sub-tables to merge onto element_instances_df
    property_table = _create_property_table(properties_df, property_instances_df)
    property_elements_table = _create_property_elements_table(relations_df, relations_instances_df)
    to_one_relations_table = _create_to_one_relations_table(relations_df, relations_instances_df)
    sub_tables: list = [
        df for df in (property_table, property_elements_table, to_one_relations_table)
        if df is not None and not df.columns.empty
    ]

    # merge subtables onto element_instances_df
    element_table = (
        element_instances_df
        .set_index(R1INSTANCEID_COL)
        .join(sub_tables, how="left")
        .reset_index()
    )

    # rename columns
    element_table = element_table.rename(columns=column_map)

    # build link (:n) tables
    link_tables = _create_link_tables(r1_element, relations_df, relations_instances_df)

    # create result dict
    result: Dict[str, pd.DataFrame] = {
        f"raw_relatics__{r1_element}": element_table
    }
    result.update(link_tables)

    return result


def _transform_relations_table(
    relations_df: pd.DataFrame,
    relation_instances_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    In the Relations table Coalesce R2ElementID, R2Element with ChildR2Element, ChildR2Elemnent when child columns are not empty. DONE
    Raise error if there are duplicate R2Element Relation combinations in the Relations table. DONE
    Using the Relations table create a rename-map duplicate R2Elements to {Relation}_{R2Element}. DONE
    Rename R2Elements in the RelationInstances table using the rename map. DONE
    In the Relations table Renames R2Elements to make them SQL safe.

    Important: the R2Element should also be renamed when the R2Element = R1Element

    Rename mapping must be done in both relations_df and relation_instance_df
    """
    # return zero-row DataFrames if relations_df is empty
    if _is_df_empty(relations_df):
        return relations_df, relation_instances_df
    
    # coalesce child elements
    if CHILDR2ELEMENT_COL and CHILDR2ELEMENTID_COL in relations_df.columns:
        relations_df['R2Element'] = relations_df['ChildR2Element'].replace('', None).combine_first(relations_df['R2Element'])
        relations_df['R2ElementID'] = relations_df['ChildR2ElementID'].replace('', None).combine_first(relations_df['R2ElementID'])
        relations_df = relations_df.drop(['ChildR2Element', 'ChildR2ElementID'], axis=1)    

    # check for duplicate relation - r2element combinations
    dup_check = relations_df.duplicated(subset=['Relation', 'R2Element'], keep=False)
    if dup_check.any() == True:
        logger.critical('Duplication was found for Relation + R2Element combination in relations_df.')
        logger.debug(relations_df[dup_check].to_dict())
        raise RuntimeError('relations_df cannot contain duplicated Relation + R2Element pairs.')
    
    # normalize values to make sql safe
    relations_df[[R1ELEMENT_COL, RELATION_COL, R2ELEMENT_COL]] = (
        relations_df[[R1ELEMENT_COL, RELATION_COL, R2ELEMENT_COL]]
        .map(_normalize_value)
    )
    relation_instances_df[R2ELEMENT_COL] = relation_instances_df[R2ELEMENT_COL].apply(_normalize_value)
    
    # create rename map
    duplicates = relations_df[relations_df[R2ELEMENT_COL].duplicated(keep=False)]
    duplicates[R2ELEMENT_COL] = duplicates[RELATION_COL] + "_" + duplicates[R2ELEMENT_COL]

    rename_map = pd.Series(duplicates[R2ELEMENT_COL].values,index=duplicates[RELATIONID_COL]).to_dict()
    
    self_ref = relations_df[relations_df[R1ELEMENT_COL] == relations_df[R2ELEMENT_COL]]
    self_ref[R2ELEMENT_COL] = self_ref[RELATION_COL] + "_" + self_ref[R2ELEMENT_COL]
    
    rename_map.update(pd.Series(self_ref[R2ELEMENT_COL].values,index=self_ref[RELATIONID_COL]).to_dict())
    
    # rename columns
    relations_df[R2ELEMENT_COL] = relations_df[RELATIONID_COL].map(rename_map).fillna(relations_df[R2ELEMENT_COL])
    relation_instances_df[R2ELEMENT_COL] = relation_instances_df[RELATIONID_COL].map(rename_map).fillna(relation_instances_df[R2ELEMENT_COL])
    
    return relations_df, relation_instances_df


def _create_property_table(
    properties_df: pd.DataFrame,
    property_instances_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Renames the property names so they are SQL safe.
    Pivots the property instances table so the properties are on the column axis.
    Ensures a column exists for every property of the element.
    """
    property_instances_df = property_instances_df.copy()
    # Get all unique properties, throw warning if it is empty
    unique_properties_list = properties_df[PROPERTY_COL].apply(_normalize_value).unique().tolist()
    if len(unique_properties_list) == 0:
        logger.warning("No properties found in properties report part.")
    if property_instances_df.shape[0] == 0:
        logger.warning("No property instanes found in property instances report part.")

    # normalize
    property_instances_df[PROPERTY_COL] = property_instances_df[PROPERTY_COL].apply(_normalize_value)
    try:
        pivot_property_instances_df = property_instances_df.pivot(index=R1INSTANCEID_COL, columns=PROPERTY_COL, values=PROPERTYINSTANCE_COL).rename_axis(columns=None)
    except ValueError:
        logging.exception("Failed to pivot table, likely due to duplicates property names.")
        raise

    return pivot_property_instances_df.reindex(columns=unique_properties_list, fill_value='')


def _create_property_elements_table(
    relations_df: pd.DataFrame,
    relations_instances_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Filters on cardinality :1 and relation name 'Heeft property'
    Pivots the relation_instances_df so the R2Element names are on the column axis.
    Ensures a column exists for each R2Element.
    """
    logger.debug('Start processing create property elements table')

   # filter to only have :1 cardinality and 'heeft_property' relations
    property_relations_df = relations_df[relations_df[RELATION_COL].str.contains('heeft_property', na=False)].copy()
    property_relations_df = _filter_cardinality(df=property_relations_df, cardinality='one')
    property_relations_instances_df = relations_instances_df[relations_instances_df[RELATIONID_COL].isin(property_relations_df[RELATIONID_COL])].copy()

    # create list with all to property relations
    property_relations_list = property_relations_df[R2ELEMENT_COL].tolist()
    
    # pivot table so R2Element are on the column axis
    relation_elements = (
            property_relations_instances_df
            .pivot(index=R1INSTANCEID_COL, columns=R2ELEMENT_COL, values=R2INSTANCEID_COL)
            .reindex(columns=property_relations_list)
            .rename_axis(columns=None)
           )
       
    return relation_elements


def _create_to_one_relations_table(
    relations_df: pd.DataFrame,
    relations_instances_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Filters on cardinality :1 and relation name != 'Heeft property'
    Add the suffix '_guid' to each R2Element.
    Pivots the relation_instances_df so the R2Element names are on the column axis.
    Ensures a column exists for each R2Element.
    """
    logger.debug('Start processing create to one relations elements table')

    # filter to only have :1 cardinality and not 'heeft_property' relations
    relations_one_df = relations_df[~relations_df[RELATION_COL].str.contains('heeft_property', na=False)].copy()
    relations_one_df = _filter_cardinality(df=relations_one_df, cardinality='one')
    relations_instances_one_df = relations_instances_df[relations_instances_df[RELATIONID_COL].isin(relations_one_df[RELATIONID_COL])].copy()

    # create list with all to one relations
    relations_one_list = [f"{v}_guid" for v in relations_one_df[R2ELEMENT_COL]]

    # add _guid suffix to all R2Elements in the instances df
    relations_instances_one_df[R2ELEMENT_COL] = relations_instances_one_df[R2ELEMENT_COL] + "_guid" 
    
    # pivot table so R2Element are on the column axis
    relation_elements = (
            relations_instances_one_df
            .pivot(index=R1INSTANCEID_COL, columns=R2ELEMENT_COL, values=R2INSTANCEID_COL)
            .reindex(columns=relations_one_list)
            .rename_axis(columns=None)
        )
    
    return relation_elements


def _create_link_tables(
    r1_element: str,
    relations_df: pd.DataFrame,
    relations_instances_df: pd.DataFrame
) -> Dict[str, pd.DataFrame]:
    """
    Filters on cardinality :n
    Create a table for each R2Element with columns for R1ElementID and R2ElementID
    The names of these columns should be the element names with suffix _guid.
    The table name should be equal to raw_relatics__{R1Element}_{R2Element}.
    Ensures a link table exists for each R2Element.
    """
    filtered_relations_df = _filter_cardinality(relations_df, "many")
    filtered_relation_instances_df = _filter_cardinality(relations_instances_df, "many")

    link_tables = {}

    for r2_element in filtered_relations_df[R2ELEMENT_COL]:

        table_name = f"raw_relatics__{r1_element}_{r2_element}"

        mask = filtered_relation_instances_df[R2ELEMENT_COL] == str(r2_element)

        table_df = filtered_relation_instances_df.loc[
            mask,
            [R1INSTANCEID_COL, R2INSTANCEID_COL]
        ].reset_index(drop=True)

        link_tables[table_name] = table_df.rename(columns={
            R1INSTANCEID_COL: f"{r1_element}_guid",
            R2INSTANCEID_COL: f"{r2_element}_guid"
        })

    return link_tables


def _is_df_empty(df: pd.DataFrame) -> bool:
    """
    Detects a table that represents 'no data'. This can arrive either as a
    genuine zero-row DataFrame, or as a single row where every value is null
    (the placeholder row the Relatics export returns when there are no
    relations, or no relation instances, for an element).
    """
    if df.empty:
        return True
    if len(df) == 1 and df.iloc[0].isna().all():
        return True
    return False


def _filter_cardinality(
    df: pd.DataFrame,
    cardinality: Literal["many", "one"]
) -> pd.DataFrame:
    """
    Takes a Dataframe and filters on cardinality column
    based on cardinality argument it either filters :n caridinality
    or :1 cardinality
    """
    df = df.copy()
    df[CARDINALITY_COL] = df[CARDINALITY_COL].map(
        lambda x: ":n"
        if "n" in str(x).split(":")[-1]
        else ":1"
    )

    if cardinality == "many":
        return df[df[CARDINALITY_COL] == ":n"]

    else:
        return df[df[CARDINALITY_COL] == ":1"]


def _normalize_value(val: str, max_length: int = 63) -> str:
    """
    Function that takes an input string and normalizes the data so it can safely be used in downstream applications.
    Returns: Sanatized string without any special characters.
    """
    if pd.isna(val) or val is None:
        return ""

    val = str(val)
    val = val.replace("&", "_en_").replace("€", "_euro_").replace("+", "_plus_")

    # Normalize Unicode -> ASCII (e.g. é -> e)
    val = unicodedata.normalize("NFKD", val)
    val = val.encode("ascii", "ignore").decode("ascii")

    # Lowercase
    val = val.lower()

    # Replace invalid characters with underscore
    val = re.sub(r"[^a-z0-9_]", "_", val)

    # Collapse multiple underscores
    val = re.sub(r"_+", "_", val)

    # Strip leading/trailing underscores
    val = val.strip("_")

    # Handle empty string or leading digit
    if not val:
        logger.debug("input value is empty returning empty string.")
        return ""
    if val[0].isdigit():
        val = f"no_num_{val}"

    # Trim to max length (Postgres default = 63)
    return val[:max_length]