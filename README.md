# FastAPI Crowdsource Backend

This project implements a scalable and modular FastAPI backend for a Telegram-based crowdsourced data collection platform. It supports multimodal data (audio, text, image) collection, task allocation, review workflows, S3 storage, analytics, and reward tracking.

## Features

- **User Roles**: Contributor, Reviewer, Super Reviewer, Admin.
- **Task Management**: Create, allocate, and track audio, text, and image tasks.
- **Multimodal Data Collection**: Handle audio, text, and image submissions.
- **AWS S3 Integration**: Securely store audio and image files.
- **PostgreSQL Database**: Store all metadata and application data using SQLModel.
- **Analytics & Reporting**: Track contributor and reviewer performance, with data export capabilities.
- **Telegram Integration Hooks**: Facilitate communication and task assignment via Telegram.
- **Modular Architecture**: Organized into routers, models, and utilities for maintainability.

## Project Structure

```
fastapi_crowdsource_backend/
├── main.py
├── database.py
├── models.py
├── requirements.txt
├── test_main.py
├── .env.example
├── routers/
│   ├── __init__.py
│   ├── users.py
│   ├── tasks.py
│   ├── submissions.py
│   ├── task_allocation.py
│   ├── telegram.py
│   └── analytics.py
└── utils/
    ├── __init__.py
    └── s3.py
```

## Setup Instructions

### 1. Clone the repository (if applicable)

```bash
git clone <repository_url>
cd fastapi_crowdsource_backend
```

### 2. Create a virtual environment and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Database Setup (PostgreSQL)

Ensure you have a PostgreSQL database running. You can use Docker for a quick setup:

```bash
docker run --name crowdsource-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=password -e POSTGRES_DB=crowdsource_db -p 5432:5432 -d postgres
```

### 4. Environment Variables

Create a `.env` file in the root directory of the project based on `.env.example` and fill in the details:

```
DATABASE_URL="postgresql://postgres:password@localhost/crowdsource_db"
AWS_ACCESS_KEY_ID="your_aws_access_key_id"
AWS_SECRET_ACCESS_KEY="your_aws_secret_access_key"
AWS_REGION="your_aws_region" # e.g., us-east-1
AWS_S3_BUCKET_NAME="your_s3_bucket_name"
```

### 5. Run the Application

```bash
uvicorn main:app --reload
```

The API documentation will be available at `http://127.0.0.1:8000/docs`.

## API Endpoints

Detailed API endpoints are available in the automatically generated OpenAPI documentation at `/docs` when the application is running. Key endpoints include:

- `/api/users/`: User management (CRUD)
- `/api/tasks/`: Task management (CRUD)
- `/api/audio_submissions/`, `/api/text_submissions/`, `/api/image_submissions/`: Submission management (CRUD)
- `/api/upload_audio/`, `/api/upload_image/`: File upload to S3
- `/api/task_allocation/`: Task allocation and status checks
- `/api/telegram/register`, `/api/telegram/status/{telegram_id}`, `/api/telegram/notify`: Telegram integration hooks
- `/api/analytics/contributor`, `/api/analytics/reviewer`: Analytics dashboards
- `/api/export_data/{data_type}`: Export data to Excel/CSV

## Testing

To run tests, ensure you have `pytest` and `httpx` installed (included in `requirements.txt`):

```bash
pytest
```

## Deployment

For production deployment, consider using Gunicorn with Nginx or a cloud-specific deployment service (e.g., AWS Elastic Beanstalk, Google Cloud Run, Azure App Service). Ensure your environment variables are properly configured for the production environment.


# crowd_gram_backend
