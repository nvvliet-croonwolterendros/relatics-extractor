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
    element_instances_df = tables["ElementInstances"].copy()
    properties_df = tables["Properties"].copy()
    property_instances_df = tables["PropertyInstances"].copy()
    relations_df = tables["Relations"].copy()
    relations_instances_df = tables["RelationInstances"].copy()

    # --- Transform the relations table(s) ---
    relations_df, relations_instances_df = _transform_relations_table(
        relations_df, relations_instances_df
    )
    # --- Build the three sub-tables to merge onto element_instances_df ---
    property_table = _create_property_table(properties_df, property_instances_df)
    property_elements_table = _create_property_elements_table(relations_df, relations_instances_df)
    to_one_relations_table = _create_to_one_relations_table(relations_df, relations_instances_df)

    # --- Set index and merge ---
    element_table = element_instances_df.set_index(R1INSTANCEID_COL)

    for df in [property_table, property_elements_table, to_one_relations_table]:
        if df is not None and not df.columns.empty:
            element_table = element_table.merge(
                df, 
                left_index=True, 
                right_index=True, 
                how="left"
            )

    # element_table = element_instances_df.join(
    #     [property_table, property_elements_table, to_one_relations_table],
    #     how="left",
    # )

    # Bring R1InstanceID back out as a normal column before renaming,
    # since column_map may rename it (e.g. to a guid-style name).
    element_table = element_table.reset_index()
    # element_table = element_table.rename(columns=column_map)

    # --- Build link (:n) tables ---
    link_tables = _create_link_tables(r1_element, relations_df, relations_instances_df)

    result: Dict[str, pd.DataFrame] = {
        f"raw_relatics__{r1_element}": element_table
    }
    result.update(link_tables)

    return result


def _is_placeholder_empty(df: pd.DataFrame) -> bool:
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

    Empty-input handling:
    - If relations_df is empty (no relations at all are defined for the
      element), there is nothing to coalesce, dedupe, or self-reference.
      Both outputs are reduced to genuine zero-row DataFrames with the
      expected columns and returned immediately.
    - If relations_df has data but relations_instances_df is empty (relations
      are defined, but no instances of any of them exist yet), relations_df
      is still fully processed (coalesced, deduped, SQL-safe renamed) but
      relations_instances_df is reduced to a genuine zero-row DataFrame with
      a resolved, SQL-safe R2Element column. This means downstream pivots,
      joins, and link-table creation come out empty instead of raising.
    """
    relations_df = relations_df.copy()
    relations_instances_df = relations_instances_df.copy()

    relations_df['Relation']

    relations_is_empty = _is_placeholder_empty(relations_df)
    relations_instances_is_empty = _is_placeholder_empty(relations_instances_df)

    if relations_is_empty:
        # No relations exist at all for this element - nothing to coalesce,
        # dedupe, or self-reference. Normalize both frames to genuine
        # zero-row DataFrames with the expected columns so downstream code
        # (pivots, joins, link-table creation) can treat this the same way
        # it treats any other empty result.
        empty_relations_df = relations_df.iloc[0:0].drop(
            columns=['ChildR2Element', 'ChildR2ElementID'], errors='ignore'
        )
        empty_relations_instances_df = relations_instances_df.iloc[0:0].drop(
            columns=['Relation'], errors='ignore'
        )
        if R2ELEMENT_COL in empty_relations_instances_df.columns:
            empty_relations_instances_df[R2ELEMENT_COL] = empty_relations_instances_df[R2ELEMENT_COL].apply(_normalize_value)
        return empty_relations_df, empty_relations_instances_df

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
    relations_df.loc[mask_duplicated_R2Element, 'R2Element'] = relations_df.loc[mask_duplicated_R2Element, 'Relation'].astype(str) + '_' + relations_df.loc[mask_duplicated_R2Element, 'R2Element'].astype(str)

    mask_duplicated_R2Element_after_rename = relations_df['R2Element'].duplicated(keep=False)
    if mask_duplicated_R2Element_after_rename.any():
        logger.critical('Renaming duplicate R2Elements to Relation_R2Element produced new duplicate R2Element values in relations_df.')
        logger.debug(relations_df[mask_duplicated_R2Element_after_rename].to_dict())
        raise RuntimeError('relations_df cannot contain duplicated R2Element values after Relation_R2Element renaming.')

    if relations_instances_is_empty:
        # Relations are defined, but no instances of any of them exist yet.
        # Skip the merge/self-reference logic entirely (there is nothing to
        # match against) and produce a genuine zero-row relations_instances_df
        # with a resolved, SQL-safe R2Element column.
        relations_df['R2Element'] = relations_df['R2Element'].apply(_normalize_value)
        empty_relations_instances_df = relations_instances_df.iloc[0:0].drop(columns=['Relation'], errors='ignore')
        empty_relations_instances_df[R2ELEMENT_COL] = empty_relations_instances_df[R2ELEMENT_COL].apply(_normalize_value)
        return relations_df, empty_relations_instances_df

    # === Parse relations_instances_df ===
    # No need to implement the rename logic again. The R2Element and relation name columns will be joined from relation_df to relation_instances_df
    # The only check needed now is if R1Element == R2Element coming from relation_df. If the case the relation name will be added in front.
    # Check again if the relationID + R2Element name are unique if not again throw an error.

    # NOTE: 'Relation' is expected to come FROM this merge (relations_df is
    # the source of truth for it), not from relations_instances_df itself -
    # real RelationInstances input does not carry its own 'Relation' column
    # at this point. We still defensively drop it first in case a caller
    # ever passes one in, so the merge can never collide it into
    # Relation_x/Relation_y (which would break the self-reference logic
    # below, which expects a plain 'Relation' column).
    # relations_instances_df = relations_instances_df.drop(columns=['Relation'], errors='ignore')
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
        relations_instances_df.loc[self_ref_mask, 'Relation'].astype(str) + '_' + relations_instances_df.loc[self_ref_mask, 'New_R2Element'].astype(str)
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

    # If all of this passes now is the time to rename the R2Element columns to be sql safe
    relations_instances_df['R2Element'] = relations_instances_df['R2Element'].apply(_normalize_value)
    relations_df['R2Element'] = relations_df['R2Element'].apply(_normalize_value)

    return relations_df, relations_instances_df


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
    logger.debug('Start processing create to one relations elements table')

    # Filter to only have :1 cardinality and not 'Heeft property' relations
    relations = relations_df[~relations_df['Relation'].str.contains('Heeft property', na=False)].copy()
    relations = _filter_cardinality(df=relations, cardinality='one')

    # R2Element is already globally unique and SQL-safe after the transform, so just add the '_guid' suffix.
    relations['R2Element_resolved'] = relations['R2Element'] + '_guid'

    # relations_instances_df['R2Element'] already matches relations_df['R2Element'] via RelationID,
    # so we can derive the resolved column name directly without re-mapping.
    relation_elements = relations_instances_df[
        relations_instances_df['RelationID'].isin(relations['RelationID'])
    ].copy()
    relation_elements['R2Element_resolved'] = relation_elements['R2Element'] + '_guid'

    relation_elements = (
        relation_elements
        .pivot(index='R1InstanceID', columns='R2Element_resolved', values='R2InstanceID')
        .reindex(columns=relations['R2Element_resolved'])
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