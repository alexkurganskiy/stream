from botocore.client import Config
import boto3

from app.core.settings import get_settings


class S3Service:
    def __init__(self) -> None:
        settings = get_settings()
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name="us-east-1",
            use_ssl=False,
            config=Config(signature_version="s3v4"),
        )

    def presign_get(self, key: str, expires: int = 30) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires,
        )

    def put_object(self, key: str, body: bytes, content_type: str | None = None) -> None:
        extra = {"ContentType": content_type} if content_type else {}
        self.client.put_object(Bucket=self.bucket, Key=key, Body=body, **extra)

    def download_file(self, key: str, destination: str) -> None:
        self.client.download_file(self.bucket, key, destination)


s3_service = S3Service()
