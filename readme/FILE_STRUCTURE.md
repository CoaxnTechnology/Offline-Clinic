# File Structure Documentation

This document provides an overview of the Clinic Backend project structure.

## Project Overview

**Clinic DICOM Flask Backend** - An offline clinic workflow system with DICOM imaging and reporting capabilities built with Flask.

## Root Directory

```
backend/
├── .env                    # Environment variables (not tracked in git)
├── .gitignore             # Git ignore rules
├── .python-version        # Python version specification
├── pyproject.toml         # Project configuration and dependencies
├── requirements.txt       # Python package dependencies
├── uv.lock                # UV package manager lock file
├── README.md              # Project documentation
├── run.py                 # Application entry point
├── dicom_listener.py      # DICOM network listener service
├── app/                   # Main application package
├── migrations/            # Database migration files (Alembic)
├── tasks/                 # Background task definitions (Celery)
└── tests/                 # Test files
```

## Directory Structure

### `/app` - Main Application Package

The core Flask application package containing all application logic.

```
app/
├── __init__.py            # Flask app factory and extension initialization
├── config.py              # Application configuration settings
├── extensions.py          # Flask extension instances
│
├── models/                # SQLAlchemy database models
│   ├── __init__.py        # Model exports
│   ├── base.py            # Base model class
│   ├── patient.py         # Patient model
│   ├── appointment.py     # Appointment model
│   └── audit_log.py       # Audit logging model
│
├── routes/                # Flask route handlers (blueprints)
│   ├── __init__.py        # Route blueprint registration
│   ├── admin.py           # Admin routes
│   ├── auth.py            # Authentication routes
│   ├── patient.py         # Patient management routes
│   ├── appointment.py     # Appointment routes
│   ├── dicom.py           # DICOM-related routes
│   └── reporting.py       # Report generation routes
│
├── services/              # Business logic layer
│   ├── __init__.py        # Service exports
│   ├── auth_service.py    # Authentication service
│   ├── patient_service.py # Patient management service
│   ├── dicom_service.py   # DICOM processing service
│   ├── report_service.py  # Report generation service
│   ├── workflow_service.py # Workflow management service
│   └── audit_service.py   # Audit logging service
│
└── utils/                 # Utility functions
    ├── __init__.py        # Utility exports
    ├── dicom_utils.py     # DICOM file utilities
    ├── pdf_utils.py       # PDF generation utilities
    ├── thumbnail_utils.py # Image thumbnail utilities
    └── validators.py      # Input validation utilities
```

### `/migrations` - Database Migrations

Alembic migration files for database schema management.

```
migrations/
├── alembic.ini            # Alembic configuration
├── env.py                 # Alembic environment setup
├── script.py.mako         # Migration script template
└── README                 # Migration documentation
```

### `/tasks` - Background Tasks

Celery task definitions for asynchronous processing.

```
tasks/
├── __init__.py            # Task module initialization
├── dicom_tasks.py         # DICOM processing tasks
├── report_tasks.py        # Report generation tasks
└── sync_tasks.py          # Data synchronization tasks
```

### `/tests` - Test Suite

Unit and integration tests for the application.

```
tests/
├── __init__.py            # Test package initialization
└── test_patient.py        # Patient model/service tests
```

## Key Files

### Configuration Files

- **`pyproject.toml`**: Project metadata, dependencies, and build configuration
- **`requirements.txt`**: Python package dependencies list
- **`.env`**: Environment variables (database URLs, secrets, etc.)
- **`app/config.py`**: Flask application configuration class

### Entry Points

- **`run.py`**: Main application entry point for running the Flask server
- **`dicom_listener.py`**: DICOM network listener service (runs separately)

### Application Core

- **`app/__init__.py`**: Flask app factory function, initializes extensions
- **`app/extensions.py`**: Flask extension instances (db, migrate, etc.)

## Technology Stack

- **Web Framework**: Flask 3.0+
- **ORM**: Flask-SQLAlchemy
- **Migrations**: Flask-Migrate (Alembic)
- **Authentication**: Flask-Login, Flask-Bcrypt
- **DICOM**: pynetdicom, pydicom
- **Task Queue**: Celery with Redis
- **PDF Generation**: WeasyPrint
- **Image Processing**: Pillow
- **Database**: PostgreSQL (psycopg2-binary)
- **Web Server**: Gunicorn
- **Real-time**: Flask-SocketIO

## Architecture Pattern

The project follows a **layered architecture**:

1. **Routes Layer** (`app/routes/`): HTTP request handlers, input validation
2. **Services Layer** (`app/services/`): Business logic and orchestration
3. **Models Layer** (`app/models/`): Database models and data access
4. **Utils Layer** (`app/utils/`): Reusable utility functions

This separation ensures:
- Clear separation of concerns
- Easier testing and maintenance
- Reusable business logic
- Clean API endpoints

## Notes

- The `.env` file is not tracked in git (should contain sensitive configuration)
- Database migrations are managed through Alembic in the `migrations/` directory
- Background tasks use Celery and are defined in the `tasks/` directory
- DICOM listener runs as a separate service for handling DICOM network communications
