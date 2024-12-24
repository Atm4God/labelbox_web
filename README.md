# Labelbox Web Application

## Overview
A web-based annotation platform built with Django and MongoDB for collaborative image labeling.

## Features
- Create annotation projects
- Upload and annotate images
- Store annotations directly in MongoDB
- Web-based annotation interface

## Prerequisites
- Python 3.9+
- MongoDB
- pip

## Installation

1. Clone the repository
2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
Create a `.env` file with:
```
DJANGO_SECRET_KEY=your_secret_key
MONGODB_NAME=labelbox_db
MONGODB_HOST=localhost
MONGODB_PORT=27017
```

5. Run migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

6. Create superuser
```bash
python manage.py createsuperuser
```

7. Run development server
```bash
python manage.py runserver
```

## Deployment Considerations
- Use gunicorn/uwsgi for production
- Configure MongoDB connection for production environment
- Use environment-specific settings

## Security Notes
- Always use strong, unique passwords
- Keep `SECRET_KEY` confidential
- Use HTTPS in production