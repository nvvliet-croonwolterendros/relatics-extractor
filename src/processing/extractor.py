import pandas as pd
import unicodedata
import re
import xml.etree.ElementTree as ET
from typing import Dict
from src.ingestion.xml_parser import parse_xml

class RelaticsExtractor:
    
    def __init__(self, root: ET.Element, workspace_id: str) -> None:
        self.elem_report_part = "Element"
        self.elem_insts_report_part = "ElementInstances"
        self.props_report_part = "Properties"
        self.prop_insts_report_part = "PropertyInstances"
        self.rels_report_part = "Relations"
        self.rel_insts_report_part = "RelationInstances"
        self.r1_element_col = "R1Element"
        self.r1_element_id_col = "R1ElementID"
        self.r1_instance_col = "R1Instance"
        self.r1_instance_description_col = "R1InstanceDescription"
        self.r1_instance_richtext_col = "R1InstanceRichtext"
        self.r1_instance_id_col = "R1InstanceID"
        self.r2_element_col = "R2Element"
        self.r2_element_id_col = "R2ElementID"
        self.r2_instance_col = "R2Instance"
        self.r2_instance_id_col = "R2InstanceID"
        self.property_col = "Property"
        self.property_value_col = "PropertyValue"
        self.relation_col = "Relation"
        self.relation_id_col = "RelationID"
        self.cardinality_col = "Cardinality"
        self.base_col_map = {
            self.r1_instance_id_col: "guid",
            self.r1_instance_col: "naam",
            self.r1_instance_description_col: "omschrijving",
            self.r1_instance_richtext_col: "richtext",
        }
        self.base_cols = ["guid", "naam", "omschrijving", "richtext"]
        
        self.workspace_id = workspace_id
        self.elem_df = parse_xml(root,self.elem_report_part)
        self.elem_insts_df = parse_xml(root,self.elem_insts_report_part)
        self.props_df = parse_xml(root,self.props_report_part)
        self.prop_insts_df = parse_xml(root,self.prop_insts_report_part)
        self.rels_df = parse_xml(root,self.rels_report_part)
        self.rel_insts_df = parse_xml(root,self.rel_insts_report_part)

    def create_element_tables(self) -> Dict[str,pd.DataFrame]:
        # create table dict
        tables = {}
        
        # get element
        element = self._get_element(self.elem_df)
            
        # get element instances
        elem_insts_df = self._get_elem_instances(self.elem_insts_df)
        
        # get properties
        properties = self._get_properties(self.props_df)
        
        # get property instances
        prop_insts_df = self._get_prop_instances(self.prop_insts_df, properties) 
        
        # create rename map
        rename_map = self._create_rename_map(self.rels_df)
        
        # get relations
        rels_one, rels_many, prop_rels_one = self._get_relations(self.rels_df, rename_map)
        
        # get relation instances
        rel_insts_one_df, rel_insts_many_df, prop_rel_insts_one_df = self._get_relation_instances(self.rel_insts_df, rename_map)    
        
        # transform to one relation instances
        rel_insts_one_df = self._transform_df(
            rel_insts_one_df,
            values=self.r2_instance_id_col,
            columns=self.r2_element_col,
            col_list=rels_one
        )
        
        # transform to one property relation instances
        prop_rel_insts_one_df = self._transform_df(
            prop_rel_insts_one_df,
            values=self.r2_instance_col,
            columns=self.r2_element_col,
            col_list=prop_rels_one
        )
        
        # make sure all columns are type str
        elem_insts_df = elem_insts_df.astype(str)
        prop_insts_df = prop_insts_df.astype(str)
        prop_rel_insts_one_df = prop_rel_insts_one_df.astype(str)
        rel_insts_one_df = rel_insts_one_df.astype(str)
    
        # merge element df with properties and to one relations
        table_name = f"raw_relatics__{element}"
        element_table = (
            elem_insts_df
            .merge(prop_insts_df, on=["guid", "naam"], how="left", suffixes=("", "_DROP"))
            .merge(prop_rel_insts_one_df, on=["guid", "naam"], how="left", suffixes=("", "_DROP"))
            .merge(rel_insts_one_df, on=["guid", "naam"], how="left", suffixes=("", "_DROP"))
        )
        element_table = element_table.loc[:, ~element_table.columns.str.endswith("_DROP")]
        element_table["workspace_id"] = self.workspace_id
        tables[table_name] = element_table

        # get link tables
        for r2_element in rels_many:
            table_name = f"raw_relatics__{element}_{r2_element}"
            
            tables[table_name] = self._get_link_table(
                rel_insts_many_df,
                element,
                r2_element
            )
        
        return tables
    
    def create_icon_table(self) -> pd.DataFrame:
        # TODO implement in reverse order the entire extraction so:
        # TODO in this file you make the table in this function + parse xml using xml_parser.parse_xml(res, "Data")
        # TODO in order to obtain the xml you need to do a request using client.get_request(workspace_id="210b2918-b359-4892-a23b-bf96ad23d82f", operation="icons")
        # TODO do a request for the icons which contain 'document' tag which is the base64 of a zip, then extract this zip in a temporary folder. persumably you can get the base64 with xml_parser.parse_xml(res, "documents")
        # TODO you now should have the table with at least element name, and filename. encode the filename to a base64 and add to the table.
        # TODO calculate sha256 checksum from the base64 and add it to the table
        # TODO return table for upload
        pass

    def _get_link_table(self, df: pd.DataFrame, element:str, r2_element: str):
        if self.r2_element_col in df.columns and r2_element in df[self.r2_element_col].unique():     
            filtered = df[df[self.r2_element_col] == r2_element]
            link_table_df = self._create_link_table(filtered)

        else:
            link_table_df = pd.DataFrame(columns=[f"{element}_guid",f"{r2_element}_guid"])
            
        # add workspace id column
        link_table_df["workspace_id"] = self.workspace_id
            
        return link_table_df
                
    def _get_relation_instances(self, df: pd.DataFrame, rename_map: dict):
        if self.cardinality_col in df.columns:
            # rename r2 elements
            df[self.r2_element_col] = df[self.relation_id_col].map(rename_map).fillna(df[self.r2_element_col])
            
            # normalize r1 and r2 elements
            df = self._normalize_cols(df,cols=[self.r1_element_col,self.r2_element_col])
            
            # split into to one and to many relations
            rel_insts_one_df, rel_insts_many_df = self._split_cardinalty(df)
            
            # split to one relations into property relations and normal relations
            prop_rel_insts_one_df, rel_insts_one_df = self._split_rels(rel_insts_one_df)
            
            # rename r2 element for to one relations (will be used as column names)
            rel_insts_one_df[self.r2_element_col] = rel_insts_one_df[self.r2_element_col] + "_guid"     
        
        else:
            rel_insts_one_df = pd.DataFrame()
            rel_insts_many_df = pd.DataFrame()
            prop_rel_insts_one_df = pd.DataFrame()
            
        return rel_insts_one_df, rel_insts_many_df, prop_rel_insts_one_df
            
    def _get_relations(self, df: pd.DataFrame, rename_map: dict):
        if self.cardinality_col in df.columns:
            # rename r2 elements
            df[self.r2_element_col] = df[self.relation_id_col].map(rename_map).fillna(df[self.r2_element_col])
            
            # normalize r1 and r2 elements
            df = self._normalize_cols(df,cols=[self.r1_element_col,self.r2_element_col])
            
            # split into to one and to many relations
            rels_one_df, rels_many_df = self._split_cardinalty(df)
            
            # split to one relations into property relations and normal relations
            prop_rels_one_df, rels_one_df = self._split_rels(rels_one_df)
            
            # create list for each relationship (will be used as column names)
            rels_one = [f"{self._normalize_value(v)}_guid" for v in rels_one_df[self.r2_element_col]]
            rels_many = rels_many_df[self.r2_element_col].map(self._normalize_value).to_list()
            prop_rels_one = prop_rels_one_df[self.r2_element_col].map(self._normalize_value).to_list()
        
        else: 
            rels_one = []
            rels_many = []
            prop_rels_one = []

        return rels_one, rels_many, prop_rels_one
        
    def _get_element(self, df: pd.DataFrame):
        """Returns element as normalized string. Raises error if element is not found"""
        element = df[self.r1_element_col][0]
        
        if not element:
            raise
        
        else:
            return self._normalize_value(str(element))
                   
    def _get_elem_instances(self, df: pd.DataFrame):
        """Ensures elem_insts_df consists of the base cols"""
        return (
            df
            .rename(columns=self.base_col_map)
            .reindex(columns=self.base_cols)
        )

    def _get_properties(self, df: pd.DataFrame):
        # Get normalized property names 
        return (
            df
            .get(self.property_col, pd.Series(dtype=object))
            .map(self._normalize_value)
            .dropna()
            .unique()
            .tolist()
        ) 
    
    def _get_prop_instances(self, df: pd.DataFrame, properties: list):      
        # Ensure prop_insts_df is of the right format
        df = self.prop_insts_df.reindex(columns=[
            self.r1_instance_id_col,
            self.r1_instance_col,
            self.property_col,
            self.property_value_col
        ])
        
        # Check for duplicates
        index_cols = [
            self.r1_instance_id_col,
            self.r1_instance_col
        ]
        
        if df.duplicated(subset=index_cols + [self.property_col]).any():
            raise ValueError("Duplicate entries found in property instances")
        
        # Normalize property_col
        df = self._normalize_cols(
            df,[self.property_col]
        )
        
        # Pivot prop_insts_df
        df = (
            df.pivot(
                values=self.property_value_col,
                columns=self.property_col,
                index=index_cols
            )
            .rename_axis(columns=None)
            .reset_index()
        )
        
        # Ensure all expected columns exist
        return (
            df
            .rename(columns=self.base_col_map)
            .reindex(
                columns= self.base_cols + properties,
                fill_value=""
            )
        )

    @staticmethod
    def _normalize_value(val: str, max_length: int = 63) -> str:
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

    def _normalize_cols(self, df: pd.DataFrame, cols: list): 
        for col in cols:
            df[col] = df[col].astype(str).apply(self._normalize_value)
            
        return df
            
    def _create_rename_map(self, df: pd.DataFrame) -> Dict:
        if self.r2_element_col in df.columns:
            duplicates = df[df[self.r2_element_col].duplicated(keep=False)]
            duplicates[self.r2_element_col] = duplicates[self.relation_col] + "_" + duplicates[self.r2_element_col]

            rename_map = pd.Series(duplicates[self.r2_element_col].values,index=duplicates[self.relation_id_col]).to_dict()
            
            self_ref = df[df[self.r1_element_col] == df[self.r2_element_col]]
            self_ref[self.r2_element_col] = self_ref[self.relation_col] + "_" + self_ref[self.r2_element_col]
            
            rename_map.update(pd.Series(self_ref[self.r2_element_col].values,index=self_ref[self.relation_id_col]).to_dict())
        
        else:
            rename_map = {}
        
        return rename_map

    def _create_link_table(self, df: pd.DataFrame) -> pd.DataFrame:
        
        return df.rename(
            columns={
                self.r1_instance_id_col: df[self.r1_element_col].iloc[0] + "_guid",
                self.r2_instance_id_col: df[self.r2_element_col].iloc[0] + "_guid"
            }
        )[ [df[self.r1_element_col].iloc[0] + "_guid", df[self.r2_element_col].iloc[0] + "_guid"] ]
    
    def _split_cardinalty(self, df: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
        valid = ["0:1","1:1","0:1|1"]
        
        return df[df[self.cardinality_col].isin(valid)], df[~df[self.cardinality_col].isin(valid)]

    def _split_rels(self, df: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
        
        return df[df[self.relation_col] == "Heeft property"], df[df[self.relation_col] != "Heeft property"]
    
    def _transform_df(self, df: pd.DataFrame, values: str, columns: str, col_list: list) -> pd.DataFrame:
        required_columns = {values,columns}
        required_columns.update(self.base_cols)
        
        if required_columns.issubset(df.columns):
            
            df.rename(columns=self.base_col_map)
            
            df = (
                df.pivot(
                    values=values,
                    columns=columns,
                    index=self.base_cols
                )
                .rename_axis(columns=None)
                .reset_index()
            )
            
        else:
            df = pd.DataFrame(columns=["guid","naam"])
        
        missing_cols = [col for col in col_list if col not in df.columns]
        
        for col in missing_cols:
            df[col] = ""
            
        return df