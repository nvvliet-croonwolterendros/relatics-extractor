import pandas as pd
from typing import Dict, Literal
import unicodedata
import re
import logging

logger = logging.getLogger(__name__)

COLUMN_MAP = {
    
}

R1INSTANCE_COL = "R1Instance"
R1INSTANCEID_COL = "R1InstanceID"

PROPERTY_COL = "Property"
PROPERTYINSTANCE_COL = "PropertyInstance"

CARDINALITY_COL = "Cardinality"

R2ELEMENT_COL = "R2Element"
R2ELEMENTID_COL = "R2ElementID"

R2INSTANCE_COL = "R2Instance"
R2INSTANCEID_COL = "R2InstanceID"

BASE_COLS = ["guid", "naam", "omschrijving", "richtext"]

def create_element_tables(
    tables: Dict[str, pd.DataFrame],
    column_map: Dict[str,str] = COLUMN_MAP 
) -> Dict[str, pd.DataFrame]:
    """
    Takes the 6 input tables for a given element.
    Transform the reltions table. 
    Create the property_table, property_elements_table and to_one_relations_table.
    Set R1InstanceID as the index on element_instances_df.
    Merge property_table, property_elements_table and to_one_relations_table on element_instances_df on R1InstanceID as index.
    Rename columns of the element table using the COLUMN_MAP.
    Create the link tables.
    Returns the element table and required link tables for the element.
    """
    pass
    
def _transform_relations_table(
    relations_df: pd.DataFrame,
    relations_instances_df: pd.DataFrame
) -> pd.DataFrame: 
    """
    In the RelationInstances table Coalesce R2ElementID, R2Element with ChildR2Element, ChildR2Elemnent when child columns are not empty.
    Raise error if there are duplicate R2Element Relation combinations in the Relations table.
    Using the Relations table create a rename-map duplicate R2Elements to {Relation}_{R2Element}.
    Rename R2Elements in the RelationInstances table using the rename map.
    In the Relations table Renames R2Elements to make them SQL safe.
    
    Important: the R2Element should also be renamed when the R2Element = R1Element

    Rename mapping must be done in both relations_df and relation_instance_df
    """

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
    relations_df = relations_df.copy()
    relations_instances_df = relations_instances_df.copy()

    logger.debug('Start processing create property elements table')
    # Filter to only have :1 cardinality and 'Heeft property' relations
    prop_relations = relations_df[relations_df['Relation'].str.contains('Heeft property', na=False)]
    prop_relations = _filter_cardinality(df=prop_relations, cardinality='one')

    # Get all property instance relations by filtering R2 element being the property name, then pivot so that the index is the R1InstanceID for later joins.
    prop_relation_instances = relations_instances_df[relations_instances_df[R2ELEMENT_COL].isin(prop_relations[R2ELEMENT_COL])]

    # Raise exception if R1InstanceID + R2Element combination is not unique
    if prop_relation_instances.duplicated(subset=[R1INSTANCEID_COL, R2ELEMENT_COL]).any():
        raise ValueError("Duplicate entries found for R1InstanceID and R2Element combination.")

    # Handle empty instances edge case before pivoting
    if prop_relation_instances.empty:
        logger.info('No property instances found, returning empty df.')
        return pd.DataFrame(columns=prop_relations[R2ELEMENT_COL].unique()).rename_axis(R1INSTANCEID_COL)

    return prop_relation_instances.pivot(index=R1INSTANCEID_COL, columns=R2ELEMENT_COL, values=R2INSTANCE_COL).reindex(columns=prop_relations[R2ELEMENT_COL].unique()).rename_axis(columns=None)
    
def _create_to_one_relations_table(
    relations_df: pd.DataFrame,
    relations_instances_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Filters on cardinality :1 and relation name != 'Heeft property'
    Pivots the relation_instances_df so the R2Element names are on the column axis.
    Ensures a column exists for each R2Element.
    Add the suffix '_guid' to each column except R1InstanceID.
    """
    relations_df = relations_df.copy()
    relations_instances_df = relations_instances_df.copy()

    logger.debug('Start processing create to one relations elements table')
    # Filter to only have :1 cardinality and not 'Heeft property' relations
    relations = relations_df[~relations_df['Relation'].str.contains('Heeft property', na=False)]
    relations = _filter_cardinality(df=relations, cardinality='one')

    # Get a new column where you construct the column name used later. it's easier to do it here as to ensure all relations are always present.
    # Check if a R2Element occurs multiple times, if yes add the relation name in front. if not do nothing. For both cases append_guid.

    n_relationids_per_R2element = relations.groupby('R2Element')['RelationID'].transform('nunique')
    needs_prefix = n_relationids_per_R2element > 1 # This is a mask to be used for later transformations.

    relations['R2Element_resolved'] = relations['R2Element'] + "_guid"
    # Use the mask created above to indentify the rows that need a prefix and add this prefix
    relations.loc[needs_prefix, 'R2Element_resolved'] = (
        relations.loc[needs_prefix, 'Relation'] + '_' + relations.loc[needs_prefix, 'R2Element']
    )
    # Create the mapping for the element table for later, apply just before the pivot and use this column for the pivor instead of R2Element.
    columnname_mapping_R2Element = relations.set_index('RelationID')['R2Element_resolved'].to_dict()

    # Create dataframe with relation instances based on the mask generated above. This table now contains all to one relations that are not preperty elements.
    relation_elements = relations_instances_df[relations_instances_df['RelationID'].isin(relations['RelationID'])]
    relation_elements['R2Element_resolved'] = relation_elements['RelationID'].map(columnname_mapping_R2Element)
    # Pivot so that the index is R1InstanceID and columns are the 
    relation_elements = relation_elements.pivot(index='R1InstanceID', columns='R2Element_resolved', values='R2InstanceID').reindex(columns=relations['R2Element_resolved']).rename_axis(columns=None)
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

def _filter_cardinality(
    df: pd.DataFrame,
    cardinality: Literal["many", "one"]
) -> pd.DataFrame:
    """
    Takes a Dataframe and filters on cardinality column
    based on cardinality argument it either filters :n caridinality
    or :1 cardinality
    """
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
    val = val.replace("&", "_en_").replace("€", "_euro_").replace("+", "_plus_")
    # Normalize Unicode → ASCII (e.g. é → e)
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

    # Ensure it doesn't start with a digit
    if not val or val[0].isdigit():
        val = f"no_num_{val}"

    # Trim to max length (Postgres default = 63)
    return val[:max_length]