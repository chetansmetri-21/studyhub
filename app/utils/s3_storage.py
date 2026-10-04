"""
StudyHub - Production AWS S3 Storage Service

Responsibilities:
- Upload files securely to private S3
- Check whether objects exist
- Generate temporary presigned URLs
- Download/view files without making the bucket public
- Delete objects
- Get object metadata
- Handle AWS errors cleanly
"""

import os
from typing import Optional

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


AWS_REGION = (
    os.getenv("AWS_REGION")
    or os.getenv("AWS_DEFAULT_REGION")
    or "ap-south-1"
)

S3_BUCKET = (
    os.getenv("S3_BUCKET")
    or os.getenv("AWS_S3_BUCKET")
)


# ============================================================
# VALIDATION
# ============================================================

if not S3_BUCKET:
    raise RuntimeError(
        "S3 bucket is missing. Add AWS_S3_BUCKET to your .env file."
    )


# ============================================================
# S3 CLIENT
# ============================================================

_s3_client = None


def get_s3_client():
    """
    Create and reuse a single S3 client.

    boto3 automatically reads:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_SESSION_TOKEN (if present)

    from the environment / AWS credential chain.
    """

    global _s3_client

    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            region_name=AWS_REGION
        )

    return _s3_client


# ============================================================
# KEY SANITIZATION
# ============================================================

def normalize_key(object_key: str) -> str:
    """
    Normalize an S3 object key.

    Prevents accidental:
        //file
        leading spaces
        empty keys
    """

    if not object_key:
        raise ValueError("S3 object key cannot be empty.")

    object_key = str(object_key).strip()
    object_key = object_key.lstrip("/")

    if not object_key:
        raise ValueError("Invalid S3 object key.")

    return object_key


# ============================================================
# UPLOAD
# ============================================================

def upload_file(
    file_obj,
    object_key: str,
    content_type: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    """
    Upload a file-like object to private S3.
    """

    object_key = normalize_key(object_key)

    extra_args = {}

    if content_type:
        extra_args["ContentType"] = content_type

    if metadata:
        extra_args["Metadata"] = {
            str(key): str(value)
            for key, value in metadata.items()
        }

    try:
        stream = getattr(
            file_obj,
            "stream",
            file_obj
        )

        stream.seek(0)

        get_s3_client().upload_fileobj(
            Fileobj=stream,
            Bucket=S3_BUCKET,
            Key=object_key,
            ExtraArgs=extra_args
        )

        return object_key

    except (ClientError, BotoCoreError) as exc:
        raise RuntimeError(
            f"S3 upload failed: {exc}"
        ) from exc


# ============================================================
# OBJECT EXISTS
# ============================================================

def object_exists(object_key: str) -> bool:
    """
    Check whether an S3 object exists.
    """

    object_key = normalize_key(object_key)

    try:
        get_s3_client().head_object(
            Bucket=S3_BUCKET,
            Key=object_key
        )

        return True

    except ClientError as exc:

        error_code = exc.response.get(
            "Error",
            {}
        ).get(
            "Code"
        )

        if error_code in (
            "404",
            "NoSuchKey",
            "NotFound"
        ):
            return False

        raise RuntimeError(
            f"Unable to check S3 object: {exc}"
        ) from exc


# ============================================================
# OBJECT METADATA
# ============================================================

def get_object_metadata(object_key: str):
    """
    Return S3 metadata for an object.

    Returns None if object doesn't exist.
    """

    object_key = normalize_key(object_key)

    try:
        return get_s3_client().head_object(
            Bucket=S3_BUCKET,
            Key=object_key
        )

    except ClientError as exc:

        error_code = exc.response.get(
            "Error",
            {}
        ).get(
            "Code"
        )

        if error_code in (
            "404",
            "NoSuchKey",
            "NotFound"
        ):
            return None

        raise RuntimeError(
            f"Unable to retrieve S3 metadata: {exc}"
        ) from exc


# ============================================================
# PRESIGNED URL
# ============================================================

def generate_presigned_url(
    object_key: str,
    *,
    download: bool = False,
    download_name: Optional[str] = None,
    expires: int = 300,
):
    """
    Generate a temporary private S3 URL.

    download=False:
        Browser attempts to display the resource.

    download=True:
        Browser downloads the resource.

    Maximum expiry:
        1 hour
    """

    object_key = normalize_key(object_key)

    if expires < 1 or expires > 3600:
        raise ValueError(
            "Presigned URL expiry must be between 1 and 3600 seconds."
        )

    if not object_exists(object_key):
        return None

    params = {
        "Bucket": S3_BUCKET,
        "Key": object_key,
    }

    if download:
        safe_name = (
            download_name
            or os.path.basename(object_key)
        )

        safe_name = (
            str(safe_name)
            .replace("\r", "")
            .replace("\n", "")
            .replace('"', "")
        )

        params["ResponseContentDisposition"] = (
            f'attachment; filename="{safe_name}"'
        )

    try:
        return get_s3_client().generate_presigned_url(
            ClientMethod="get_object",
            Params=params,
            ExpiresIn=expires
        )

    except (ClientError, BotoCoreError) as exc:
        raise RuntimeError(
            f"Unable to generate S3 URL: {exc}"
        ) from exc


# ============================================================
# DELETE
# ============================================================

def delete_object(object_key: str) -> bool:
    """
    Delete an object from S3.

    Returns True when deletion request succeeds.
    """

    object_key = normalize_key(object_key)

    try:
        get_s3_client().delete_object(
            Bucket=S3_BUCKET,
            Key=object_key
        )

        return True

    except (ClientError, BotoCoreError) as exc:
        raise RuntimeError(
            f"S3 deletion failed: {exc}"
        ) from exc


# ============================================================
# COPY OBJECT
# ============================================================

def copy_object(
    source_key: str,
    destination_key: str
):
    """
    Copy an S3 object inside the same bucket.
    """

    source_key = normalize_key(source_key)
    destination_key = normalize_key(destination_key)

    try:
        get_s3_client().copy_object(
            Bucket=S3_BUCKET,
            CopySource={
                "Bucket": S3_BUCKET,
                "Key": source_key
            },
            Key=destination_key
        )

        return destination_key

    except (ClientError, BotoCoreError) as exc:
        raise RuntimeError(
            f"S3 copy failed: {exc}"
        ) from exc


# ============================================================
# GET OBJECT SIZE
# ============================================================

def get_object_size(object_key: str):
    """
    Return object size in bytes.

    Returns None if object doesn't exist.
    """

    metadata = get_object_metadata(object_key)

    if metadata is None:
        return None

    return metadata.get("ContentLength")


# ============================================================
# GET CONTENT TYPE
# ============================================================

def get_object_content_type(object_key: str):
    """
    Return the MIME type stored in S3.
    """

    metadata = get_object_metadata(object_key)

    if metadata is None:
        return None

    return metadata.get("ContentType")


# ============================================================
# TEST CONNECTION
# ============================================================

def test_s3_connection():
    """
    Verify that StudyHub can access the configured bucket.
    """

    try:
        get_s3_client().head_bucket(
            Bucket=S3_BUCKET
        )

        return {
            "success": True,
            "bucket": S3_BUCKET,
            "region": AWS_REGION
        }

    except (ClientError, BotoCoreError) as exc:
        return {
            "success": False,
            "bucket": S3_BUCKET,
            "region": AWS_REGION,
            "error": str(exc)
        }