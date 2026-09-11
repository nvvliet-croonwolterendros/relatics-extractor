from collections import defaultdict
import pandas as pd
import itertools
import xml.etree.ElementTree as ET

def parse_xml(root:ET.Element, report_part:str) -> pd.DataFrame:
    """Function to convert a relatics report part into a pandas DataFrame.

    Relatics report parts can be deeply nested, this function recusively unpacks the XML and returns a single DataFrame.

    Args:
        root (xml.etree.ElementTree): The complete xml.etree.ElementTree xml as obtained from the relatics webservice. Can be easily obtained from the RelaticsClient.
        report_part: Specific report part to unpack into a pandas dataframe.

    Returns:
        df: An unpacked pandas DataFrame of a specific report part.

    """
    start_element = root.find(report_part)
    
    nested_rows = []
    
    if start_element is not None:
        nested_rows.append(_parse_xml_to_dict(start_element=start_element))
        
    unpacked_rows = []
    
    for row in nested_rows:
        unpacked_rows.extend(_recursive_unpack(row))
    
    df = pd.DataFrame(unpacked_rows)
    
    df.columns = [col.split('.')[-1] for col in df.columns]

    return df

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
    
