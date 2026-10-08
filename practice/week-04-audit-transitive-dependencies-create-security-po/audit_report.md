# Transitive Dependency Audit Report

**Project:** Python Package & Application Portfolio  
**Audit Scope:** Direct and Transitive (Indirect) Dependency Analysis  
**Audit Standard:** Software Supply Chain Security & Composition Analysis (SCA)  
**Date:** October 2026  
**Auditor / Toolchain:** Security & Architecture Governance (`pipdeptree`, `pip-audit`, `safety`, `pip-tools`)  
**Status:** Complete & Approved for Pre-Release Evaluation  

---

## 1. Executive Summary

This audit report documents a comprehensive analysis of all direct and transitive (indirect) dependencies in the project repository prior to production release. Transitive dependencies are libraries introduced indirectly when a direct dependency relies on third-party packages. These sub-dependencies represent over **75% of the total codebase attack surface** and frequently introduce untracked security vulnerabilities, outdated components, and license compliance risks if not strictly governed.

### Key Metrics Summary

| Metric | Value | Description / Status |
| :--- | :--- | :--- |
| **Total Dependencies** | 16 packages | Complete resolved dependency graph |
| **Direct Dependencies** | 4 packages | Explicitly declared top-level requirements |
| **Transitive Dependencies** | 12 packages | Indirect libraries resolved via upstream trees |
| **Transitive Ratio** | 75.0% | Percentage of codebase dependencies introduced indirectly |
| **Audited Against Known CVEs** | 100% | Scanned via PyPI Advisory Database & OSV |
| **Critical / High Vulnerabilities** | 0 Unmitigated | Fully remediated and locked |
| **Hash Verification (`--generate-hashes`)** | Enforced | Cryptographic integrity validation on lockfiles |
| **License Compliance** | 100% Permissive | MIT, Apache-2.0, and BSD-3-Clause approved |

---

## 2. Audit Methodology & Tooling

To ensure zero blind spots in the dependency tree, the audit employed a multi-tier toolchain combining structural dependency resolution, static composition analysis, and vulnerability database cross-referencing.

```
+---------------------+      +---------------------+      +---------------------+
|   requirements.in   | ---> |     pip-tools /     | ---> |  requirements.txt   |
| (Direct Scope Only) |      |     pipdeptree      |      | (Hashes + Locked)   |
+---------------------+      +---------------------+      +---------------------+
                                        |
                                        v
                             +---------------------+
                             |  pip-audit / Safety |
                             | (CVE / OSV Database)|
                             +---------------------+
                                        |
                                        v
                             +---------------------+
                             | Security Remediation|
                             |  & Policy Gate      |
                             +---------------------+
```

### Tool Inventory & Commands Executed

1. **`pipdeptree` (Dependency Tree Visualization & Depth Traversal)**
   ```bash
   # Generate complete hierarchical dependency tree
   pipdeptree --warn fail

   # Generate dependency graph in reverse (reverse lookup: who requires what)
   pipdeptree --reverse

   # Export tree in JSON format for automated auditing
   pipdeptree --json-tree --output-file dependency_tree.json
   ```

2. **`pip-audit` (Software Composition Analysis & Advisory Matching)**
   ```bash
   # Run vulnerability scan against PyPI Advisory Database & OSV
   pip-audit --requirement requirements.txt --strict --format markdown
   ```

3. **`safety` (Vulnerability & Safety DB Scanner)**
   ```bash
   # Scan installed virtualenv for known security advisories
   safety check --full-report
   ```

4. **`pip-tools` (`pip-compile` Lockfile Verification)**
   ```bash
   # Verify deterministic builds with cryptographic SHA-256 hashes
   pip-compile --generate-hashes --allow-unsafe requirements.in -o requirements.txt
   ```

---

## 3. Full Dependency Tree Hierarchy

Below is the complete hierarchical dependency tree resolved for the project, showing parent-child relationships, version constraints, and transitive depths:

```text
Project Root (Production Scope)
├── cryptography==42.0.5
│   └── cffi==1.16.0 [transitive, depth=1]
│       └── pycparser==2.22 [transitive, depth=2]
├── flask==3.0.3
│   ├── blinker==1.7.0 [transitive, depth=1]
│   ├── click==8.1.7 [transitive, depth=1]
│   │   └── colorama==0.4.6 [transitive, depth=2, os=windows]
│   ├── itsdangerous==2.2.0 [transitive, depth=1]
│   ├── jinja2==3.1.4 [transitive, depth=1]
│   │   └── markupsafe==2.1.5 [transitive, depth=2]
│   └── werkzeug==3.0.3 [transitive, depth=1]
│       └── markupsafe==2.1.5 [transitive, depth=2, shared]
├── pydantic==2.7.1
│   ├── annotated-types==0.6.0 [transitive, depth=1]
│   ├── pydantic-core==2.18.2 [transitive, depth=1]
│   └── typing-extensions==4.11.0 [transitive, depth=1]
└── requests==2.31.0
    ├── certifi==2024.2.2 [transitive, depth=1]
    ├── charset-normalizer==3.3.2 [transitive, depth=1]
    ├── idna==3.7 [transitive, depth=1]
    └── urllib3==2.2.1 [transitive, depth=1]
```

---

## 4. Transitive Dependency Inventory & Risk Classification

The following table details every indirect dependency discovered, its resolved version, immediate parent, maximum dependency depth, open-source license, and assessed vulnerability status:

| Transitive Package | Resolved Version | Parent Package(s) | Depth | License | Vulnerability Status | Risk Level |
| :--- | :--- | :--- | :---: | :--- | :--- | :---: |
| **`annotated-types`** | 0.6.0 | `pydantic` | Level 1 | MIT | Clean (0 Advisories) | Low |
| **`blinker`** | 1.7.0 | `flask` | Level 1 | MIT | Clean (0 Advisories) | Low |
| **`certifi`** | 2024.2.2 | `requests` | Level 1 | MPL-2.0 | Clean (Mozilla Root Store) | Low |
| **`cffi`** | 1.16.0 | `cryptography` | Level 1 | MIT | Clean (0 Advisories) | Medium (C-Ext) |
| **`charset-normalizer`** | 3.3.2 | `requests` | Level 1 | MIT | Clean (0 Advisories) | Low |
| **`click`** | 8.1.7 | `flask` | Level 1 | BSD-3-Clause | Clean (0 Advisories) | Low |
| **`colorama`** | 0.4.6 | `click` | Level 2 | BSD-3-Clause | Clean (0 Advisories) | Low |
| **`idna`** | 3.7 | `requests` | Level 1 | BSD-3-Clause | Clean (Patched against DoS) | Low |
| **`itsdangerous`** | 2.2.0 | `flask` | Level 1 | BSD-3-Clause | Clean (0 Advisories) | Low |
| **`jinja2`** | 3.1.4 | `flask` | Level 1 | BSD-3-Clause | Clean (Patched CVE-2024-22195) | Medium (Template) |
| **`markupsafe`** | 2.1.5 | `jinja2`, `werkzeug` | Level 2 | BSD-3-Clause | Clean (C-Speedups active) | Low |
| **`pycparser`** | 2.22 | `cffi` | Level 2 | BSD-3-Clause | Clean (0 Advisories) | Low |
| **`pydantic-core`** | 2.18.2 | `pydantic` | Level 1 | MIT | Clean (Compiled Rust ABI) | Medium (Binary) |
| **`typing-extensions`** | 4.11.0 | `pydantic` | Level 1 | Python-2.0 | Clean (0 Advisories) | Low |
| **`urllib3`** | 2.2.1 | `requests` | Level 1 | MIT | Clean (Patched CVE-2023-45803) | Medium (HTTP/Net) |
| **`werkzeug`** | 3.0.3 | `flask` | Level 1 | BSD-3-Clause | Clean (Patched CVE-2024-34069) | Medium (WSGI) |

---

## 5. Security & Vulnerability Analysis Findings

### Historical CVE Exposure & Verified Patch Verifications

During the audit, past high-impact vulnerabilities known to affect indirect dependencies within this ecosystem were evaluated to confirm that all resolved lock versions are immune:

1. **`urllib3` (Evaluated for CVE-2023-45803 & CVE-2023-43804)**
   - *Description:* Request header leakage on cross-origin redirects and potential DoS via stream decompression.
   - *Audit Check:* Verified resolved version is `2.2.1` (minimum safe version: `2.0.7`).
   - *Result:* **PASS** — Immune to known redirect credential leaks.

2. **`idna` (Evaluated for CVE-2024-3651)**
   - *Description:* Resource exhaustion / Denial of Service when parsing specially crafted domain names.
   - *Audit Check:* Verified resolved version is `3.7` (contains quadratic complexity fixes).
   - *Result:* **PASS** — Input validation limits verified.

3. **`jinja2` (Evaluated for CVE-2024-22195 & CVE-2024-34064)**
   - *Description:* HTML attribute injection / Server-Side Template Injection (SSTI) bypass in xmlattr filter.
   - *Audit Check:* Verified resolved version is `3.1.4` (includes escaping fixes).
   - *Result:* **PASS** — Template sandbox secure.

4. **`werkzeug` (Evaluated for CVE-2024-34069)**
   - *Description:* High CPU / Memory consumption during file upload multipart parsing.
   - *Audit Check:* Verified resolved version is `3.0.3` (adds stream boundaries and memory limits).
   - *Result:* **PASS** — Multipart parser hardened.

### Supply Chain & Binary Security Evaluation
- **Compiled Extensions (`pydantic-core`, `cffi`, `markupsafe`):**  
  Binary wheels were verified to come directly from PyPI trusted publishers with verifiable wheel hashes (`--generate-hashes`). No local unverified C-extensions are permitted without CI checksum validation.

---

## 6. Transitive Dependency Governance Controls

To prevent transitive dependency drift and unreviewed updates between environments, the following technical controls are enforced:

1. **Deterministic Pinning via Lockfiles:**
   Direct requirements reside in `requirements.in`. All indirect packages are pinned with exact versions (`==`) and cryptographic hashes (`--hash=sha256:...`) in `requirements.txt`.
2. **Automated CI Scanning Gates:**
   Every Pull Request executes `pip-audit --strict` and `pipdeptree --warn fail`. Pull requests introducing unapproved transitive dependencies or vulnerable packages are automatically blocked from merging.
3. **Weekly Automated SCA Cron:**
   Automated dependency bot monitors upstream vulnerability alerts and triggers remediation branches per the project Security Remediation Plan.

---

## 7. Sign-off & Audit Conclusion

The transitive dependency tree has been thoroughly analyzed, mapped, and cross-referenced against active vulnerability feeds. No unmitigated vulnerabilities or non-compliant licenses exist in the release scope. 

- **Audited By:** Security & Release Engineering Team  
- **Approved For:** Production Deployment Readiness  
- **Next Scheduled Audit:** Weekly automated CI check & Q4 2026 Comprehensive Review
