import os
import logging
import urllib.request
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from base64 import b64encode
from email.utils import formatdate
from urllib.parse import urljoin

from src import (
    bucket_name, 
    endpoint_url, 
    access_key_id, 
    secret_access_key
)

# Hàm ký yêu cầu AWS S3
def sign_request(method, url, headers):
    canonical_headers = ''.join([f"{k.lower()}:{v}\n" for k, v in sorted(headers.items())])
    signed_headers = ';'.join([k.lower() for k in sorted(headers.keys())])
    payload_hash = hashlib.sha256(b"").hexdigest()

    canonical_request = f"{method}\n{url}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    string_to_sign = f"AWS4-HMAC-SHA256\n{headers['x-amz-date']}\n{headers['x-amz-date'][:8]}/us-east-1/s3/aws4_request\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"
    date_key = hmac.new(('AWS4' + secret_access_key).encode(), headers['x-amz-date'][:8].encode(), hashlib.sha256).digest()
    region_key = hmac.new(date_key, b'us-east-1', hashlib.sha256).digest()
    service_key = hmac.new(region_key, b's3', hashlib.sha256).digest()
    signing_key = hmac.new(service_key, b'aws4_request', hashlib.sha256).digest()

    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
    headers['Authorization'] = f"AWS4-HMAC-SHA256 Credential={access_key_id}/{headers['x-amz-date'][:8]}/us-east-1/s3/aws4_request, SignedHeaders={signed_headers}, Signature={signature}"

# Liệt kê các tệp
def list_objects(prefix):
    url = urljoin(endpoint_url, f"{bucket_name}?prefix={prefix}")
    headers = {
        "Host": url.split("//")[1],
        "x-amz-date": datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    }
    sign_request("GET", url, headers)
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request) as response:
        return response.read().decode()

# Xóa tệp
def delete_object(key):
    url = urljoin(endpoint_url, f"{bucket_name}/{key}")
    headers = {
        "Host": url.split("//")[1],
        "x-amz-date": datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    }
    sign_request("DELETE", url, headers)
    request = urllib.request.Request(url, headers=headers, method="DELETE")
    with urllib.request.urlopen(request) as response:
        return response.status

# Tải lên tệp
def upload_file(file_path, key):
    url = urljoin(endpoint_url, f"{bucket_name}/{key}")
    headers = {
        "Host": url.split("//")[1],
        "x-amz-date": datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
        "Content-Type": "application/octet-stream"
    }
    sign_request("PUT", url, headers)
    with open(file_path, 'rb') as file_data:
        request = urllib.request.Request(url, data=file_data, headers=headers, method="PUT")
        with urllib.request.urlopen(request) as response:
            return response.status

# Hàm xóa các tệp cũ
def delete_old_files(prefix, threshold_minutes=60):
    try:
        objects = list_objects(prefix)
        # Parse XML response
        from xml.etree import ElementTree as ET
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

# Hàm chính để tải tệp
def upload(file_path, key, threshold_minutes=60):
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return
    try:
        # Xóa các tệp cũ trong cùng thư mục
        delete_old_files(key.rsplit('/', 1)[0], threshold_minutes)
        # Tải lên tệp
        status = upload_file(file_path, key)
        if status == 200:
            logging.info(f"Upload success: {key}")
    except Exception as e:
        logging.error(f"Failed to upload file: {e}")
