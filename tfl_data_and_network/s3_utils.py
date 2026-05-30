"""S3 utility functions for interacting with AWS S3."""

import boto3
import logging
from io import BytesIO
from typing import Union

logger = logging.getLogger(__name__)


def fetch_file_from_s3(
    bucket_name: str, file_key: str, as_bytes: bool = False
) -> Union[str, bytes, None]:
    """Fetch a file from S3 and return as string or bytes.

    Args:
        bucket_name: Name of the S3 bucket
        file_key: Key/path of the file in S3
        as_bytes: If True, return bytes; if False, return string

    Returns:
        File contents as string or bytes, or None if file not found

    Raises:
        Exception: If S3 access fails
    """
    try:
        s3_client = boto3.client("s3")
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        content = response["Body"].read()

        if as_bytes:
            return content
        else:
            return content.decode("utf-8")

    except s3_client.exceptions.NoSuchKey:
        logger.warning(f"File not found in S3: s3://{bucket_name}/{file_key}")
        return None
    except Exception as e:
        logger.error(f"Error fetching file from S3: {e}")
        raise


def upload_file_to_s3(
    bucket_name: str, file_key: str, content: Union[str, bytes]
) -> bool:
    """Upload file content to S3.

    Args:
        bucket_name: Name of the S3 bucket
        file_key: Key/path for the file in S3
        content: Content to upload (string or bytes)

    Returns:
        True if successful, False otherwise
    """
    try:
        s3_client = boto3.client("s3")

        if isinstance(content, str):
            content = content.encode("utf-8")

        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=content)
        logger.info(f"Successfully uploaded to s3://{bucket_name}/{file_key}")
        return True

    except Exception as e:
        logger.error(f"Error uploading file to S3: {e}")
        return False


def file_exists_in_s3(bucket_name: str, file_key: str) -> bool:
    """Check if a file exists in S3.

    Args:
        bucket_name: Name of the S3 bucket
        file_key: Key/path of the file in S3

    Returns:
        True if file exists, False otherwise
    """
    try:
        s3_client = boto3.client("s3")
        s3_client.head_object(Bucket=bucket_name, Key=file_key)
        return True
    except s3_client.exceptions.NoSuchKey:
        return False
    except Exception as e:
        logger.error(f"Error checking file existence in S3: {e}")
        return False
