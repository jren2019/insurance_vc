# Database Setup Summary

This document summarizes the database infrastructure created for the OIDC backend with PostgreSQL.

## 🗄️ Database Schema

### Credential Table
```sql
CREATE TABLE credential (
    id SERIAL PRIMARY KEY,
    credential_id VARCHAR(50) UNIQUE NOT NULL,
    subject_id VARCHAR(255),
    type VARCHAR(50) NOT NULL,
    format VARCHAR(50) NOT NULL DEFAULT 'ISO mdoc',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    issued TIMESTAMP NOT NULL DEFAULT NOW(),
    expires TIMESTAMP
);
```

### Verification Log Table
```sql
CREATE TABLE verification_log (
    id SERIAL PRIMARY KEY,
    checked_at TIMESTAMP NOT NULL DEFAULT NOW(),
    credential_id VARCHAR(50) NOT NULL REFERENCES credential(credential_id),
    result VARCHAR(10) NOT NULL,
    response_time INTEGER NOT NULL,
    verifier VARCHAR(100) NOT NULL
);
```

## 📁 Files Created

### Core Database Files
- `models.py` - SQLAlchemy ORM models for Credential and VerificationLog
- `database.py` - Database initialization and session management
- `config.py` - Configuration management with database settings

### Migration Files
- `alembic.ini` - Alembic configuration
- `migrations/env.py` - Alembic environment setup
- `migrations/script.py.mako` - Migration template
- `migrations/versions/0001_initial_migration.py` - Initial migration

### Management Scripts
- `manage_db.py` - Database management script with commands for init, migrate, seed, setup
- `setup.sh` - Automated setup script
- `test_db.py` - Database testing script

### Application Files
- `app_with_db.py` - Enhanced Flask app with database integration and API endpoints
- `requirements.txt` - Python dependencies including SQLAlchemy and Alembic

### Configuration
- `env.example` - Environment variables template
- `README.md` - Comprehensive setup and usage documentation

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Database
```bash
# Option A: Automated setup
./setup.sh

# Option B: Manual setup
python manage_db.py setup
```

### 3. Run Application
```bash
python app_with_db.py
```

## 📊 Available Endpoints

### Database API Endpoints
- `GET /api/credentials` - Get all credentials
- `GET /api/credentials/<id>` - Get specific credential
- `POST /api/credentials` - Create new credential
- `GET /api/verification-logs` - Get all verification logs
- `POST /api/verification-logs` - Create new verification log
- `GET /api/credentials/<id>/verification-logs` - Get logs for specific credential

### Web Interfaces
- `GET /dashboard` - Database dashboard with statistics and tables
- `GET /verify` - Credential verification UI
- `GET /form_credential` - Credential request form

## 🛠️ Database Management Commands

```bash
# Initialize database tables
python manage_db.py init

# Run migrations
python manage_db.py migrate

# Seed with sample data
python manage_db.py seed

# Complete setup (init + migrate + seed)
python manage_db.py setup

# Test database functionality
python test_db.py
```

## 📋 Sample Data

The seeding script includes sample data matching your table images:

### Sample Credentials
- ACC-418277-QLKO (Account, active)
- CUS-919371-AZ5X (Custom, active)
- MEM-167754-P2N8 (Membership, revoked)
- IDT-240031-E104 (Identity, active)
- And more...

### Sample Verification Logs
- Various verification attempts with different results (PASS/FAIL)
- Different verifier systems (Web-Portal-002, External-API-002, Mobile-App-Android, etc.)
- Response times and timestamps

## 🔧 Configuration

Key configuration options in `config.py`:
- `SQLALCHEMY_DATABASE_URI` - Database connection string
- `ISSUER` - OIDC issuer identifier
- `CONFIG_ID` - Supported credential configuration ID

Environment variables in `.env`:
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - Flask secret key
- `FLASK_ENV` - Flask environment

## 🧪 Testing

Run the test script to verify database functionality:
```bash
python test_db.py
```

This will test:
- Database connection
- CRUD operations on credentials and verification logs
- Relationships between tables
- API endpoints

## 📈 Database Dashboard

Access the dashboard at `http://localhost:5000/dashboard` to see:
- Statistics (total credentials, active credentials, verification counts)
- Credentials table with all fields
- Verification logs table with recent entries
- Real-time data from the database

## 🔄 Migrations

To create new migrations after model changes:
```bash
# Generate migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1
```

## 🐛 Troubleshooting

### Common Issues
1. **Database Connection Error**
   - Check PostgreSQL is running
   - Verify database credentials in `.env`
   - Ensure database exists

2. **Migration Errors**
   - Check Alembic configuration
   - Verify model imports in `migrations/env.py`

3. **Import Errors**
   - Ensure all dependencies are installed
   - Check Python path includes project directory

### Getting Help
- Check the main `README.md` for detailed setup instructions
- Run `python test_db.py` to diagnose database issues
- Use `python manage_db.py help` for command help

## 🎯 Next Steps

1. **Customize Models**: Modify `models.py` to add new fields or tables
2. **Add Business Logic**: Extend the API endpoints in `app_with_db.py`
3. **Production Setup**: Configure proper database credentials and security
4. **Monitoring**: Add logging and monitoring for database operations
5. **Backup**: Set up database backup procedures

## 📝 Notes

- The database uses PostgreSQL with SQLAlchemy ORM
- Migrations are managed with Alembic
- Sample data is included for testing and demonstration
- The setup is designed for development but can be adapted for production
- All database operations include proper error handling and rollback 