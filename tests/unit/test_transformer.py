import pytest
    
def test_create_property_table_complete_properties():
    """
    Test whether a df with all a column for each property is returned
    in the case all properties exist in the Property column of the input df.
    """
    
def test_create_property_table_incomplete_properties():
    """
    Test whether a df with all a column for each property is returned
    in the case not all properties exist in the Property column of the input df.
    """
    
def test_create_property_elements_table_complete_properties():
    """
    Test whether a df with all a column for each property R2Element is returned
    in the case all R2Elements exist in the Property column of the input df.
    """
    
def test_create_property_elements_table_incomplete_properties():
    """
    Test whether a df with all a column for each property R2Element is returned
    in the case not all R2Elements exist in the Property column of the input df.
    """
    
def test_create_property_elements_table_only_uses_to_one():
    """
    Test whether the function only uses the relations with a :1 cardinality
    """
    
def test_create_property_elements_table_only_uses_property_elements():
    """
    Test whether the function only uses the relations with name 'Heeft property'
    """
    
def test_create_property_elements_table_false_cardinality_to_one():
    """
    Test whether the function give an error when the a :1 cardinality is not 
    truly a :1 cardinality
    """
    
def test_create_property_elements_table_false_cardinality_to_many():
    """
    Test whether the function give an error when the a :n cardinality relation 
    has name 'Heeft property'
    """