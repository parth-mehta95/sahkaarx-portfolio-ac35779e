# Secure Data Pipeline (`secure-data-pipeline`)

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://pypi.org/project/secure-data-pipeline/)
[![Security Audit](https://img.shields.io/badge/security%20audit-passed-brightgreen.svg)](security_scan_report.md)
[![Python Support](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**`secure-data-pipeline`** is an enterprise-grade Python framework for orchestrating data processing pipelines. It features a complete **Dependency Injection (DI)** container, robust **REST API endpoint validation**, and strict **cryptographic supply chain security controls**.

---

## 1. Installation Guide

### Option A: Install from PyPI (Public Registry)

```bash
# Standard installation
pip install secure-data-pipeline

# With developer / testing dependencies
pip install "secure-data-pipeline[dev]"

# With security scanning tools
pip install "secure-data-pipeline[security]"
```

### Option B: Install from Private Registry (Internal Artifactory / Nexus / AWS CodeArtifact)

Configure pip to fetch packages from your organization's private repository:

```bash
# Using pip CLI flag
pip install secure-data-pipeline \
  --index-url https://svc-ci-publisher:${INTERNAL_REGISTRY_TOKEN}@packages.internal.corp.network/repository/pypi-releases/simple/

# Or using environment variable / pip.conf
export PIP_EXTRA_INDEX_URL="https://packages.internal.corp.network/repository/pypi-releases/simple/"
pip install secure-data-pipeline
```

### Option C: Install from Local Built Wheel / Distribution

```bash
pip install ./dist/secure_data_pipeline-1.0.0-py3-none-any.whl
```

### Verify Installation

Run the built-in installation verification command:

```bash
datapipeline-verify
# or
python verify_install.py
```

---

## 2. Registry Credentials & Publication Setup

To publish new releases to PyPI or a private repository:

### 1. PyPI Credentials Setup
Create or update `~/.pypirc` (see [`.pypirc.example`](.pypirc.example)):

```ini
[distutils]
index-servers =
    pypi
    testpypi
    private-registry

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-AgEIcHlwaS5vcmcCJ... # Production token

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgENdGVzdC5weXBpLm9yZw... # Staging token

[private-registry]
repository = https://packages.internal.corp.network/repository/pypi-releases/
username = deployer
password = ${INTERNAL_REGISTRY_PASSWORD}
```

### 2. CI/CD GitHub Secrets Configuration
Configure the following secrets in your GitHub repository (`Settings -> Secrets and variables -> Actions`):
- `PYPI_API_TOKEN`: PyPI upload token with package scope.
- `TEST_PYPI_API_TOKEN`: TestPyPI upload token for staging.
- `PRIVATE_REGISTRY_URL`: URL of the internal repository.
- `PRIVATE_REGISTRY_USERNAME`: Service account username.
- `PRIVATE_REGISTRY_PASSWORD`: Service account password or access token.

### 3. Automated Release Command
```bash
# Build and release to PyPI
python publish.py --target pypi

# Staging dry-run
python publish.py --target testpypi --dry-run
```

---

## 3. Dependency Injection (DI) Architecture

The framework provides an Inversion of Control (IoC) container supporting:
- **Singleton, Transient, and Scoped** lifetimes
- **Interface / Abstract Base Class resolution**
- **Child container isolation** for unit testing and mocking
- **`@inject` decorator** for transparent function parameter injection
- **Circular dependency prevention**

### Core DI Interfaces & Concrete Implementations

```
┌────────────────────────────────────────────────────────┐
│                   IoC Container                        │
└────────────────────────────────────────────────────────┘
          ▲                    ▲                   ▲
          │                    │                   │
┌─────────────────┐  ┌──────────────────┐  ┌───────────────┐
│ IStorageService │  │   IAuthService   │  │ IDataTransform│
└─────────────────┘  └──────────────────┘  └───────────────┘
          ▲                    ▲                   ▲
          │                    │                   │
  InMemoryStorage        HmacAuthService     StandardTransform
```

### Code Example: Container Configuration & Service Resolution

```python
from datapipeline import Container, Scope, inject
from datapipeline.di.interfaces import IStorageService, IAuthService
from datapipeline.di.providers import InMemoryStorageService, HmacAuthService
from datapipeline.services import PipelineService

# 1. Initialize container
container = Container()

# 2. Register abstractions and implementations
container.register_singleton(IStorageService, InMemoryStorageService)
container.register_singleton(IAuthService, HmacAuthService)

# 3. Auto-wire service with resolved dependencies
container.register_singleton(PipelineService)

# 4. Resolve instance
pipeline_service = container.resolve(PipelineService)
```

### Code Example: Function Injection with `@inject`

```python
from datapipeline import inject, set_default_container
from datapipeline.di.interfaces import IStorageService

@inject()
def persist_customer_event(event_id: str, storage: IStorageService):
    return storage.save("events", event_id, {"event": "login"})

# The storage parameter is automatically injected by the container
persist_customer_event(event_id="evt_101")
```

### Code Example: Test Mocking with Child Containers

```python
# Create child container inheriting registrations
test_container = app_container.create_child_container()

# Override storage with a mock for test isolation
test_container.register_singleton(IStorageService, MockStorageService)

# Resolve service with mocked dependency
test_service = test_container.resolve(PipelineService)
```

---

## 4. REST API Endpoint Reference & Examples

### Overview of API Endpoints

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/health` | Service health status and container diagnostics | No |
| `POST` | `/api/v1/auth/token` | Authenticate client and generate Bearer access token | No |
| `GET` | `/api/v1/pipelines` | List all registered pipelines | Yes (Bearer) |
| `POST` | `/api/v1/pipelines` | Register a new pipeline definition | Yes (Bearer) |
| `GET` | `/api/v1/pipelines/{id}` | Fetch pipeline configuration by ID | Yes (Bearer) |
| `POST` | `/api/v1/pipelines/{id}/run` | Execute pipeline transforms on dataset | Yes (Bearer) |
| `GET` | `/api/v1/datasets` | List stored dataset collections | Yes (Bearer) |
| `POST` | `/api/v1/datasets/validate` | Validate schema and record integrity | Yes (Bearer) |
| `GET` | `/api/v1/metrics` | Retrieve application metrics and counters | No |

---

## 5. API Usage Examples

### Using Python SDK Client (`PipelineClient`)

```python
from datapipeline import PipelineClient

client = PipelineClient()

# 1. Health check
print(client.health())

# 2. Authenticate
token = client.authenticate(
    client_id="admin-client",
    client_secret="secret-admin-token-key-prod-99"
)

# 3. Register a pipeline
config = {
    "pipeline_id": "daily-sanitize",
    "name": "Daily Sanitization ETL",
    "transform_operations": ["strip_whitespace", "lowercase_keys", "hash_pii"],
    "max_retries": 3,
    "timeout_seconds": 600,
}
client.create_pipeline(config)

# 4. Execute pipeline
records = [
    {"Name": " Alice ", "Email": "alice@corp.com"},
    {"Name": " Bob ", "Email": "bob@corp.com"},
]
results = client.run_pipeline("daily-sanitize", records)
print("Pipeline Output:", results["output"])
```

### Direct HTTP Request Examples (cURL)

#### 1. Obtain Bearer Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "admin-client",
    "client_secret": "secret-admin-token-key-prod-99"
  }'
```

#### 2. Create Pipeline
```bash
curl -X POST http://localhost:8000/api/v1/pipelines \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "pipeline_id": "analytics-cleaner",
    "name": "Analytics Data Cleaner",
    "transform_operations": ["strip_whitespace", "lowercase_keys", "hash_pii"]
  }'
```

#### 3. Execute Pipeline
```bash
curl -X POST http://localhost:8000/api/v1/pipelines/analytics-cleaner/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "records": [
      {"User": " Jane Doe ", "Email": "jane@example.com"}
    ]
  }'
```

---

## 6. Testing & Security Audits

### Running Full Test Suite
```bash
python run_tests.py
# or with pytest
pytest tests/ -v
```

### Running Security Scans
```bash
python run_security_scan.py
# or using pip-audit directly
pip-audit --requirement requirements.lock --strict
# or using bandit
bandit -r src/ -c .bandit.yml
```

---

## 7. License & Compliance
Licensed under the [MIT License](LICENSE). Complies with supply chain security standards.
