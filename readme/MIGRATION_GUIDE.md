# Database Migration Guide - Creating Patient and Appointment Tables

## Prerequisites

1. **PostgreSQL is running** and accessible
2. **Database exists**: The database `clinic_db` should exist (or create it)
3. **Environment variables**: `.env` file is configured with `DATABASE_URL`

## Step-by-Step Instructions

### Step 1: Ensure Database Exists

If the database doesn't exist yet, create it:

```bash
# Connect to PostgreSQL
psql -U clinic_db -h localhost

# Or if using postgres user:
psql -U postgres -h localhost

# Create database
CREATE DATABASE clinic_db;
CREATE USER clinic_db WITH PASSWORD 'clinic';
GRANT ALL PRIVILEGES ON DATABASE clinic_db TO clinic_db;
\q
```

### Step 2: Install Dependencies (if not already done)

Since you're using `uv`, make sure dependencies are installed:

```bash
uv sync
```

### Step 3: Initialize Migrations (First Time Only)

If migrations haven't been initialized yet:

```bash
export FLASK_APP=run.py
uv run flask db init
```

This creates the `migrations/versions/` directory.

**Note**: If you get "Error: Directory migrations already exists", migrations are already initialized - skip to Step 4.

### Step 4: Create Initial Migration

Generate a migration file that will create the Patient and Appointment tables:

```bash
export FLASK_APP=run.py
uv run flask db migrate -m "Create patient and appointment tables"
```

This will:
- Scan your models (Patient and Appointment)
- Generate a migration file in `migrations/versions/`
- Include all the columns and relationships defined in your models

### Step 5: Review the Migration File

Check the generated migration file in `migrations/versions/` to ensure it looks correct:
- Should create `patients` table with all columns
- Should create `appointments` table with foreign key to `patients`

### Step 6: Apply the Migration

Apply the migration to create the tables in your database:

```bash
export FLASK_APP=run.py
uv run flask db upgrade
```

This will:
- Execute the SQL to create the tables
- Create a `alembic_version` table to track migrations

### Step 7: Verify Tables Created

Verify the tables were created successfully:

```bash
psql -U clinic_db -h localhost -d clinic_db -c "\dt"
```

Or check specific table structure:

```bash
psql -U clinic_db -h localhost -d clinic_db -c "\d patients"
psql -U clinic_db -h localhost -d clinic_db -c "\d appointments"
```

## Quick Command Reference (Using uv)

```bash
# Set Flask app (or add to your shell profile)
export FLASK_APP=run.py

# Initialize migrations (first time only)
uv run flask db init

# Create migration
uv run flask db migrate -m "Your migration message"

# Apply migration
uv run flask db upgrade

# Check migration status
uv run flask db current

# Rollback last migration
uv run flask db downgrade
```

## Troubleshooting

### Issue: "Target database is not up to date"
**Solution**: Run `flask db upgrade` to apply pending migrations

### Issue: "Can't locate revision identified by..."
**Solution**: If migrations are corrupted, you may need to:
1. Drop and recreate the database
2. Run `flask db init` again
3. Create a fresh migration

### Issue: "No such table: alembic_version"
**Solution**: Run `flask db stamp head` to mark the database as up-to-date

### Issue: Connection refused
**Solution**: 
- Check PostgreSQL is running: `sudo systemctl status postgresql`
- Verify DATABASE_URL in `.env` is correct
- Check database credentials

## What Gets Created

### `patients` Table
- `id` (String, Primary Key) - e.g., "P001"
- `clinic_id` (String, Unique)
- `title`, `first_name`, `last_name`, `gender`
- `birth_date`, `phone`, `email`
- `identity_number`, `height`, `weight`, `blood_group`
- `notes`, `primary_doctor`
- `new_patient` (Boolean)
- `demographics` (Text)
- `created_at`, `updated_at` (Timestamps)

### `appointments` Table
- `id` (Integer, Primary Key)
- `patient_id` (String, Foreign Key → patients.id)
- `doctor`, `department`
- `date`, `time`
- `status` (String, default: 'Waiting')
- `created_at`, `updated_at` (Timestamps)

## Next Steps

After tables are created, you can:
1. Start implementing route handlers in `app/routes/`
2. Implement service layer in `app/services/`
3. Test database operations with your Flask app
