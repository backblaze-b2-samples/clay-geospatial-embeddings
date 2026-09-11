"""Generic B2 object helpers for app-authored artifacts.

Job records (JSON) and embedding tensors (.npy) are written and enumerated
through here. Same ``repo`` layer as ``b2_client``, so boto3/botocore usage is
allowed. Every write invalidates the shared listing cache so the full-bucket
explorer and dashboard reflect new artifacts immediately.
"""

import io

from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client
from app.repo.list_cache import invalidate as _invalidate_list_cache

_NOT_FOUND = ("404", "NoSuchKey", "NotFound")


def put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    """Write raw bytes to B2 at ``key``. Raises RuntimeError on S3 failure."""
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=io.BytesIO(data),
            ContentType=content_type,
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 put_object failed for '{key}': {e}") from e
    _invalidate_list_cache()


def list_keys(prefix: str) -> list[str]:
    """Every object key under ``prefix`` (paginated). Raises RuntimeError on failure."""
    client = get_s3_client()
    keys: list[str] = []
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": prefix, "MaxKeys": 1000}
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            keys.extend(obj["Key"] for obj in response.get("Contents", []))
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 list failed for prefix '{prefix}': {e}") from e
    return keys


def object_exists(key: str) -> bool:
    """True if ``key`` exists. Raises RuntimeError on non-404 S3 failure."""
    client = get_s3_client()
    try:
        client.head_object(Bucket=settings.b2_bucket_name, Key=key)
        return True
    except ClientError as e:
        if e.response.get("Error", {}).get("Code", "") in _NOT_FOUND:
            return False
        raise RuntimeError(f"B2 head_object failed for '{key}': {e}") from e


def delete_key(key: str) -> None:
    """Delete one object. Raises RuntimeError on S3 failure."""
    client = get_s3_client()
    try:
        client.delete_object(Bucket=settings.b2_bucket_name, Key=key)
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 delete failed for '{key}': {e}") from e
    _invalidate_list_cache()


def delete_prefix(prefix: str) -> int:
    """Delete every object under ``prefix``; return how many were removed.

    Used for the scoped per-job delete (``embeddings/<id>/``). Batches into the
    S3 multi-object delete (max 1000 keys/request). Raises RuntimeError on failure.
    """
    keys = list_keys(prefix)
    if not keys:
        return 0
    client = get_s3_client()
    try:
        for start in range(0, len(keys), 1000):
            batch = keys[start : start + 1000]
            client.delete_objects(
                Bucket=settings.b2_bucket_name,
                Delete={"Objects": [{"Key": k} for k in batch], "Quiet": True},
            )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 bulk delete failed for prefix '{prefix}': {e}") from e
    _invalidate_list_cache()
    return len(keys)
