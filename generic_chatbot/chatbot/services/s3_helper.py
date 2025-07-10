import os
import io
from PIL import Image
import boto3

s3 = boto3.client(
        's3',
        region_name=os.getenv("AWS_REGION")
    )

def download(prefix, file_path):
    try:
        # Step 1: Download image from S3
        s3_response = s3.get_object(Bucket=os.getenv("AWS_BUCKET_NAME"), Key=f'{prefix}/{file_path}')
        image_data = s3_response['Body'].read()

        # Step 2: Load into PIL (or whatever your processing pipeline uses)
        return Image.open(io.BytesIO(image_data))
    
    except s3.exceptions.NoSuchKey:
        print({"error": "Image not found in S3"})
    except Exception as e:
        print({"error": str(e)})
    return None

def upload(data, file_path):
    try:
        s3.upload_fileobj(
            data,
            os.getenv("AWS_BUCKET_NAME"),
            f'avatar/{file_path}',
            ExtraArgs={
                "ContentType": 'PNG',
                "ACL": "private"  # or 'public-read' if you want it public
            }
        )
        return f'avatar/{file_path}'

    except Exception as e:
        print(f'[ERROR] {e}')
        return None

def delete(prefix, file_path):
    try:
        s3.delete_object(Bucket=os.getenv("AWS_BUCKET_NAME"), Key=f'{prefix}/{file_path}')
    except Exception as e:
        print(f'[ERROR] {e}')
        return None

def get_presigned_url(prefix, file_path, expiration=1000):
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': os.getenv("AWS_BUCKET_NAME"),
                'Key': f'{prefix}/{file_path}'
            },
            ExpiresIn=expiration  # seconds
        )
        return url
    except Exception as e:
        print("Error generating pre-signed URL:", e)
        return None