import pandas as pd
import logging
from typing import Dict

from src.processing.schema import SCHEMA

def normalize_tables(
    tables: Dict[str, pd.DataFrame],
    schema: Dict[str, dict] = SCHEMA
) -> Dict[str, pd.DataFrame]:
    """ 
    Function that takes a dict of tables and adds to each 
    table the unrequired columns according to the schema, 
    if they are not present.
    """
    return tables

def is_valid_schema(
    tables: Dict[str, pd.DataFrame],
    schema: Dict[str,dict] = SCHEMA
) -> None:
    """
    Checks tables against schema and returns validation report.
    
    Raises: error when the scheama is not fully satisfied.
    """

    report = {
        "is_valid": False 
    }