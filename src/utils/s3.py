import aiobotocore.session, aiobotocore, os
from aiobotocore.session import AioSession 
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")



async def upload_file_to_s3(file_content: bytes, file_name: str, content_type: str) -> str | None:
    """
    Upload a file asynchronously to S3 and return the public URL.

    Args:
        file_content (bytes): File content in bytes.
        file_name (str): Full S3 key (can include folder prefix).
        content_type (str): MIME type of the file (e.g., audio/mpeg, image/png).

    Returns:
        str | None: Public S3 URL if successful, None otherwise.
    """
    session = aiobotocore.session.AioSession()  # ✅ use AioSession
    try:
        async with session.create_client(
            "s3",
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,

        ) as client:
            response = await client.put_object(
                Bucket=AWS_S3_BUCKET_NAME,
                Key=file_name,
                Body=file_content,
                ContentType=content_type,
            )
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                return f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{file_name}"
    except Exception as e:
        print(f"[S3 Upload Error] {e}")
    return None
