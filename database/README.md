# VantageNet Database Migrations

This directory contains Alembic database migrations for VantageNet.

## Setup

1. Install dependencies:
```bash
pip install alembic psycopg2-binary
```

2. Configure database connection in `alembic.ini`

3. Run migrations:
```bash
# Upgrade to latest
alembic upgrade head

# Downgrade one revision
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

## Creating New Migrations

```bash
# Auto-generate from model changes
alembic revision --autogenerate -m "Description of changes"

# Create empty migration
alembic revision -m "Description of changes"
```

## Directory Structure

```
database/
├── README.md           # This file
├── alembic.ini         # Alembic configuration
├── env.py              # Alembic environment configuration
└── versions/           # Migration scripts
    └── 001_initial_schema.py
```

## Database Connection

Default connection string:
```
postgresql://vantage:vantage_secret@localhost:5434/vantage_db
```

Override with environment variable:
```bash
export DATABASE_URL="postgresql://user:pass@host:port/dbname"
```

## Notes

- The `init-scripts/01-init.sql` is used for Docker initialization
- Alembic migrations are for programmatic schema changes
- Always test migrations on a development database first
- Create backups before running migrations in production
