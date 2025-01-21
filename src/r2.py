import os
import logging
import urllib.request
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree as ET

from src import (
    bucket_name,
    endpoint_url,
    access_key_id,
    secret_access_key,
)

logging.basicConfig(level=logging.DEBUG)

def sign_request(method, url, headers, payload_hash=""):
    canonical_uri = url.split(endpoint_url.rstrip('/'))[-1]
    canonical_headers = ''.join(f"{k.lower()}:{v.strip()}\n" for k, v in sorted(headers.items()))
    signed_headers = ';'.join(k.lower() for k in sorted(headers.keys()))
    payload_hash = payload_hash or hashlib.sha256(b"").hexdigest()

    canonical_request = (
        f"{method}\n{canonical_uri}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    )
    logging.debug(f"CanonicalRequest:\n{canonical_request}")

    date = headers['x-amz-date'][:8]
    string_to_sign = (
        f"AWS4-HMAC-SHA256\n{headers['x-amz-date']}\n"
        f"{date}/us-east-1/s3/aws4_request\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"
    )
    logging.debug(f"StringToSign:\n{string_to_sign}")

    date_key = hmac.new(('AWS4' + secret_access_key).encode(), date.encode(), hashlib.sha256).digest()
    region_key = hmac.new(date_key, b'us-east-1', hashlib.sha256).digest()
    service_key = hmac.new(region_key, b's3', hashlib.sha256).digest()
    signing_key = hmac.new(service_key, b'aws4_request', hashlib.sha256).digest()
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    headers['Authorization'] = (
        f"AWS4-HMAC-SHA256 Credential={access_key_id}/{date}/us-east-1/s3/aws4_request, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    logging.debug(f"Signature:\n{signature}")

def build_url(bucket, key=None):
    base_url = endpoint_url.rstrip('/')
    if key:
        return f"{base_url}/{bucket}/{key.lstrip('/')}"
    return f"{base_url}/{bucket}"

def list_objects(prefix):
    url = build_url(bucket_name, f"?prefix={prefix}")
    headers = {
        "Host": endpoint_url.split("//")[1],
        "x-amz-date": datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
    }
    sign_request("GET", url, headers)
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request) as response:
        return response.read().decode()

def delete_object(key):
    url = build_url(bucket_name, key)
    headers = {
        "Host": endpoint_url.split("//")[1],
        "x-amz-date": datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
    }
    sign_request("DELETE", url, headers)
    request = urllib.request.Request(url, headers=headers, method="DELETE")
    with urllib.request.urlopen(request) as response:
        return response.status

def upload_file(file_path, key):
    url = build_url(bucket_name, key)
    with open(file_path, 'rb') as file:
        file_data = file.read()
    payload_hash = hashlib.sha256(file_data).hexdigest()
    headers = {
        "Host": endpoint_url.split("//")[1],
        "x-amz-date": datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
        "x-amz-content-sha256": payload_hash,
        "Content-Type": "application/octet-stream",
        "Content-Length": str(len(file_data)),  # Fix lỗi 411
    }
    sign_request("PUT", url, headers, payload_hash)
    with open(file_path, 'rb') as file:
        request = urllib.request.Request(url, data=file, headers=headers, method="PUT")
        with urllib.request.urlopen(request) as response:
            return response.status

def delete_old_files(prefix, threshold_minutes=60):
    try:
        objects = list_objects(prefix)
        root = ET.fromstring(objects)
        for obj in root.findall('.//Contents'):
            key = obj.find('Key').text
            last_modified = datetime.strptime(obj.find('LastModified').text, "%Y-%m-%dT%H:%M:%S.%fZ")
            age = datetime.now(timezone.utc) - last_modified
            if age > timedelta(minutes=threshold_minutes):
                delete_object(key)
                logging.info(f"Deleted old file: {key}")
    except Exception as e:
        logging.error(f"Error deleting old files: {e}")

def upload(file_path, key, threshold_minutes=60):
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return
    try:
        delete_old_files(key.rsplit('/', 1)[0], threshold_minutes)
        status = upload_file(file_path, key)
        if status == 200:
            logging.info(f"Upload success: {key}")
    except Exception as e:
        logging.error(f"Failed to upload file: {e}")
