import requests
import json
import base64
import zipfile
import os
import io
import hashlib

with open("response.json") as f:
    response = json.load(f)

binary_data = base64.b64decode(response["Documents"][0])
zipped = io.BytesIO(binary_data)
extract_dir = "extracted_files"
os.makedirs(extract_dir, exist_ok=True) 

with zipfile.ZipFile(zipped, "r") as zip_ref:
    zip_ref.extractall(extract_dir)

# print(response["Data"]["Element"][10]) # full element
# print(response["Data"]["Element"][10]["@RelaticsIconFilename"]) # filename
# print(response["Data"]["Element"][10]["@Element"]) # element name
# print(response["Data"]["Element"][10]["@RelaticsIconFilename"].split(".")[-1]) # extention
for i in range(len(response["Data"]["Element"])):
    try:
        os.rename("extracted_files/" + response["Data"]["Element"][i]["@RelaticsIconFilename"], "extracted_files/" + response["Data"]["Element"][i]["@Element"].replace(" ", "_") + "." + response["Data"]["Element"][i]["@RelaticsIconFilename"].split(".")[-1])
    except Exception as e:
        print(f"error processing: {e}")
        # count += 1
for i in os.listdir("extracted_files"):
    with open("extracted_files/" + i, "rb") as f:
        data = f.read()
    hashlib.sha256(data).hexdigest()
