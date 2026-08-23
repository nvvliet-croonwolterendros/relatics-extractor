import pandas as pd
from typing import Dict, Literal, Tuple
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
    relations_df = relations_df.copy()
    relations_instances_df = relations_instances_df.copy()

    # === Parse relations_df ===
    # Coalesce ChildR2Element with R2Element
    relations_df['R2Element'] = relations_df['ChildR2Element'].replace('', None).combine_first(relations_df['R2Element'])
    relations_df['R2ElementID'] = relations_df['ChildR2ElementID'].replace('', None).combine_first(relations_df['R2ElementID'])
    relations_df = relations_df.drop(['ChildR2Element', 'ChildR2ElementID'], axis=1)

    # Check if Relation + R2element is always unique. If not, throw an error.
    dup_check = relations_df.duplicated(subset=['Relation', 'R2Element'], keep=False)
    if dup_check.any() == True:
        logger.critical('Duplication was found for Relation + R2Element combination in relations_df.')
        logger.debug(relations_df[dup_check].to_dict())
        raise RuntimeError('relations_df cannot contain duplicated Relation + R2Element pairs.')

    # Rename R2Element to Relation_R2Element if R2Elements are duplicates
    mask_duplicated_R2Element = relations_df['R2Element'].duplicated(keep=False)
    relations_df.loc[mask_duplicated_R2Element,'R2Element'] = relations_df.loc[mask_duplicated_R2Element,'Relation'] + '_' + relations_df.loc[mask_duplicated_R2Element,'R2Element']

    mask_duplicated_R2Element_after_rename = relations_df['R2Element'].duplicated(keep=False)
    if mask_duplicated_R2Element_after_rename.any():
        logger.critical('Renaming duplicate R2Elements to Relation_R2Element produced new duplicate R2Element values in relations_df.')
        logger.debug(relations_df[mask_duplicated_R2Element_after_rename].to_dict())
        raise RuntimeError('relations_df cannot contain duplicated R2Element values after Relation_R2Element renaming.')

    # === Parse relations_instances_df ===
    # No need to implement the rename logic again. The R2Element and relation name columns will be joined from relation_df to relation_instances_df
    # The only check needed now is if R1Element == R2Element coming from relation_df. If the case the relation name will be added in front.
    # Check again if the relationID + R2Element name are unique if not again throw an error.

    relations_instances_df = relations_instances_df.merge(
    relations_df[['RelationID', 'R2ElementID', 'Relation', 'R2Element']].rename(
        columns={'R2Element': 'New_R2Element'}
    ),
    on=['RelationID', 'R2ElementID'],
    how='left'
    )

    unmatched_mask = relations_instances_df['New_R2Element'].isna()
    if unmatched_mask.any():
        logger.critical('relations_instances_df contains RelationID + R2ElementID combinations with no match in relations_df.')
        logger.debug(relations_instances_df[unmatched_mask].to_dict())
        raise RuntimeError('relations_instances_df contains RelationID + R2ElementID combinations with no match in relations_df.')

    # Check for R1Element == R2Element
    self_ref_mask = relations_instances_df['R1Element'] == relations_instances_df['New_R2Element']
    relations_instances_df.loc[self_ref_mask, 'New_R2Element'] = (
        relations_instances_df.loc[self_ref_mask, 'Relation'] + '_' + relations_instances_df.loc[self_ref_mask, 'New_R2Element']
    )

    # As only R1Element is present in the relation instances df, the relations table needs to be updated again after all this to include the R1Element == R2Element case.
    renamed_self_refs = relations_instances_df.loc[self_ref_mask, ['RelationID', 'R2ElementID', 'New_R2Element']].drop_duplicates()

    inconsistent_self_ref_mask = renamed_self_refs.duplicated(subset=['RelationID', 'R2ElementID'], keep=False)
    if inconsistent_self_ref_mask.any():
        logger.critical('Self-reference renaming produced multiple different R2Element names for the same RelationID + R2ElementID combination.')
        logger.debug(renamed_self_refs[inconsistent_self_ref_mask].to_dict())
        raise RuntimeError('Self-reference renaming is inconsistent for at least one RelationID + R2ElementID combination.')

    relations_df_row_count_before_self_ref_merge = len(relations_df)
    relations_df = relations_df.merge(renamed_self_refs, on=['RelationID', 'R2ElementID'], how='left')
    if len(relations_df) != relations_df_row_count_before_self_ref_merge:
        logger.critical('Merging self-reference renames into relations_df changed the number of rows.')
        raise RuntimeError('Merging self-reference renames into relations_df changed the number of rows.')
    relations_df['R2Element'] = relations_df['New_R2Element'].combine_first(relations_df['R2Element'])
    relations_df.drop(columns=['New_R2Element'], inplace=True)
    
    relations_instances_df['R2Element'] = relations_instances_df['New_R2Element']
    relations_instances_df.drop(columns=['New_R2Element', 'Relation'], inplace=True)

    dup_check = relations_df.duplicated(subset=['Relation', 'R2Element'], keep=False)
    if dup_check.any() == True:
        logger.critical('Duplication was found for Relation + R2Element combination in relations_df after self-reference renaming.')
        logger.debug(relations_df[dup_check].to_dict())
        raise RuntimeError('relations_df cannot contain duplicated Relation + R2Element pairs after self-reference renaming.')

    # Check if duplicate names exist in relations_instance_df
    dup_check = relations_instances_df.duplicated(subset=['RelationID', 'R2Element'], keep=False)
    if dup_check.any() == True:
        logger.critical('Duplication was found for RelationID + R2Element combination in relations_instances_df.')
        logger.debug(relations_instances_df[dup_check].to_dict())
        raise RuntimeError('relations_instances_df cannot contain duplicated RelationID + R2Element pairs.')

    # If all of this passes now is the time to rename the R2Element columns to be sql safe
    relations_instances_df['R2Element'] = relations_instances_df['R2Element'].apply(_normalize_value)
    relations_df['R2Element'] = relations_df['R2Element'].apply(_normalize_value)

    return relations_df, relations_instances_df


# TODO: make sure no more changes are made to relations_df and relation_instanced df after this. Also verify the tests.
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