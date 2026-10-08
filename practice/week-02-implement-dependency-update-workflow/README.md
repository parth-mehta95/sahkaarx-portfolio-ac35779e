# Dependency Update Workflow & Version Pinning Strategy

## Overview

This repository implements an automated, safe dependency update workflow to keep project dependencies current without breaking production systems. It establishes clear upgrade procedures, version constraint validation, and cross-package compatibility checks.

---

## Deliverables & Success Criteria

| Deliverable | Implementation Artifact | Status |
| :--- | :--- | :--- |
| **Automated Update Script** | [`update_dependencies.py`](file:///d:/challengers%20testing/sahkaarx-portfolio-ac35779e/practice/week-02-implement-dependency-update-workflow/update_dependencies.py) | Completed |
| **Compatibility Validation** | Cross-dependency validation engine in `update_dependencies.py` | Completed |
| **Version Pinning Logic** | SemVer bounds (`>=X.Y.Z, <(X+1).0.0`) & exact lockfile pinning | Completed |
| **Upgrade Documentation** | This `README.md` guide | Completed |
| **Automated Test Suite** | [`test_update_dependencies.py`](file:///d:/challengers%20testing/sahkaarx-portfolio-ac35779e/practice/week-02-implement-dependency-update-workflow/test_update_dependencies.py) | Completed |

---

## 1. Key Features of `update_dependencies.py`

1. **Outdated Package Detection**: Queries package indexes (PyPI) to identify available releases and compares them against installed/declared versions.
2. **Constraint Enforcement**: Strictly adheres to version constraints (such as `<3.0.0`), preventing breaking major updates from entering production.
3. **Compatibility Validation**: Cross-checks declared dependencies and sub-dependencies to detect version conflicts before applying upgrades.
4. **Dual Pinning Strategy**:
   - **`requirements.in`**: Declares loose bounds with upper limits (`>=2.31.0, <3.0.0`) for flexibility and safety.
   - **`requirements.lock`**: Generates deterministic exact pins (`==2.32.0`) for reproducible deployments.
5. **Dry-Run & JSON Support**: Allows safe simulation and structured JSON output for CI/CD pipelines.

---

## 2. Version Pinning Strategy

Our team utilizes a **two-tier version management strategy**:

```
+-------------------------------------------------------------+
|                      requirements.in                        |
|  - Abstract dependencies with upper & lower bounds          |
|  - Example: requests>=2.31.0,<3.0.0                         |
|  - Purpose: Defines allowable API surface & SemVer bounds    |
+-------------------------------------------------------------+
                              |
                     [update_dependencies.py]
                   (Validates compatibility)
                              |
                              v
+-------------------------------------------------------------+
|                     requirements.lock                       |
|  - Concrete, exact versions for deterministic builds         |
|  - Example: requests==2.32.0                                |
|  - Purpose: 100% reproducible test, CI, & production builds  |
+-------------------------------------------------------------+
```

### Semantic Versioning (SemVer) Update Rules

| Version Component | Format | Risk Level | Update Policy | Constraint Rule |
| :--- | :--- | :--- | :--- | :--- |
| **Patch** | `x.y.Z` (Bug fixes) | Low | Automated weekly updates | Automatically allowed |
| **Minor** | `x.Y.z` (Features, backwards compatible) | Medium | Bi-weekly / Sprint updates after automated tests | Allowed within `<(X+1).0.0` |
| **Major** | `X.y.z` (Breaking API changes) | High | Manual review, code refactoring, & migration plan | **Blocked by default** (`<NextMajor.0.0`) |

---

## 3. Step-by-Step Upgrade Guide

Follow this standard operating procedure when updating project dependencies:

### Step 1: Audit and Check for Outdated Packages
Run the script in check mode to detect which dependencies have newer releases available:
```bash
python update_dependencies.py --check --file requirements.in
```
The script will display a status table:
```
+--------------------+------------+------------+-------------+-------------+-----------------------+
| Package            | Current    | Compatible | Latest PyPI | Update Type | Constraint Status     |
+--------------------+------------+------------+-------------+-------------+-----------------------+
| requests           | 2.31.0     | 2.32.3     | 3.0.0       | MINOR       | PROTECTED (< breaking)|
| urllib3            | 2.2.1      | 2.2.2      | 3.0.0       | PATCH       | PROTECTED (< breaking)|
| certifi            | 2024.2.2   | 2024.7.4   | 2024.7.4    | MINOR       | SAFE                  |
+--------------------+------------+------------+-------------+-------------+-----------------------+
```

### Step 2: Validate Cross-Dependency Compatibility
Ensure planned package upgrades do not create mutual dependency conflicts:
```bash
python update_dependencies.py --validate --file requirements.in
```

### Step 3: Dry-Run Upgrade Simulation
Preview changes without modifying any files on disk:
```bash
python update_dependencies.py --update --dry-run --file requirements.in --lock-file requirements.lock
```

### Step 4: Apply Safe Upgrades
Apply updates matching your preferred strategy (`patch`, `minor`, or `compatible`):
```bash
# Apply only patch updates (lowest risk)
python update_dependencies.py --update --strategy patch --file requirements.in --lock-file requirements.lock

# Apply compatible minor and patch updates
python update_dependencies.py --update --strategy compatible --file requirements.in --lock-file requirements.lock
```

### Step 5: Run Automated Tests
Run your test suite to verify system integrity:
```bash
pytest
# or
python -m unittest discover tests
```

### Step 6: Commit and Push Changes
Commit both `requirements.in` and `requirements.lock` to ensure all team members and CI/CD runners use the updated lockfile:
```bash
git add requirements.in requirements.lock
git commit -m "chore(deps): update dependencies respecting SemVer constraints"
git push origin main
```

---

## 4. CLI Command Reference

| Flag | Short | Description |
| :--- | :--- | :--- |
| `--check` | `-c` | Scan dependencies and display update status table |
| `--update` | `-u` | Apply updates to requirements and lockfile |
| `--validate`| `-v` | Validate mutual dependency compatibility |
| `--dry-run` | `-d` | Simulate proposed updates without writing to disk |
| `--strategy`| `-s` | Strategy: `patch`, `minor`, `compatible` (default: `compatible`) |
| `--file` | `-f` | Path to input specification (default: `requirements.in`) |
| `--lock-file`| `-l` | Path to lockfile output (default: `requirements.lock`) |
| `--json` | | Output report in structured JSON format |

---

## 5. Verification & Testing

Unit tests for the update script and constraint logic are located in [`test_update_dependencies.py`](file:///d:/challengers%20testing/sahkaarx-portfolio-ac35779e/practice/week-02-implement-dependency-update-workflow/test_update_dependencies.py).

Run the tests using Python's standard `unittest` module:
```bash
python test_update_dependencies.py
```

All test cases verify:
- Semantic version parsing and ordering.
- Rejection of breaking major version upgrades.
- Enforcement of `<3.0.0` upper bounds.
- Detection of inter-dependency version conflicts.
- Preservation of comments and deterministic lockfile generation.

---

## 6. Rollback Procedure

If a dependency update introduces an unexpected regression in staging or production:
1. Revert to the previous pinned lockfile:
   ```bash
   git checkout HEAD~1 -- requirements.lock
   pip install -r requirements.lock
   ```
2. Pin the problematic package to the last known good version in `requirements.in`:
   ```text
   broken-package==1.2.3  # Pinned due to issue #123
   ```
3. Re-run validation and redeploy.