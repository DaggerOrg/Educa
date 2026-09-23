"""S3-compatible object storage -- the default backend (requirement: store
the original PDF in S3-compatible storage, not in Postgres). Works
against MinIO locally (set S3_ENDPOINT_URL) and real AWS S3 in production
(leave it unset) -- it's the same client either way, just pointed at a
different endpoint.
"""

from __future__ import annotations

import os

import boto3
from botocore.exceptions import ClientError

from ..logging_config import get_logger

logger = get_logger(__name__)


class S3ObjectStorage:
    def __init__(
        self,
        bucket: str | None = None,
        endpoint_url: str | None = None,
        region_name: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
    ):
        self.bucket = bucket or os.environ.get("CURRICULUM_S3_BUCKET", "educa-curriculum-documents")
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url or os.environ.get("CURRICULUM_S3_ENDPOINT_URL") or None,
            region_name=region_name or os.environ.get("CURRICULUM_S3_REGION", "us-east-1"),
            aws_access_key_id=access_key or os.environ.get("CURRICULUM_S3_ACCESS_KEY") or None,
            aws_secret_access_key=secret_key or os.environ.get("CURRICULUM_S3_SECRET_KEY") or None,
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except ClientError:
            logger.info("Bucket %r not found, creating it", self.bucket)
            self._client.create_bucket(Bucket=self.bucket)

    def put(self, key: str, content: bytes, content_type: str) -> None:
        self._client.put_object(Bucket=self.bucket, Key=key, Body=content, ContentType=content_type)

    def get(self, key: str) -> bytes:
        return self._client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def delete(self, key: str) -> None:
        # S3's DeleteObject is idempotent (200 whether or not the key
        # existed) -- no existence check needed to satisfy "must not raise
        # if it's already gone".
        self._client.delete_object(Bucket=self.bucket, Key=key)
