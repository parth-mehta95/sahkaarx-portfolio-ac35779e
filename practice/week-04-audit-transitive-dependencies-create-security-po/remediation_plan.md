# Security Vulnerability Remediation Plan

**Project:** Python Application & Package Supply Chain Security  
**Document:** Vulnerability Remediation Plan & SLA Framework  
**Scope:** Direct Dependencies, Transitive Dependencies, and Application Code  
**Version:** 1.0.0  
**Effective Date:** October 2026  
**Status:** Active Governance Standard  

---

## 1. Purpose & Strategic Objectives

The purpose of this Security Remediation Plan is to establish a rigorous, repeatable, and automated operational framework for resolving security vulnerabilities discovered in direct and transitive (indirect) dependencies.

Transitive dependencies present unique operational challenges: when an indirect library has a known vulnerability, a team often cannot simply bump a top-level requirement without analyzing version constraints, downstream breaking changes, or upstream maintainer release schedules. This plan defines exact priority levels, binding fix timelines, remediation strategies for indirect packages, validation protocols, and rollback procedures.

---

## 2. Priority Classification Matrix & Fix Timelines (SLAs)

All discovered vulnerabilities must be categorized within **24 hours of detection** using CVSS v3.1 / v4.0 scoring combined with an active reachability assessment.

| Priority Level | CVSS Score Range | Business Impact / Exploitability | Initial Triage & Containment | Remediation & Fix SLA | Release Mechanism |
| :---: | :---: | :--- | :---: | :---: | :--- |
| **P0: Critical** | **9.0 – 10.0** | Actively exploitable remote code execution (RCE), unauthenticated bypass, or active in-the-wild supply chain compromise. | **< 4 Hours** | **< 24 – 48 Hours** | Emergency Out-of-Band Hotfix |
| **P1: High** | **7.0 – 8.9** | High-privilege escalation, sensitive data exfiltration, denial of service on mission-critical paths, or exploitable transitive library with public PoC. | **< 12 Hours** | **< 7 Calendar Days** | Expedited Priority Patch |
| **P2: Medium** | **4.0 – 6.9** | Conditional vulnerability requiring specific configuration, non-default feature activation, or authenticated access with low impact. | **< 24 Hours** | **< 30 Calendar Days** | Next Scheduled Sprint / Release |
| **P3: Low** | **0.1 – 3.9** | Informational security flaw, theoretical denial of service requiring extreme local conditions, or code path confirmed unreachable in our architecture. | **< 48 Hours** | **< 90 Calendar Days** | Routine Maintenance / Version Bump |

---

## 3. Transitive Dependency Remediation Playbook

When an alert flags an indirect (transitive) dependency, the engineering team executes the following decision hierarchy to eliminate the risk:

```
                    +------------------------------------+
                    |   Vulnerability Detected in        |
                    |   Transitive Dependency            |
                    +-----------------+------------------+
                                      |
                                      v
                    +------------------------------------+
                    | Is Upstream Parent Package Updated |
                    | with Safe Transitive Constraint?   |
                    +--------+------------------+--------+
                             |                  |
                       YES   |                  | NO
                             v                  v
        +----------------------------+   +------------------------------------+
        | Strategy A:                |   | Can Safe Version Be Explicitly     |
        | Bump Parent Dependency     |   | Pinned in requirements.in / Lock?  |
        | in requirements.in         |   +--------+------------------+--------+
        +----------------------------+            |                  |
                                            YES   |                  | NO
                                                  v                  v
                             +----------------------------+   +------------------------------------+
                             | Strategy B:                |   | Is Vulnerable Code Path Reachable  |
                             | Explicit Transitive Pin    |   | in Our Application?                |
                             | (Constraint Override)      |   +--------+------------------+--------+
                             +----------------------------+            |                  |
                                                                 YES   |                  | NO
                                                                       v                  v
                                                  +----------------------------+   +-----------------------+
                                                  | Strategy C / D:            |   | Document Exception &  |
                                                  | Compensating Control or    |   | Apply Workaround Flag |
                                                  | Replace Upstream Library   |   +-----------------------+
                                                  +----------------------------+
```

### Strategy A: Upstream Parent Version Bump (Preferred)
- **Scenario:** The parent library (e.g., `requests`) releases a new version that bumps the required version of the vulnerable transitive dependency (e.g., `urllib3 >= 2.0.7`).
- **Action:**
  1. Update `requirements.in` to allow or pin the new parent version.
  2. Re-run `pip-compile --generate-hashes requirements.in -o requirements.txt`.
  3. Validate full test suite.

### Strategy B: Explicit Transitive Pinning (Lockfile Override)
- **Scenario:** The parent package's declared constraint is loose (e.g., `urllib3>=1.21.1,<3`), but the lockfile pinned an older, vulnerable version. The parent has not yet published a new release.
- **Action:**
  1. Add an explicit constraint for the transitive dependency directly into `requirements.in`:
     ```text
     # Enforce patched transitive dependency until parent updates
     urllib3>=2.2.1; python_version>='3.10'
     ```
  2. Recompile the lockfile via `pip-compile --generate-hashes`.
  3. The resolver forces the safe version into `requirements.txt` while maintaining parent compatibility.

### Strategy C: Compensating Controls & Attack Surface Reduction
- **Scenario:** A patch is not yet available from the package maintainer, and the vulnerability is Critical (P0) or High (P1).
- **Action:**
  1. Implement immediate defensive controls at the application perimeter (e.g., Web Application Firewall rule, header stripping, or strict request body limits).
  2. Disable the specific module, feature flag, or unneeded optional sub-package in application settings.
  3. Log and alert on attempts to exercise the vulnerable endpoint.

### Strategy D: Package Replacement / Migration
- **Scenario:** The upstream parent is abandoned, unmaintained, or unable to resolve transitive security advisories within SLA.
- **Action:**
  1. Identify maintained drop-in replacements (e.g., replace deprecated HTTP client with `httpx`, or migrate parser to modern alternative).
  2. Schedule prioritized refactoring sprint with automated regression tests.

---

## 4. End-to-End Remediation Workflow

Every vulnerability remediation follows a structured 7-step execution cycle:

```
[1. Detect] --> [2. Triage & Verify] --> [3. Branch & Patch] --> [4. Automated Test] --> [5. Code Review] --> [6. Deploy] --> [7. Retrospective]
```

### Step 1: Detection & Alert Routing
- Vulnerability is identified via automated SCA (`pip-audit`, Dependabot, or manual disclosure).
- An automated GitHub Security Advisory tracking ticket is dispatched to the Security On-Call engineer.

### Step 2: Triage & Reachability Analysis
- The engineer determines whether our application exercises the vulnerable API method of the indirect package.
- If reachable: Assign SLA priority based on matrix.
- If unreachable: Document formal SCA exception justification and schedule remediation for standard maintenance window.

### Step 3: Branching & Isolated Fix Development
- Create a dedicated security fix branch: `security/fix-<cve-identifier>`.
- Apply minimum necessary modification to `requirements.in` / lockfile or code.

### Step 4: Verification & Automated Regression Testing
- Execute local and CI validation checks:
  ```bash
  # 1. Verify lockfile compiles cleanly with hashes
  pip-compile --generate-hashes requirements.in -o requirements.txt

  # 2. Run SCA vulnerability scanner to confirm zero alerts
  pip-audit --requirement requirements.txt --strict

  # 3. Validate dependency tree structure
  pipdeptree --warn fail

  # 4. Run test suite
  pytest tests/ --cov
  ```

### Step 5: Security Review & Approval
- PR requires two approvals: one Senior Core Maintainer and one Product Security Engineer.
- Reviewers verify that no unintended transitive packages or license changes were introduced.

### Step 6: Production Rollout & Smoke Verification
- Merge into `main` via linear history.
- Production CI/CD builds container image from immutable locked requirements.
- Execute canary / smoke testing in staging, followed by production rollout.

### Step 7: Post-Incident Review & Knowledge Capture
- Document lessons learned in the security incident log.
- If the issue was an unpatched zero-day, submit an upstream patch to open-source maintainers.

---

## 5. Rollback & Emergency Contingency Procedures

If a dependency bump or transitive remediation causes unexpected regressions or runtime errors:

1. **Rollback Trigger Criteria:**
   - Error rate increases by $> 0.5\%$ within 15 minutes of deployment.
   - Any failure in critical transactional pathways or health check endpoints.
   - Unexpected memory leak or process crash.
2. **Rollback Execution:**
   - Execute zero-downtime deployment rollback to the previous cryptographically signed image / git commit tag.
   - Revert lockfile in git: `git revert <commit-sha>`.
3. **Contingency Mitigation:**
   - Re-activate compensating controls (WAF filter or feature disablement) while debugging the dependency compatibility issue in a staging environment.

---

## 6. Governance, Cadence & Audit Schedule

| Activity | Frequency | Responsible Role | Deliverable |
| :--- | :---: | :--- | :--- |
| **Automated Dependency Scan** | Every Pull Request | CI/CD Pipeline (`pip-audit`) | Build Pass/Fail Gate |
| **Scheduled SCA Tree Scan** | Daily (02:00 UTC) | GitHub Actions Scheduled Workflow | Auto-generated Security PRs |
| **Triage & Backlog Review** | Weekly | Security Lead & Engineering Leads | SLA Tracking Dashboard |
| **Full Transitive Tree Audit** | Monthly | Lead Architect & Security Lead | Updated Dependency Audit Report |
| **Security Policy & SLA Review** | Semi-Annually | VP Engineering & Security Team | Policy Revision & Sign-off |
