import pandas as pd
from typing import Dict
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

BASE_COLS = ["guid", "naam", "omschrijving", "richtext"]

def create_element_tables(
    tables: Dict[str, pd.DataFrame],
    column_map: Dict[str,str] = COLUMN_MAP 
) -> Dict[str, pd.DataFrame]:
    """
    Takes the 6 input tables for a given element.
    
    Split the following into seprate function:
        In the Relations table Renames R2Elements to make them SQL safe.
        Using the Relations table create a rename-map duplicate R2Elements by adding the (SQL safe) Relation name as a prefix.
        Check if there are duplicate R2Elements even after renaming.
        Rename R2Elements in the RelationInstances table using the rename map.
        In the RelationInstances table Coalesce R2ElementID, R2Element with ChildR2Element, ChildR2Elemnent when child columns are not empty.
    
    set R1InstanceID as the index on element_instances_df
    Merge property_table, property_elements_table and to_one_relations_table on element_instances_df on R1InstanceID as index
    
    rename columns or the element table using the COLUMN_MAP
    
    Returns the element table and required link tables for the element.
    """
    pass
    
def _create_property_table(
    properties_df: pd.DataFrame,
    property_instances_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Renames the property names so they are SQL safe.
    Pivots the property instances table so the properties are on the column axis.
    Ensures a column exists for every property of the element.
    """
    # Get all unique properties, throw warning if it is empty
    # unique_properties = properties_df.rename(columns=_normalize_value)
    unique_properties_list = properties_df[PROPERTY_COL].apply(_normalize_value).dropna().unique().tolist()
    if len(unique_properties_list) == 0:
        logging.warning("No properties found in properties report part.")

    # normalize 
    property_instances_df[PROPERTY_COL] = property_instances_df[PROPERTY_COL].apply(_normalize_value) 
    try:
        pivot_property_instances_df = property_instances_df.pivot(index=R1INSTANCEID_COL, columns=PROPERTY_COL, values=PROPERTYINSTANCE_COL).rename_axis(columns=None).reset_index()
    except ValueError:
        logging.exception("Failed to pivot table, likely due to duplicates property names.")
        raise
    reindexed_property_instances_df = pivot_property_instances_df.reindex(columns=[R1INSTANCEID_COL] + unique_properties_list, fill_value='')
    return reindexed_property_instances_df
    
def _create_property_elements_table(
    relations_df: pd.DataFrame,
    relations_instances_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Filters on cardinality :1 and relation name 'Heeft property'
    Pivots the relation_instances_df so the R2Element names are on the column axis.
    Ensures a column exists for each R2Element.
    """
    
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