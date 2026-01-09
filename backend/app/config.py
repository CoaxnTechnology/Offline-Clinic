class Config:
    SQLALCHEMY_DATABASE_URI = (
        "postgresql://postgres:clinic@localhost:5432/clinic_db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "dev-secret"
