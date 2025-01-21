import os
import logging
import urllib.request
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from base64 import b64encode
from urllib.parse import urljoin
from xml.etree import ElementTree as ET
from src import (
    bucket_name,
    endpoint_url,
    access_key_id,
    secret_access_key,
)

# Hàm ký yêu cầu AWS S3
def sign_request(method, url, headers):
    canonical_headers = ''.join([f"{k.lower()}:{v}\n" for k, v in sorted(headers.items())])
    signed_headers = ';'.join([k.lower() for k in sorted(headers.keys())])
    payload_hash = hashlib.sha256(b"").hexdigest()

    canonical_request = f"{method}\n{url}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    string_to_sign = (
        f"AWS4-HMAC-SHA256\n{headers['x-amz-date']}\n"
        f"{headers['x-amz-date'][:8]}/us-east-1/s3/aws4_request\n"
        f"{hashlib.sha256(canonical_request.encode()).hexdigest()}"
    )
    date_key = hmac.new(('AWS4' + secret_access_key).encode(), headers['x-amz-date'][:8].encode(), hashlib.sha256).digest()
    region_key = hmac.new(date_key, b'us-east-1', hashlib.sha256).digest()
    service_key = hmac.new(region_key, b's3', hashlib.sha256).digest()
    signing_key = hmac.new(service_key, b'aws4_request', hashlib.sha256).digest()
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    headers['Authorization'] = (
        f"AWS4-HMAC-SHA256 Credential={access_key_id}/{headers['x-amz-date'][:8]}"
        f"/us-east-1/s3/aws4_request, SignedHeaders={signed_headers}, Signature={signature}"
    )

# Hàm liệt kê các file trong thư mục bucket
def list_objects(prefix):
    url = f"{endpoint_url}/{bucket_name}?prefix={prefix}"
    logging.debug(f"GET URL for list_objects: {url}")

    headers = {
        "Host": endpoint_url.split("//")[1],
        "x-amz-date": datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
    }
    sign_request("GET", f"/{bucket_name}?prefix={prefix}", headers)

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            return response.read().decode()
    except Exception as e:
        logging.error(f"Error in list_objects: {e}")
        raise

# Hàm xóa tệp trong bucket
def delete_object(key):
    url = f"{endpoint_url}/{bucket_name}/{key}"
    logging.debug(f"DELETE URL: {url}")

    headers = {
        "Host": endpoint_url.split("//")[1],
        "x-amz-date": datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
    }
    sign_request("DELETE", f"/{bucket_name}/{key}", headers)

    request = urllib.request.Request(url, headers=headers, method="DELETE")
    try:
        with urllib.request.urlopen(request) as response:
            return response.status
    except urllib.error.HTTPError as e:
        logging.error(f"HTTPError: {e.reason}, Code: {e.code}, URL: {url}")
        raise

# Hàm xóa các tệp cũ trong thư mục bucket
def delete_old_files(prefix, threshold_minutes=60):
    """
    Xóa các tệp cũ trong một thư mục bucket dựa trên prefix.
    """
    try:
        logging.debug(f"Prefix used for list_objects: {prefix}")
        objects = list_objects(prefix)
        logging.debug(f"Objects returned: {objects}")

        root = ET.fromstring(objects)
        for obj in root.findall('.//Contents'):
            key = obj.find('Key').text
            last_modified = datetime.strptime(obj.find('LastModified').text, "%Y-%m-%dT%H:%M:%S.%fZ")
            age = datetime.now(timezone.utc) - last_modified

            if age > timedelta(minutes=threshold_minutes):
                logging.debug(f"Deleting file: {key}, Age: {age}")
                delete_object(key)
                logging.info(f"Deleted old file: {key}")
    except Exception as e:
        logging.error(f"Error deleting old files: {e}")

# Hàm tải tệp lên bucket
def upload_file(file_path, key):
    """
    Tải tệp lên bucket S3.
    """
    url = f"{endpoint_url}/{bucket_name}/{key}"
    logging.debug(f"PUT URL for upload_file: {url}")

    headers = {
        "Host": endpoint_url.split("//")[1],
        "x-amz-date": datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
        "Content-Type": "application/octet-stream",
    }
    sign_request("PUT", f"/{bucket_name}/{key}", headers)

    with open(file_path, 'rb') as file_data:
        request = urllib.request.Request(url, data=file_data.read(), headers=headers, method="PUT")
        try:
            with urllib.request.urlopen(request) as response:
                return response.status
        except urllib.error.HTTPError as e:
            logging.error(f"HTTPError: {e.reason}, Code: {e.code}, URL: {url}")
            raise

# Hàm chính để tải file và xóa tệp cũ
def upload(file_path, key, threshold_minutes=60):
    """
    Tải file lên bucket và xóa các file cũ hơn threshold_minutes.
    """
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return

    try:
        # Xóa các file cũ trong cùng thư mục
        delete_old_files(key.rsplit('/', 1)[0] + '/', threshold_minutes)

        # Tải lên file
        status = upload_file(file_path, key)
        if status == 200:
            logging.info(f"Upload success: {key}")
    except Exception as e:
        logging.error(f"Failed to upload file: {e}")
