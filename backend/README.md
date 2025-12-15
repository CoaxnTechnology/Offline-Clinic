clinic_pacs_flask/
│
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── config.py                # App & DB configuration
│   │
│   ├── extensions/
│   │   ├── __init__.py
│   │   ├── db.py                # SQLAlchemy instance
│   │   ├── migrate.py           # Flask-Migrate (Alembic)
│   │   ├── jwt.py               # Auth (JWT / session)
│   │   └── cache.py             # Redis (optional)
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── patient.py
│   │   ├── study.py
│   │   ├── series.py
│   │   ├── image.py
│   │   ├── report.py
│   │   └── audit_log.py
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py              # Login / logout
│   │   ├── patients.py          # Patient CRUD
│   │   ├── studies.py           # Study & workflow
│   │   ├── images.py            # Viewer APIs
│   │   ├── reports.py           # Reporting APIs
│   │   └── admin.py             # Users, roles
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── dicom_receiver.py    # pynetdicom SCP
│   │   ├── dicom_parser.py      # Metadata extraction
│   │   ├── thumbnailer.py       # Thumbnail generation
│   │   ├── report_generator.py  # PDF generation
│   │   └── audit_service.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user_schema.py       # Marshmallow / Pydantic
│   │   ├── patient_schema.py
│   │   ├── study_schema.py
│   │   └── report_schema.py
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   └── dicom_tasks.py       # Celery background jobs
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── security.py          # Password hashing
│   │   ├── permissions.py       # RBAC checks
│   │   ├── file_utils.py
│   │   └── constants.py
│   │
│   └── templates/               # (Optional) server-side HTML
│       └── reports/
│
├── migrations/                  # Alembic versions
│
├── storage/
│   ├── dicom/                   # Raw DICOM files
│   ├── thumbnails/
│   └── reports/
│
├── tests/
│   ├── test_auth.py
│   ├── test_patients.py
│   └── test_dicom.py
│
├── venv/
│
├── run.py                       # App entry point
├── celery_worker.py             # Background worker
├── requirements.txt
├── .env
└── README.md

