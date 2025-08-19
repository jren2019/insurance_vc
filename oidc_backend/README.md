# OIDC Backend with PostgreSQL Database

This is a Flask backend for a credential management platform with PostgreSQL database support.

## Features

- **Credential Management**: Issue and revoke credentials
- **Verification Logging**: Track credential verification attempts
- **PostgreSQL Database**: Robust database with migrations
- **OIDC4VCI Support**: OpenID Connect for Verifiable Credential Issuance
- **ISO 18013-5 mdoc**: Mobile driving license format support

## Database Schema

### Credential Table
- `id`: Primary key (auto-increment)
- `credential_id`: Unique credential identifier (e.g., "ACC-418277-QLKO")
- `subject_id`: Subject identifier (can be null)
- `type`: Credential type (Account, Custom, Membership, Identity)
- `format`: Credential format (default: "ISO mdoc")
- `status`: Credential status (active, revoked)
- `issued`: Issue date
- `expires`: Expiration date (can be null for "Never")

### Verification Log Table
- `id`: Primary key (auto-increment)
- `checked_at`: Verification timestamp
- `credential_id`: Foreign key to credential table
- `result`: Verification result (PASS, FAIL)
- `response_time`: Response time in milliseconds
- `verifier`: System that performed verification

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Database Setup

#### Option A: Using PostgreSQL (Recommended)

1. **Install PostgreSQL** (if not already installed)
   ```bash
   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib
   
   # macOS with Homebrew
   brew install postgresql
   ```

2. **Create Database**
   ```bash
   sudo -u postgres psql
   CREATE DATABASE oidc;
   CREATE USER oidc_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE oidc TO oidc_user;
   \q
   ```

3. **Configure Environment**
   ```bash
   cp env.example .env
   # Edit .env with your database credentials
   ```

#### Option B: Using Docker

```bash
docker run --name postgres-oidc -e POSTGRES_PASSWORD=password -e POSTGRES_DB=oidc -p 5432:5432 -d postgres:13
```

### 3. Database Migration and Setup

```bash
# Initialize database tables
python manage_db.py init

# Run migrations
python manage_db.py migrate

# Seed with sample data
python manage_db.py seed

# Or do all at once
python manage_db.py setup
```

### 4. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Database Management

### Available Commands

```bash
python manage_db.py init      # Initialize database tables
python manage_db.py migrate   # Run database migrations
python manage_db.py seed      # Seed with sample data
python manage_db.py setup     # Initialize, migrate, and seed
python manage_db.py help      # Show help
```

### Creating New Migrations

```bash
# Generate a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1
```

## API Endpoints

### OIDC4VCI Endpoints
- `GET /.well-known/oauth-authorization-server` - OAuth metadata
- `GET /.well-known/openid-credential-issuer` - OIDC4VCI metadata
- `POST /offer` - Generate credential offer
- `POST /token` - Exchange pre-authorized code for access token
- `POST /nonce` - Get nonce for proof
- `POST /credential` - Issue credential

### Demo Endpoints
- `GET /verify` - Manual credential verification UI
- `GET /request_credential` - One-click demo flow
- `GET /form_credential` - Form-based credential request

## Sample Data

The seeding script includes sample data matching the tables shown in your images:

### Sample Credentials
- ACC-418277-QLKO (Account, active)
- CUS-919371-AZ5X (Custom, active)
- MEM-167754-P2N8 (Membership, revoked)
- And more...

### Sample Verification Logs
- Various verification attempts with different results
- Different verifier systems (Web-Portal-002, External-API-002, etc.)
- Response times and timestamps

## Configuration

Key configuration options in `config.py`:

- `SQLALCHEMY_DATABASE_URI`: Database connection string
- `ISSUER`: OIDC issuer identifier
- `CONFIG_ID`: Supported credential configuration ID
- `ALG_COSE`/`ALG_JOSE`: Cryptographic algorithms

## Development

### Project Structure
```
oidc_backend/
├── app.py              # Main Flask application
├── config.py           # Configuration settings
├── models.py           # SQLAlchemy ORM models
├── database.py         # Database initialization
├── manage_db.py        # Database management script
├── requirements.txt    # Python dependencies
├── alembic.ini        # Alembic configuration
├── migrations/        # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
└── README.md          # This file
```

### Adding New Models

1. Add model to `models.py`
2. Generate migration: `alembic revision --autogenerate -m "Add new model"`
3. Apply migration: `alembic upgrade head`

## Troubleshooting

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

## License

This project is for demonstration purposes. Use appropriate licensing for production deployments. 

# TLS/HTTPS with Let's Encrypt (Certbot)

This project includes an automated Certbot container and Nginx configuration for HTTPS.

## Prerequisites
- A DNS A record pointing issuance-vc.australiaeast.cloudapp.azure.com to your server's public IP
- Port 80 and 443 open to the Internet
- Set your email in the environment variable `LETSENCRYPT_EMAIL` in `.env` (used for certificate renewal notices)

## One-time certificate issuance
1. Start Nginx so the ACME HTTP challenge can be served:
   ```bash
   docker-compose up -d nginx certbot
   ```
2. Obtain the initial certificate (run on the host):
   ```bash
   docker run --rm \
     -v certbot-etc:/etc/letsencrypt \
     -v certbot-www:/var/www/certbot \
     --network oidc_oidc_network \
     certbot/certbot certonly --webroot \
     -w /var/www/certbot \
     -d issuance-vc.australiaeast.cloudapp.azure.com \
     --email "$LETSENCRYPT_EMAIL" --agree-tos --non-interactive
   ```
3. Reload Nginx to pick up the new certificates:
   ```bash
   docker-compose restart nginx
   ```

## Automatic renewal
- The `certbot` service runs `certbot renew` twice a day. Nginx will use renewed certs automatically; you can schedule a monthly reload:
  ```bash
  docker-compose exec nginx nginx -s reload
  ```

## Notes
- Certificates are stored in the `certbot-etc` named volume and mounted read-only into Nginx.
- ACME challenges are served from `/.well-known/acme-challenge/` via the `certbot-www` volume. 