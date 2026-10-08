# API Endpoint Specification & Validation Documentation

**Package:** `secure-data-pipeline`  
**API Version:** `v1`  
**Base URL:** `/api/v1`  
**Protocol:** REST / JSON  
**Authentication Scheme:** Bearer Token (HMAC-SHA256)  

---

## 1. Authentication & Security Headers

All authenticated endpoints require the standard `Authorization` header:

```http
Authorization: Bearer <TOKEN>
Content-Type: application/json
```

---

## 2. Standard Response Envelope

All API endpoints return responses using the unified `APIResponse` model:

```json
{
  "success": true,
  "data": { ... },
  "errors": null,
  "status_code": 200,
  "timestamp": 1728399345.123
}
```

On validation or authorization failure:

```json
{
  "success": false,
  "data": null,
  "errors": [
    "Field 'pipeline_id' must be non-empty and alphanumeric"
  ],
  "status_code": 400,
  "timestamp": 1728399345.123
}
```

---

## 3. Endpoint Reference

### 3.1 Health Check

- **Method:** `GET`
- **Path:** `/api/v1/health`
- **Auth:** None
- **Description:** Verifies service uptime and Dependency Injection container readiness.

#### Response (200 OK)
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "uptime_seconds": 12.34,
    "container_services": [
      "IStorageService",
      "IAuthService",
      "IMetricsCollector",
      "IDataTransformer",
      "INotificationService"
    ]
  },
  "status_code": 200
}
```

---

### 3.2 Authentication Token

- **Method:** `POST`
- **Path:** `/api/v1/auth/token`
- **Auth:** None
- **Description:** Exchanges client credentials for a signed Bearer token.

#### Request Body
```json
{
  "client_id": "admin-client",
  "client_secret": "secret-admin-token-key-prod-99"
}
```

#### Validation Rules
- `client_id`: Required, non-empty string.
- `client_secret`: Required, non-empty string.

#### Response (200 OK)
```json
{
  "success": true,
  "data": {
    "access_token": "dpt_admin-client:admin:1728390000:7a9f...:signature",
    "token_type": "Bearer",
    "expires_in": 86400
  },
  "status_code": 200
}
```

#### Errors
- `400 Bad Request`: Missing `client_id` or `client_secret`.
- `401 Unauthorized`: Invalid client credentials.

---

### 3.3 List Pipelines

- **Method:** `GET`
- **Path:** `/api/v1/pipelines`
- **Auth:** Bearer Token
- **Description:** Returns all registered pipelines.

#### Response (200 OK)
```json
{
  "success": true,
  "data": [
    {
      "pipeline_id": "sales-etl",
      "name": "Sales ETL",
      "description": "Daily sales ingest",
      "transform_operations": ["strip_whitespace", "lowercase_keys", "hash_pii"],
      "enabled": true,
      "max_retries": 3,
      "timeout_seconds": 300
    }
  ],
  "status_code": 200
}
```

---

### 3.4 Create Pipeline

- **Method:** `POST`
- **Path:** `/api/v1/pipelines`
- **Auth:** Bearer Token
- **Description:** Registers a new pipeline definition.

#### Request Body
```json
{
  "pipeline_id": "customer-data-sync",
  "name": "Customer Data Sync Pipeline",
  "description": "Daily sync and sanitization of customer entries",
  "transform_operations": ["strip_whitespace", "hash_pii"],
  "enabled": true,
  "max_retries": 3,
  "timeout_seconds": 600
}
```

#### Validation Rules
- `pipeline_id`: Alphanumeric, hyphen, and underscore only. Cannot be empty.
- `name`: String, minimum 3 characters.
- `transform_operations`: List of valid operations: `strip_whitespace`, `lowercase_keys`, `hash_pii`, `add_timestamp`.
- `max_retries`: Integer between 0 and 10.
- `timeout_seconds`: Integer between 1 and 3600.

#### Response (201 Created)
```json
{
  "success": true,
  "data": {
    "pipeline_id": "customer-data-sync",
    "name": "Customer Data Sync Pipeline",
    "transform_operations": ["strip_whitespace", "hash_pii"],
    "enabled": true,
    "max_retries": 3,
    "timeout_seconds": 600
  },
  "status_code": 201
}
```

---

### 3.5 Get Pipeline by ID

- **Method:** `GET`
- **Path:** `/api/v1/pipelines/{id}`
- **Auth:** Bearer Token

#### Response (200 OK)
Returns pipeline configuration object.

#### Errors
- `404 Not Found`: If pipeline with specified ID does not exist.

---

### 3.6 Run Pipeline

- **Method:** `POST`
- **Path:** `/api/v1/pipelines/{id}/run`
- **Auth:** Bearer Token
- **Description:** Executes transformation operations on the supplied dataset records.

#### Request Body
```json
{
  "records": [
    {
      "name": "  Bob Builder  ",
      "email": "bob@example.com",
      "DEPARTMENT": "Operations"
    }
  ]
}
```

#### Response (200 OK)
```json
{
  "success": true,
  "data": {
    "pipeline_id": "customer-data-sync",
    "status": "success",
    "records_in": 1,
    "records_out": 1,
    "duration_seconds": 0.0012,
    "output": [
      {
        "name": "Bob Builder",
        "email_hash": "a4d8b5...",
        "DEPARTMENT": "Operations"
      }
    ],
    "timestamp": 1728399345.567
  },
  "status_code": 200
}
```

---

### 3.7 Validate Dataset

- **Method:** `POST`
- **Path:** `/api/v1/datasets/validate`
- **Auth:** Bearer Token

#### Request Body
```json
{
  "dataset_id": "batch-2026-10-08",
  "schema_version": "1.0",
  "records": [
    {"user_id": 101, "score": 98.5}
  ]
}
```

#### Response (200 OK)
```json
{
  "success": true,
  "data": {
    "dataset_id": "batch-2026-10-08",
    "record_count": 1,
    "status": "validated"
  },
  "status_code": 200
}
```

#### Errors
- `422 Unprocessable Entity`: If `dataset_id` is invalid or `records` list is empty or contains non-dict items.

---

### 3.8 Metrics Snapshot

- **Method:** `GET`
- **Path:** `/api/v1/metrics`
- **Auth:** None

#### Response (200 OK)
```json
{
  "success": true,
  "data": {
    "counters": {
      "health_checks_total": 4,
      "pipeline_runs_total{pipeline_id=sales-etl}": 2,
      "pipeline_success_total": 2
    },
    "gauges": {
      "last_pipeline_duration_seconds": 0.0024
    },
    "timestamp": 1728399345.789
  },
  "status_code": 200
}
```
