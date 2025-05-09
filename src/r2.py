import os
import logging
import requests
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from urllib.parse import quote, urlparse
from xml.etree import ElementTree
from src import bucket_name, endpoint_url, access_key_id, secret_access_key

def get_signature_key(key, date_stamp, region, service):
    k_date = hmac.new(('AWS4' + key).encode(), date_stamp.encode(), hashlib.sha256).digest()
    k_region = hmac.new(k_date, region.encode(), hashlib.sha256).digest()
    k_service = hmac.new(k_region, service.encode(), hashlib.sha256).digest()
    k_signing = hmac.new(k_service, b'aws4_request', hashlib.sha256).digest()
    return k_signing

def sign_request(method, path, headers, secret_key, query_params=''):
    region = 'auto'
    service = 's3'
    host = urlparse(endpoint_url).netloc
    amz_date = headers['x-amz-date']
    date_stamp = amz_date[:8]

    canonical_uri = '/' + quote(path, safe='/~')
    canonical_querystring = query_params
    canonical_headers = ''.join(f"{k.lower()}:{v.strip()}\n" for k, v in sorted(headers.items()))
    signed_headers = ';'.join(k.lower() for k in sorted(headers))
    payload_hash = headers['x-amz-content-sha256']

    canonical_request = f"{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = f"AWS4-HMAC-SHA256\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"

    signing_key = get_signature_key(secret_key, date_stamp, region, service)
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    return f"AWS4-HMAC-SHA256 Credential={access_key_id}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"

def list_objects(bucket, prefix):
    query = f"prefix={quote(prefix)}"
    url = f"{endpoint_url}/{bucket}?{query}"
    amz_date = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')

    headers = {
        'Host': urlparse(endpoint_url).netloc,
        'x-amz-date': amz_date,
        'x-amz-content-sha256': hashlib.sha256(b'').hexdigest(),
    }
    headers['Authorization'] = sign_request('GET', bucket, headers, secret_access_key, query)

    r = requests.get(url, headers=headers)
    r.raise_for_status()

    root = ElementTree.fromstring(r.content)
    objs = []
    for content in root.findall('.//{http://s3.amazonaws.com/doc/2006-03-01/}Contents'):
        key = content.find('{http://s3.amazonaws.com/doc/2006-03-01/}Key').text
        lastmod = content.find('{http://s3.amazonaws.com/doc/2006-03-01/}LastModified').text
        lastmod_dt = datetime.strptime(lastmod, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
        objs.append({'Key': key, 'LastModified': lastmod_dt})
    return objs

def delete_object(bucket, key):
    path = f"{bucket}/{key}"
    url = f"{endpoint_url}/{path}"
    amz_date = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    headers = {
        'Host': urlparse(endpoint_url).netloc,
        'x-amz-date': amz_date,
        'x-amz-content-sha256': hashlib.sha256(b'').hexdigest(),
    }
    headers['Authorization'] = sign_request('DELETE', path, headers, secret_access_key)

    r = requests.delete(url, headers=headers)
    if not r.ok:
        logging.error(f"Delete failed: {r.text}")
        r.raise_for_status()
    logging.info(f"Deleted: {key}")

def delete_old_files(bucket, prefix, threshold_minutes=60):
    for obj in list_objects(bucket, prefix):
        age = datetime.now(timezone.utc) - obj['LastModified']
        if age > timedelta(minutes=threshold_minutes):
            delete_object(bucket, obj['Key'])

def upload(file_path, key):
    path = f"{bucket_name}/{key}"
    url = f"{endpoint_url}/{path}"
    amz_date = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')

    with open(file_path, 'rb') as f:
        body = f.read()
    payload_hash = hashlib.sha256(body).hexdigest()

    headers = {
        'Host': urlparse(endpoint_url).netloc,
        'x-amz-date': amz_date,
        'x-amz-content-sha256': payload_hash,
        'Content-Type': 'application/octet-stream',
    }
    headers['Authorization'] = sign_request('PUT', path, headers, secret_access_key)

    delete_old_files(bucket_name, key.rsplit('/', 1)[0])

    r = requests.put(url, headers=headers, data=body)
    if not r.ok:
        logging.error(f"Upload failed: {r.text}")
        r.raise_for_status()
    logging.info(f"Uploaded: {key}")
