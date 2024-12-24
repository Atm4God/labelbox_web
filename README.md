# Labelbox Web Application

## Overview
A web-based annotation platform built with Django and LabelBox for collaborative image labeling.

## Features
- Create annotation projects
- Upload and annotate images
- Store annotations directly in Postgres
- Web-based annotation interface

## Prerequisites
- Python 3.9+
- PostgreSQL
- pip
- labelbox==6.4.0

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
LABELBOX_API_KEY=key
DB_NAME=labelbox
DB_USER=postgres
DB_PASSWORD=Password
DB_HOST=localhost
DEBUG_MODE=False
PRETORIAL_PASS=pass
PRETORIAL_USER=user
```

5. Run migrations
```bash
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

## Usage
- Create a project
- View pending tasks
- Add annotations
- Use the "Bounding Box" button to draw boxes on the canvas. 
- Add classification fields dynamically as needed. 
- Save your annotations using the "Save Annotation" button.

## Deployment Considerations
- Use gunicorn/uwsgi for production
- Configure Postgresql connection for production environment
- Use environment-specific settings

## Security Notes
- Always use strong, unique passwords
- Keep `SECRET_KEY` confidential
- Use HTTPS in production