"""
Watches an IPTK HTTP API endpoint for new datasets and extracts DICOM metadata
if the dataset contains *.dcm files. If multiple dcm files are present in the
dataset, only one will be indexed.
"""

from datetime import datetime
from json.decoder import JSONDecodeError
import requests
import pydicom
import redis
import time
import os
import io

api_endpoint = os.environ.get("API_ENDPOINT", "http://localhost").rstrip('/')
spec_id = "32bdac29d951d9def51e3cee10c4f0e582f2a962"
redis_host = os.environ.get("REDIS_HOST", None)
r = None
if redis_host:
    r = redis.StrictRedis(redis_host, decode_responses=True)

def handle_dataset(dataset_id):
    dataset_url = f"{api_endpoint}/v3/datasets/{dataset_id}"
    meta_response = requests.get(f"{dataset_url}/meta")
    try:
        meta_info = meta_response.json()
    except JSONDecodeError:
        print(f"{dataset_id}: Failed (Could not decode)")
        print(meta_response.status_code)
    if spec_id in meta_info["metadatasets"]:
        print(f"{dataset_id}: Skipped (existing)")
        return
    file_list = requests.get(f"{dataset_url}/data").json()
    dicom_files = [x for x in file_list["files"] if x.endswith(".dcm")]
    if not dicom_files:
        print(f"{dataset_id}: Skipped (no DICOM files)")
        return
    dicom_file = dicom_files[0]
    dicom_data = requests.get(f"{dataset_url}/data/{dicom_file}").content
    ds = pydicom.read_file(io.BytesIO(dicom_data))
    ds.remove_private_tags()
    tags = ds.keys()
    info = {}
    for element in ds.values():
        if not element.keyword:
            # Ignore private and unknown elements
            continue
        if element.VM > 1:
            # Ignore elements with multiple values
            continue
        if element.VR == "DA":
            # For date elements, try to join them with the corresponding time
            # element to create an additional DateTime element.
            first_part = element.keyword[:-4]
            time_keyword = first_part + "Time"
            time_value = ds.get(time_keyword, "000000.0")
            if '.' not in time_value:
                time_value = time_value + '.0'
            date_value = element.value
            full_value = f"{date_value} {time_value}"
            try:
                date_time = datetime.strptime(full_value, '%Y%m%d %H%M%S.%f')
                info[first_part + "DateTime"] = date_time.isoformat()
            except ValueError:
                # If date or time were not properly formatted, ignore.
                pass
        if element.VR == "PN":
            info[element.keyword] = str(element.value)
        if element.VR in ["US", "DS", "UI", "CS", "IS", "LO", "SH", "TM", "DA"]:
            info[element.keyword] = element.value
    dicom_meta_url = f"{dataset_url}/meta/{spec_id}"
    r = requests.post(dicom_meta_url, json=info)
    print(f"{dataset_id}: Updated")


seen_ids = set()
def dataset_seen(dataset_id):
    if r:
        answer = r.sismember("datasets_indexed_dicom", dataset_id)
        r.sadd("datasets_indexed_dicom", dataset_id)
    else:
        answer = dataset_id in seen_ids
        seen_ids.add(dataset_id)
    return answer
    
current_idx = 0
while True:
    params = {"start": current_idx, "per_page": 10}
    logs = requests.get(f"{api_endpoint}/v3/logs/dataset_changes", params=params).json()
    for entry in logs["entries"]:
        dataset_id = entry["dataset_id"]
        if not dataset_seen(dataset_id):
            handle_dataset(dataset_id)
        else:
            print(f"{dataset_id}: Skipped (seen)")
    current_idx = logs["range"]["end"]
    if logs["range"]["end"] == logs["range"]["max"]:
        time.sleep(10)
