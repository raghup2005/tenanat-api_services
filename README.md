Multi-Tenant API Service
A backend API service built with FastAPI that provides API-key authentication, tenant-specific rate limiting, daily request quotas, usage tracking, and Redis caching. PostgreSQL stores tenant and usage data, while Docker Compose runs the application and its supporting services.
Features
- API-key authentication — API keys use the tsk_ prefix; SHA-256 hashes are stored rather than raw keys.
- Tenant isolation — authenticated tenants can access only their own tenant and usage information.
- Rate limiting — Redis-backed, per-tenant request limits with HTTP 429 Too Many Requests responses when limits are exceeded.
- Daily quotas — tracks daily usage and rejects requests when a tenant reaches its configured quota.
- Usage tracking — PostgreSQL records usage per tenant and date.
- Redis caching — usage results are cached with a 30-second TTL, with a database fallback if caching fails.
- Request logging — middleware logs incoming requests.
- Containerized development — Docker Compose runs the API, PostgreSQL, and Redis.
- Automated tests — unit and integration tests cover authentication, rate limits, quotas, and tenant usage.
Technology Stack
- Python 3.10
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- Docker and Docker Compose
- Pytest
Architecture
Client
  |
  | X-API-Key
  v
FastAPI application
  |
  +--> API-key authentication and tenant isolation
  |
  +--> Redis: rate-limit counters and usage cache
  |
  +--> PostgreSQL: tenants and daily usage records
Project Structure
tenant-api-service/
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   └── services/
├── tests/
├── .dockerignore
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
Getting Started
Prerequisites
- Python 3.10
- Docker Desktop with Docker Compose
- Git (optional, for cloning the repository)
1. Start the services
From the project directory, build and start the containers:
docker compose up --build -d
Check the container status:
docker compose ps
2. Verify the API
- Swagger UI: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health
The health endpoint should return a response similar to:
{
  "status": "ok",
  "service": "tenant-api-service"
}
3. Stop the services
docker compose down
This stops and removes the containers. Database data persistence depends on the volumes configured in docker-compose.yml.
API Endpoints
Method	Endpoint	Description
GET	/health	Check application health
POST	/tenants	Create a tenant and issue an API key
GET	/tenants/me	Retrieve information for the authenticated tenant
GET	/usage/me	Retrieve usage information for the authenticated tenant


For request schemas, response models, and interactive API testing, open Swagger UI at /docs.
Authentication
Protected endpoints use the X-API-Key request header. Use the API key issued when creating a tenant:
X-API-Key: tsk_your_issued_api_key
Replace the example value with your actual key. Never publish real API keys in source code, screenshots, logs, or public repositories.
Running Tests
Run tests from the project directory with the project virtual environment activated:
python -m pytest -q
Integration tests require a dedicated test database configured through TEST_DATABASE_URL. For example, configure it locally to point to your test database before running the suite. Do not point integration tests at your development or production database. Keep database credentials in environment variables or a local .env file, and never commit them.

The project previously passed 40 tests in the development environment. Results can vary if the code or environment changes.
Security Notes
- Store only hashed API keys in the database; treat the original issued key as a secret.
- Keep .env files and credentials out of version control.
- Use a dedicated database for integration tests.
- Apply appropriate secret management, TLS, monitoring, and database access controls before deploying to production.
- Configure rate limits and quotas according to the requirements of each tenant.
Potential Future Improvements
- Database migrations with Alembic
- Continuous integration with GitHub Actions
- Dedicated background workers for asynchronous jobs
- Structured metrics, tracing, and production monitoring
- More granular API-key rotation and revocation workflows
License
No license has been specified yet. Add a license before distributing or reusing the project publicly.