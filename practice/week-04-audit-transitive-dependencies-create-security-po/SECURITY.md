# Security Policy

**Scope:** Repository, Direct Dependencies, and Transitive Dependencies  
**Version:** 1.0.0  
**Effective Date:** October 2026  
**Document Owner:** Product Security & Engineering Team  

---

## 1. Overview & Security Objectives

This Security Policy defines the standards, protocols, and workflows governing vulnerability detection, responsible disclosure, and incident response across our code repositories and software supply chain.

We treat security as a first-class engineering priority. We recognize that vulnerabilities may originate not only in our first-party code, but also within direct and transitive third-party dependencies. This document establishes our commitment to safeguarding our users, infrastructure, and open-source ecosystem.

---

## 2. Supported Versions

Security updates, vulnerability patches, and dependency remediations are actively maintained for the following versions:

| Version Branch | Supported | Minimum Python | Security Support End Date | Notes |
| :--- | :---: | :---: | :---: | :--- |
| **`v2.x` (Main / Production)** | :white_check_mark: Yes | `>= 3.10` | Ongoing (Current Active) | Full security fixes and dependency updates |
| **`v1.x` (Maintenance)** | :white_check_mark: Yes | `>= 3.9` | December 31, 2026 | Critical security patches only |
| **`< v1.0` (Legacy)** | :x: No | `< 3.9` | EOL (Deprecated) | Unsupported; upgrade immediately |

---

## 3. Vulnerability Detection Mechanisms

Our software composition and application architecture are continuously monitored using automated security gates:

### 3.1 Software Composition Analysis (SCA)
- **Continuous Dependency Auditing:** Direct and transitive dependencies are scanned continuously against the PyPA Advisory Database, GitHub Advisory Database, and Open Source Vulnerabilities (OSV) database.
- **Tools Integrated in CI/CD:**
  - `pip-audit`: Fails build pipelines on any detected vulnerability in locked requirements.
  - `pipdeptree`: Validates that no unapproved circular or rogue transitive dependencies enter the dependency tree.
  - Dependabot / Renovate: Automated daily PRs for CVE security advisories and version bumps.

### 3.2 Static Application Security Testing (SAST)
- Codebases are scanned with automated SAST analyzers (`bandit`, `ruff`, `semgrep`) on every pull request to identify injection risks, insecure deserialization, weak cryptographic primitives, and credential leaks.

### 3.3 Secret & Credential Scanning
- Pre-commit hooks and GitHub secret scanning detect accidental commits of API keys, tokens, or private certificates before code is pushed to remote repositories.

---

## 4. Reporting a Vulnerability (Responsible Disclosure)

We encourage ethical security researchers and community members to responsibly report any identified vulnerability. **Please do not report security vulnerabilities via public GitHub issues, discussions, or pull requests.**

### 4.1 Reporting Channels
Please report security findings using one of the following secure channels:
1. **GitHub Private Security Advisory (Recommended):**
   - Navigate to the repository's **Security** tab.
   - Click **"Report a vulnerability"** to open a confidential advisory draft.
2. **Security Team Direct Email:**
   - Email: `security-team@sahkaarx.internal` (or `security@sahkaarx.org`)
   - Subject line: `[SECURITY VULNERABILITY] <Component/Dependency Name> - Brief Summary`
3. **Encrypted Communication (PGP):**
   - For sensitive disclosures, encrypt reports using our public PGP key:
     `F3D8 94A2 10BC 78E9 4452  1189 AB90 32C1 DE88 471B`

### 4.2 Information to Include in Your Report
To accelerate validation and triage, please provide:
- Type of vulnerability (e.g., Remote Code Execution, Supply Chain Injection, SQLi, DoS).
- Component / Dependency affected (including exact version and whether direct or transitive).
- Step-by-step instructions or minimal Proof of Concept (PoC) to reproduce the behavior.
- Estimated severity or CVSS v3.1 vector.
- Suggested fix, mitigation, or workaround (if identified).

### 4.3 Safe Harbor Commitment
Activities conducted under responsible disclosure that respect user privacy, avoid data destruction, and do not disrupt production systems are covered under our Safe Harbor policy. We will not pursue legal action against researchers acting in good faith.

---

## 5. Vulnerability Response & Incident Workflow

Our vulnerability response process follows an organized, 5-stage lifecycle governed by strict Service Level Agreements (SLAs):

```
+---------------------------------------------------------------------------------+
|                                 VULNERABILITY LIFECYCLE                         |
+---------------------------------------------------------------------------------+
|  Stage 1: Intake & Acknowledgment (< 24 Hours)                                  |
|  - Log incident, acknowledge reporter, initiate confidential tracking           |
+---------------------------------------+-----------------------------------------+
                                        |
                                        v
+---------------------------------------------------------------------------------+
|  Stage 2: Triage & CVSS Scoring (< 48 Hours)                                    |
|  - Replicate exploit, assess blast radius, assign CVSS v3.1 score and priority  |
+---------------------------------------+-----------------------------------------+
                                        |
                                        v
+---------------------------------------------------------------------------------+
|  Stage 3: Containment & Temporary Mitigation (< 72 Hours)                       |
|  - Apply WAF rule, feature flag bypass, or lockfile transitive pin              |
+---------------------------------------+-----------------------------------------+
                                        |
                                        v
+---------------------------------------------------------------------------------+
|  Stage 4: Patch Engineering & Verification (Per SLA Matrix)                     |
|  - Develop fix in private security fork, execute full regression tests          |
+---------------------------------------+-----------------------------------------+
                                        |
                                        v
+---------------------------------------------------------------------------------+
|  Stage 5: Coordinated Release & Advisory Publication                           |
|  - Merge patch, tag release, deploy to production, publish GitHub Advisory / CVE|
+---------------------------------------------------------------------------------+
```

### Detailed Workflow Stages

1. **Intake & Acknowledgment:**
   - The Security Response Team receives the disclosure or automated scanner alert.
   - Initial confirmation of receipt is delivered to the reporter within **24 hours**.

2. **Triage & Classification:**
   - Security engineers reproduce the vulnerability in an isolated environment.
   - The team assigns a CVSS v3.1 base score, calculates exploitability metrics, and determines if transitive dependencies expose active code paths.

3. **Containment & Mitigation:**
   - If an immediate upstream patch is unavailable, temporary compensating controls (e.g., input sanitization, configuration overrides, transitive lockfile pinning) are deployed.

4. **Remediation & Testing:**
   - A dedicated security branch (`security/remediate-<id>`) is created.
   - Dependency upgrades or code patches are applied and validated through the automated test suite, security scans, and integration tests.

5. **Release & Public Advisory:**
   - The fix is released as a patch release (e.g., `v2.7.2`).
   - If applicable, a CVE is requested and published through GitHub Security Advisories.
   - The original researcher is credited in the advisory release notes (with permission).

---

## 6. Response Timelines & SLAs

Our incident response team adheres to the following maximum turnaround times based on CVSS severity:

| Severity Level | CVSS Score | Initial Acknowledgment | Remediation SLA | Release Type |
| :--- | :---: | :---: | :---: | :--- |
| **Critical** | 9.0 – 10.0 | < 4 hours | < 24 – 48 hours | Emergency Out-of-Band Hotfix |
| **High** | 7.0 – 8.9 | < 12 hours | < 7 calendar days | Expedited Patch Release |
| **Medium** | 4.0 – 6.9 | < 24 hours | < 30 calendar days | Next Scheduled Minor/Patch Release |
| **Low** | 0.1 – 3.9 | < 48 hours | < 90 calendar days | Routine Maintenance Release |

---

## 7. Supply Chain Governance & Transitive Dependency Policy

To mitigate supply chain threats (typosquatting, compromised maintainer accounts, malicious releases):
- **Cryptographic Hashes Required:** All dependencies must have exact SHA-256 hashes generated via `pip-compile --generate-hashes`.
- **Transitive Pinning:** Transitive dependencies cannot float freely; all indirect packages must be pinned to immutable versions in production lockfiles.
- **Repository Provenance:** Dependencies must originate exclusively from verified PyPI index mirrors or certified trusted publishers.

---

## 8. Policy Enforcement & Audit Cadence

- **Automated CI Enforcement:** Non-compliant pull requests that fail vulnerability checks are automatically blocked from merging to `main`.
- **Quarterly Reviews:** This security policy and our dependency inventory undergo formal review by the Security Lead and Engineering Maintainers every quarter.
