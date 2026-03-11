# hr/utils/file_validators.py
from django.core.exceptions import ValidationError

MAX_PHOTO_SIZE = 300 * 1024        # 300 KB
MAX_PDF_SIZE = 2 * 1024 * 1024     # 2 MB
MAX_PHOTO_SIZE_CERTIFICATE = 500 * 1024        # 500 KB

def validate_photo_size(file):
    if file and file.size > MAX_PHOTO_SIZE:
        raise ValidationError("Photo size must be at most 300 KB.")

def validate_photo_size_certificate(file):
    if file and file.size > MAX_PHOTO_SIZE:
        raise ValidationError("Photo size must be at most 300 KB.")

def validate_pdf_size(file):
    if file and file.size > MAX_PDF_SIZE:
        raise ValidationError("PDF size must be at most 2 MB.")