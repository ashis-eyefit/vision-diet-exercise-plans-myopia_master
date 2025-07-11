import boto3
import os
from botocore.exceptions import NoCredentialsError, ClientError

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_IMG")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY_IMG")
S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME_IMG")
AWS_REGION = os.getenv("AWS_REGION_IMG", "us-east-1")

# Create S3 client
def get_s3_client():
    return boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

# Upload image file to S3
def upload_image_to_s3(file_path, s3_key):
    try:
        s3 = get_s3_client()
        with open(file_path, 'rb') as f:
            s3.upload_fileobj(f, S3_BUCKET_NAME, s3_key)
        return f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
    except (NoCredentialsError, ClientError, FileNotFoundError) as e:
        print("S3 upload error:", str(e))
        return None

# Generate S3 URL
def generate_s3_url(s3_key):
    return f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"

# Check if file exists in S3
def file_exists_in_s3(s3_key):
    s3 = get_s3_client()
    try:
        s3.head_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        return True
    except ClientError:
        return False
