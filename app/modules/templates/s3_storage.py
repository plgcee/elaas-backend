import boto3
from botocore.exceptions import ClientError
from app.config import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class S3Storage:
    def __init__(self):
        if not all([settings.aws_access_key_id, settings.aws_secret_access_key, settings.s3_bucket_name]):
            raise ValueError("AWS S3 credentials and bucket name must be configured")
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region
        )
        self.bucket_name = settings.s3_bucket_name
    
    def upload_file(self, file_content: bytes, key: str, content_type: str = "application/zip") -> str:
        """Upload file to S3 and return the S3 URL"""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                ContentType=content_type
            )
            return f"s3://{self.bucket_name}/{key}"
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {str(e)}")
            raise
    
    def delete_file(self, key: str) -> bool:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {str(e)}")
            return False
