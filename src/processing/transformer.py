import pandas as pd
from typing import Dict

COLUMN_MAP = {
    
}

def create_element_tables(
    tables: Dict[str, pd.DataFrame],
    column_map: Dict[str,str] = COLUMN_MAP 
) -> Dict[str, pd.DataFrame]:
    """
    Takes the 6 input tables for a given element.
    
    In the Relations table Renames R2Elements to make them SQL safe.
    Using the Relations table create a rename-map duplicate R2Elements by adding the (SQL safe) Relation name as a prefix.
    In the RelationInstances table Coalesce R2ElementID, R2Element with ChildR2Element, ChildR2Elemnent when child columns are not empty.
    
    Merge property_table, property_elements_table and to_one_relations_table on relation_instances_df
    
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
) -> pd.DataFrame:
    """
    Filters on cardinality :n
    Create a table for each R2Element with columns for R1ElementID and R2ElementID
    The names of these columns should be the element names with suffix _guid.
    The table name should be equal to {R1Element}_{R2Element}
    Ensures a link table exists for each R2Element.
    """