import os
from dotenv import load_dotenv

load_dotenv()


OBS_SECRET_ACCESS_KEY=os.getenv("OBS_SECRET_ACCESS_KEY", "Yours")
OBS_ENDPOINT_URL=os.getenv("OBS_ENDPOINT_URL", "Yours")
OBS_REGION=os.getenv("OBS_REGION", "Yours")
OBS_BUCKET_NAME=os.getenv("OBS_BUCKET_NAME", "Yours")
TELEGRAM_ID=os.getenv("TELEGRAM_ID", "Yours")
OBS_ENDPOINT_URL=os.getenv("OBS_ENDPOINT_URL", "Yours")
DATABASE_URL = os.getenv("DATABASE_URL", "Yours")


SECRET_KEY = os.getenv("SECRET_KEY", "Yours")
ALGORITHM = os.getenv("ALGORITHM", "Yours")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))