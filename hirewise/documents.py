import hashlib
import io
import os
import subprocess
import uuid
import zipfile
from pathlib import Path

import boto3
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


def validate_upload(upload):
    ext = Path(upload.name).suffix.lower()
    mimes = {'.pdf': {'application/pdf'}, '.docx': {'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}, '.txt': {'text/plain'}}
    if ext not in mimes or upload.content_type not in mimes[ext]:
        raise ValidationError('Use a PDF, DOCX or plain-text file with its correct file type.')
    if upload.size == 0 or upload.size > settings.UPLOAD_MAX_BYTES:
        raise ValidationError('File must be non-empty and no larger than 5 MB.')
    data = upload.read(settings.UPLOAD_MAX_BYTES + 1)
    upload.seek(0)
    if len(data) > settings.UPLOAD_MAX_BYTES:
        raise ValidationError('File is too large.')
    if ext == '.pdf' and not data.startswith(b'%PDF-'):
        raise ValidationError('The file signature does not match a PDF.')
    if ext == '.docx':
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entries = archive.infolist()
                names = archive.namelist()
                if len(entries) > 2000 or sum(x.file_size for x in entries) > 25 * 1024 * 1024:
                    raise ValidationError('The document expands beyond the safe processing limit.')
                if '[Content_Types].xml' not in names or 'word/document.xml' not in names:
                    raise ValidationError('This is not a DOCX document.')
                if any('vbaProject' in x or x.endswith('.exe') for x in names):
                    raise ValidationError('Active document content is not allowed.')
        except zipfile.BadZipFile as exc:
            raise ValidationError('The DOCX archive is invalid.') from exc
    if ext == '.txt':
        try:
            data.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise ValidationError('Text files must use UTF-8 encoding.') from exc
        if b'\x00' in data:
            raise ValidationError('Binary content cannot be uploaded as text.')
    return ext, data


def s3():
    return boto3.client('s3', endpoint_url=os.environ.get('S3_ENDPOINT_URL') or None,
                        region_name=os.environ.get('AWS_DEFAULT_REGION', 'eu-west-1'))


def store_document(upload):
    ext, data = validate_upload(upload)
    key = f'quarantine/{uuid.uuid4().hex}{ext}'
    bucket = os.environ.get('PRIVATE_BUCKET')
    if bucket:
        options = {'Bucket': bucket, 'Key': key, 'Body': data, 'ContentType': 'application/octet-stream'}
        encryption = os.environ.get('S3_SERVER_SIDE_ENCRYPTION', 'AES256')
        if encryption:
            options['ServerSideEncryption'] = encryption
        s3().put_object(**options)
    elif settings.ENVIRONMENT == 'development':
        key = default_storage.save(key, ContentFile(data))
    else:
        raise ValidationError('Private storage is not configured. Please try again later.')
    return {'storage_key': key, 'extension': ext, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def read_document(document):
    bucket = os.environ.get('PRIVATE_BUCKET')
    if bucket:
        response = s3().get_object(Bucket=bucket, Key=document.storage_key)
        return response['Body'].read(settings.UPLOAD_MAX_BYTES + 1)
    with default_storage.open(document.storage_key, 'rb') as stream:
        return stream.read(settings.UPLOAD_MAX_BYTES + 1)


def delete_document(document):
    bucket = os.environ.get('PRIVATE_BUCKET')
    if bucket:
        s3().delete_object(Bucket=bucket, Key=document.storage_key)
    else:
        default_storage.delete(document.storage_key)


def scan_bytes(data):
    # clamdscan INSTREAM scans stdin; no untrusted filenames become shell commands.
    executable = os.environ.get('CLAMDSCAN_PATH', 'clamdscan')
    result = subprocess.run([executable, '--no-summary', '-'], input=data, capture_output=True, timeout=45, check=False)
    if result.returncode == 0:
        return 'clean'
    if result.returncode == 1:
        return 'infected'
    raise RuntimeError('scanner_unavailable')
