"""GCS storage for template ZIP files."""
import logging
from typing import Optional

from app.config import settings
from app.core.gcp_credentials import get_gcp_credentials

logger = logging.getLogger(__name__)


class GCSStorage:
    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or settings.gcs_templates_bucket or settings.gcs_template_staging_bucket
        if not self.bucket_name or not settings.gcp_project_id:
            raise ValueError("GCS templates bucket and gcp_project_id must be configured")
        from google.cloud import storage
        kwargs = {"project": settings.gcp_project_id}
        creds = get_gcp_credentials()
        if creds:
            kwargs["credentials"] = creds
        self._client = storage.Client(**kwargs)
        self._bucket = self._client.bucket(self.bucket_name)

    def upload_file(self, file_content: bytes, key: str, content_type: str = "application/zip") -> str:
        """Upload file to GCS and return gs:// URI."""
        blob = self._bucket.blob(key)
        blob.upload_from_string(file_content, content_type=content_type)
        return f"gs://{self.bucket_name}/{key}"

    def delete_file(self, key: str) -> bool:
        """Delete file from GCS."""
        try:
            self._bucket.blob(key).delete()
            return True
        except Exception as e:
            logger.warning("Failed to delete from GCS (%s): %s", key, e)
            return False
