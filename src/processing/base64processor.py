import base64
import hashlib
import io
from pathlib import Path
import zipfile
import pandas as pd

def add_file_metadata_from_base64_zip(df: pd.DataFrame, base64_zip_str: str) -> pd.DataFrame:
    """
    Enter a table containing information about the zipfile. The table should contain info about the element and filename.
    Also enter the base64 encoded zip file.
    This function will first decode the zip-base64 into a bytes object, this will be read into memory.
    A dict will be made so each file only is read once and can then be looked up. 
    """
    if not {"Element", "RelaticsIconFilename"}.issubset(df.columns):
        raise ValueError("Missing required columns: Element, RelaticsIconFilename")

    result_df = df.copy()


    zip_bytes = base64.b64decode(base64_zip_str)
    
    metadata_lookup = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        for info in zf.infolist():
            if not info.is_dir():
                filename = Path(info.filename).name
                data = zf.read(info)
                metadata_lookup[filename] = {
                    "Base64": base64.b64encode(data).decode("utf-8"),
                    "SHA256Hash": hashlib.sha256(data).hexdigest(),
                }

    metadata_df = result_df["RelaticsIconFilename"].map(metadata_lookup).apply(pd.Series)
    
    result_df[["Base64", "SHA256Hash"]] = metadata_df[["Base64", "SHA256Hash"]]
    
    return result_df

# if __name__ == "__main__":
#     xml = RelaticsClient(client_id="REMOVED_SECRET", client_secret="REMOVED_SECRET", environment="cwd").get_request(workspace_id="210b2918-b359-4892-a23b-bf96ad23d82f", operation="icons")
#     df, zipped = parse_icon_xml(root=xml)
#     result_df = add_file_metadata_from_base64_zip(df=df, base64_zip_str=zipped)
#     result_df.to_csv("output.csv", index=False)