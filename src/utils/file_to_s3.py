import aiohttp
import uuid
from fastapi import HTTPException


from src.utils.s3 import upload_file_to_s3
from src.config import TELEGRAM_ID


TELEGRAM_BOT_TOKEN = TELEGRAM_ID 


async def fetch_and_upload_from_telegram(file_id: str, folder: str) -> str:
    """
    Download a Telegram file using its file_id and upload to S3.
    """
    async with aiohttp.ClientSession() as session:
        # Step 1: Get file path from Telegram
        async with session.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
        ) as resp:
            data = await resp.json()
            if not data.get("ok"):
                raise HTTPException(status_code=400, detail="Invalid Telegram file_id")
            file_path = data["result"]["file_path"]

        # Step 2: Download file
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        async with session.get(file_url) as resp:
            content = await resp.read()

        # Step 3: Upload to S3
        ext = file_path.split(".")[-1]
        unique_name = f"{folder}/{uuid.uuid4().hex}.{ext}"
        s3_path = await upload_file_to_s3(content, unique_name, f"audio/{ext}")
        if not s3_path:
            raise HTTPException(status_code=500, detail="Failed to upload Telegram file to S3")
        return s3_path
