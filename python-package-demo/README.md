# python-package-demo

> **Repository URL:** [https://github.com/parth-mehta95/python-package-demo](https://github.com/parth-mehta95/python-package-demo)

A production-ready, reusable Python package foundation with deterministic locked dependencies, ensuring reliable and repeatable deployments across staging, CI/CD, and production environments.

---

## 1. Scenario & Objectives

Modern engineering teams often face deployment discrepancies caused by "dependency drift"—where non-deterministic resolution of transitive dependencies breaks production systems while local builds succeed.

This repository provides:
- A standardized **Python package scaffold** (`src/` layout with `pyproject.toml`).
- **Pinned direct dependencies** in `requirements.txt`.
- **Cryptographically locked dependency files** (`requirements.lock` via `pip-compile` and `poetry.lock` via Poetry).
- Guaranteed parity between `requirements.txt` and the generated lock files.

---

## 2. Dependency Pinning Strategy

### The Two-Tier Dependency Philosophy

To guarantee build reproducibility without sacrificing long-term maintainability, we adopt a two-tier dependency management architecture:

1. **Abstract / Top-Level Declaration (`requirements.in` / `pyproject.toml`)**:
   - Declares direct package requirements and allowed compatibility ranges or primary pins.
   - Kept minimal and readable.

2. **Concrete Resolved Lockfile (`requirements.lock` / `poetry.lock`)**:
   - Resolves the complete dependency graph, capturing every direct and transitive sub-dependency.
   - Pins exact versions (`==`) and records SHA-256 integrity hashes for each package distribution artifact.
   - Committed to version control and used in all automated deployment pipelines.

### Why Exact Pinning Matters

- **Elimination of Dependency Drift:** Guarantees every developer, container, and CI runner installs byte-for-byte identical dependencies regardless of when or where the build executes.
- **Supply-Chain & Integrity Security:** Including SHA-256 hashes prevents upstream artifact modification or compromised mirror attacks.
- **Controlled Upgrades:** Dependencies are never upgraded implicitly during deployments; updates require deliberate re-compilation of the lockfile.

---

## 3. Version Parity Verification

The success criterion requires that **the lock file matches all pinned versions in `requirements.txt`**.

The table below demonstrates the exact match across all dependencies:

| Package | Pinned Version (`requirements.txt`) | Version in `requirements.lock` (`pip-compile`) | Version in `poetry.lock` | Direct / Transitive |
| :--- | :--- | :--- | :--- | :--- |
| **certifi** | `2024.2.2` | `2024.2.2` | `2024.2.2` | Transitive (`requests`) |
| **charset-normalizer** | `3.3.2` | `3.3.2` | `3.3.2` | Transitive (`requests`) |
| **idna** | `3.7` | `3.7` | `3.7` | Transitive (`requests`) |
| **requests** | `2.31.0` | `2.31.0` | `2.31.0` | Direct |
| **urllib3** | `2.2.1` | `2.2.1` | `2.2.1` | Transitive (`requests`) |

*All 5 pinned packages in `requirements.txt` match identically in both `requirements.lock` and `poetry.lock`.*

---

## 4. Repository Structure

```text
python-package-demo/
├── .gitignore                      # Python build, test, and virtualenv artifacts
├── README.md                       # Architecture & dependency pinning documentation
├── pyproject.toml                  # Modern Python build metadata & tool config
├── requirements.in                 # Source direct requirements for pip-tools
├── requirements.txt                # Pinned dependencies specification
├── requirements.lock               # Deterministic lock file with SHA-256 hashes (pip-compile)
├── poetry.lock                     # Deterministic lock file for Poetry users
├── src/
│   └── python_package_demo/
│       ├── __init__.py             # Package exports & version
│       └── core.py                 # Resilient HTTP client & health checking module
└── tests/
    ├── __init__.py
    └── test_core.py                # Unit tests with mocked network calls
```

---

## 5. Lock File Generation & Management Workflow

### Option A: Using `pip-tools` (`pip-compile`)

To generate or refresh the lock file from pinned requirements:

```bash
# 1. Install pip-tools in your virtual environment
pip install pip-tools

# 2. Compile the locked dependency tree with cryptographic hashes
pip-compile --generate-hashes --output-file=requirements.lock requirements.txt

# 3. Synchronize your virtual environment to strictly match the lockfile
pip-sync requirements.lock
```

### Option B: Using Poetry

If your team utilizes Poetry for dependency management:

```bash
# 1. Resolve and lock dependencies according to pyproject.toml
poetry lock --no-update

# 2. Install exactly what is specified in poetry.lock
poetry install --no-root
```

---

## 6. Installation & Deployment Instructions

### Production Deployment (Recommended)
Always deploy using the lock file with hash verification:

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Deterministic install with hash verification
pip install --require-hashes -r requirements.lock

# Install the package itself in editable or standard mode
pip install --no-deps -e .
```

### Alternative Installation via `requirements.txt`
```bash
pip install -r requirements.txt
pip install -e .
```

---

## 7. Running Tests

Unit tests are included to verify functionality:

```bash
pytest tests/
```

---

## 8. Summary of Deliverables

- **Repository Name:** `python-package-demo`
- **Public URL:** `https://github.com/parth-mehta95/python-package-demo`
- **Requirements File:** [`requirements.txt`](./requirements.txt)
- **Lock Files:** [`requirements.lock`](./requirements.lock) & [`poetry.lock`](./poetry.lock)
- **Package Scaffold:** [`src/python_package_demo/`](./src/python_package_demo/)
