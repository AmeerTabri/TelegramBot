import os
import boto3

AWS_REGION = "us-east-1"
AWS_S3_BUCKET = "ameer-polybot-images-dev"


s3 = boto3.client('s3', region_name=AWS_REGION)


def upload_image_to_s3(local_path, s3_key):
    s3.upload_file(local_path, AWS_S3_BUCKET, s3_key)


def download_predicted_image_from_s3(chat_id: str, image_name: str, local_path: str):
    s3_key = f"{chat_id}/predicted/{image_name}"
    s3.download_file(AWS_S3_BUCKET, s3_key, local_path)