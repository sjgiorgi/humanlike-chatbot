import os

import boto3
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def get_presigned_url(request):
    file_name = request.GET.get("filename")
    content_type = request.GET.get("content_type")

    if settings.BACKEND_ENVIRONMENT == "local":
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION"),
        )
    else:
        s3_client = boto3.client(
            "s3",
            region_name=os.getenv("AWS_REGION"),
        )

    url = s3_client.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": os.getenv("AWS_BUCKET_NAME"),
            "Key": f"uploads/{file_name}",
            "ContentType": content_type,
        },
        ExpiresIn=300,
        HttpMethod="PUT",
    )

    return JsonResponse(
        {
            "s3_url": url,
            "file_url": f"https://{os.getenv('AWS_BUCKET_NAME')}.s3.amazonaws.com/uploads/{file_name}",
        },
        status=200,
    )
