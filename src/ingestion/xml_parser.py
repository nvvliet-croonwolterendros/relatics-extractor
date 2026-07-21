from collections import defaultdict
import pandas as pd
import itertools
import xml.etree.ElementTree as ET

def parse_xml(root:ET.Element, report_part:str) -> pd.DataFrame:
    start_element = root.find(report_part)
    
    nested_rows = []
    
    if start_element:
        nested_rows.append(_parse_xml_to_dict(start_element=start_element))
        
    unpacked_rows = []
    
    for row in nested_rows:
        unpacked_rows.extend(_recursive_unpack(row))
    
    df = pd.DataFrame(unpacked_rows)
    
    df.columns = [col.split('.')[-1] for col in df.columns]

    return df

def parse_icon_xml(root:ET.Element) -> tuple[pd.DataFrame, str]:
    documents = root.find("Documents")
    zipbase64 = None
    if documents is not None and documents.text:
        zipbase64 = documents.text
        del documents # manually deallocate memory as the file can be large i dont want to wait for the GC.
    elif zipbase64 is None:
        raise ValueError("No Document tag found or tag is empty")
    # Get the table for the icons as well as it will be needed for renaming
    df = parse_xml(root=root, report_part="Data")
    return df, zipbase64
    
def _parse_xml_to_dict(start_element):
    dictionary = defaultdict(list)

    # Collect all direct children of the current element
    for child_element in start_element:
        dictionary[child_element.tag].append(child_element)

    # Process collected elements
    for child_tag in list(dictionary.keys()):
        unpacked_element_list = []
        for child_element in dictionary[child_tag]:
            unpacked_element = child_element.attrib

            # Recurse if the element has children
            if list(child_element):
                children_dict = _parse_xml_to_dict(child_element)
                if children_dict:
                    unpacked_element.update(children_dict)

            # If we got something meaningful, keep it
            if unpacked_element:
                unpacked_element_list.append(unpacked_element)

        dictionary[child_tag] = unpacked_element_list

    return dict(dictionary)

def _recursive_unpack(nested_row):
    """Recursively unpack a nested dict with list-of-dict values into flat records."""
    base_record = {}
    unpacked_lists = []

    for key, value in nested_row.items():
        if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            # Recursively unpack each item in the list
            new_list = []
            for item in value:
                flattened_items = _recursive_unpack(item)
                for flat in flattened_items:
                    # Add prefix to each key
                    prefixed = {f"{key}.{k}": v for k, v in flat.items()}
                    new_list.append(prefixed)
            unpacked_lists.append(new_list)
        elif isinstance(value, dict):
            # Recursively flatten the nested dict
            nested = _recursive_unpack(value)
            for flat in nested:
                base_record.update({f"{key}.{k}": v for k, v in flat.items()})
        elif value:
            base_record[key] = value

    # If there are unpacked lists, compute cartesian product
    if unpacked_lists:
        result = []
        for combo in itertools.product(*unpacked_lists):
            combined = dict(base_record)  # copy base record
            for item in combo:
                combined.update(item)
            result.append(combined)
        return result
    else:
        return [base_record]
    
