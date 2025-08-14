import io
import logging
import os
import random

import boto3
from PIL import Image

# Get logger for this module
logger = logging.getLogger(__name__)

# Initialize S3 client
try:
    if os.getenv("BACKEND_ENVIRONMENT") == "local":
        # For local development, use explicit credentials
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_region = os.getenv("AWS_REGION", "us-east-1")

        if aws_access_key and aws_secret_key:
            s3 = boto3.client(
                "s3",
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region,
            )
        else:
            logger.warning(
                "AWS credentials not found. S3 functionality will be disabled for local development.",
            )
            s3 = None
    else:
        # For production, use default credential chain
        s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION", "us-east-1"))
except Exception as e:
    logger.warning(f"Failed to initialize S3 client: {e}")
    s3 = None


def download(prefix, file_path):
    if not s3:
        logger.warning("S3 not available - download operation skipped")
        return None

    try:
        # Step 1: Download image from S3
        s3_key = f"{prefix}/{file_path}"
        logger.debug(f"Attempting to download from S3: {s3_key}")
        s3_response = s3.get_object(
            Bucket=os.getenv("AWS_BUCKET_NAME"),
            Key=s3_key,
        )
        image_data = s3_response["Body"].read()
        logger.debug(f"Successfully downloaded {len(image_data)} bytes from S3")

        # Step 2: Load into PIL (or whatever your processing pipeline uses)
        return Image.open(io.BytesIO(image_data))

    except s3.exceptions.NoSuchKey:
        logger.error(f"Image not found in S3: {prefix}/{file_path}")
    except Exception as e:
        logger.error(f"Download failed: {e!s}")
    return None


def upload(data, file_path):
    if not s3:
        logger.warning("S3 not available - upload operation skipped")
        return None

    try:
        # Check if file_path already includes the avatar prefix
        if file_path.startswith("avatar/"):
            s3_key = file_path
        else:
            s3_key = f"avatar/{file_path}"

        # Ensure the data is at the beginning
        if hasattr(data, "seek"):
            data.seek(0)

        s3.upload_fileobj(
            data,
            os.getenv("AWS_BUCKET_NAME"),
            s3_key,
            ExtraArgs={
                "ContentType": "image/png",
                "ACL": "private",  # or 'public-read' if you want it public
            },
        )
        return s3_key

    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        return None


def delete(prefix, file_path):
    if not s3:
        logger.warning("S3 not available - delete operation skipped")
        return

    try:
        # Check if file_path already includes the prefix
        if file_path.startswith(f"{prefix}/"):
            s3_key = file_path
        else:
            s3_key = f"{prefix}/{file_path}"

        s3.delete_object(
            Bucket=os.getenv("AWS_BUCKET_NAME"),
            Key=s3_key,
        )
    except Exception as e:
        logger.error(f"S3 delete failed: {e}")
        return


def get_presigned_url(prefix, file_path, expiration=3600):
    if not s3:
        logger.warning("S3 not available - returning dummy URL")
        return f"https://example.com/{prefix}/{file_path}"

    try:
        # Check if file_path already includes the prefix
        if file_path.startswith(f"{prefix}/"):
            s3_key = file_path
        else:
            s3_key = f"{prefix}/{file_path}"

        url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": os.getenv("AWS_BUCKET_NAME"),
                "Key": s3_key,
            },
            ExpiresIn=expiration,  # seconds
        )
        return url
    except Exception as e:
        logger.error("Error generating pre-signed URL:", e)
        return None


def get_random_image(prefix, file_path, expiration=3600):
    if not s3:
        logger.warning("S3 not available - returning None for random image")
        return None

    try:
        response = s3.list_objects_v2(
            Bucket=os.getenv("AWS_BUCKET_NAME"),
            Prefix=prefix,
        )
        if "Contents" in response:
            file_keys = [
                item["Key"].removeprefix(f"{prefix}/")
                for item in response["Contents"]
                if item["Key"].removeprefix(f"{prefix}/") != file_path
            ]
            return random.choice(file_keys)
        return None
    except Exception as e:
        logger.error("Error generating pre-signed URL:", e)
        return None
