#!/usr/bin/env python3
"""
Automated Dependency Update & Compatibility Validation Script
============================================================

This script checks project dependencies against PyPI releases, enforces semantic
versioning constraints to prevent breaking changes, validates cross-dependency
compatibility, and safely updates requirement specifications and lockfiles.

Usage:
    python update_dependencies.py --check
    python update_dependencies.py --update --strategy minor
    python update_dependencies.py --validate
    python update_dependencies.py --dry-run
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# ==============================================================================
# 1. Version Parsing and Comparison (PEP 440 & Semantic Versioning)
# ==============================================================================

@dataclass(order=True)
class Version:
    """Represents a parsed semantic version conforming to PEP 440."""
    epoch: int = 0
    release: Tuple[int, ...] = (0, 0, 0)
    pre: Optional[Tuple[str, int]] = None
    post: Optional[int] = None
    dev: Optional[int] = None
    raw: str = field(compare=False, default="")

    @classmethod
    def parse(cls, version_str: str) -> "Version":
        """Parses a version string into a comparable Version object."""
        clean = version_str.strip()
        raw = clean

        epoch = 0
        if "!" in clean:
            parts = clean.split("!", 1)
            try:
                epoch = int(parts[0])
            except ValueError:
                epoch = 0
            clean = parts[1]

        # Strip build metadata (+...)
        clean = clean.split("+")[0]

        # Extract post-release (.postN or -N)
        post = None
        post_match = re.search(r"(\.post|-post|r)(\d+)", clean, re.IGNORECASE)
        if post_match:
            post = int(post_match.group(2))
            clean = clean[:post_match.start()]

        # Extract dev-release (.devN)
        dev = None
        dev_match = re.search(r"(\.dev)(\d+)", clean, re.IGNORECASE)
        if dev_match:
            dev = int(dev_match.group(2))
            clean = clean[:dev_match.start()]

        # Extract pre-release (aN, bN, rcN)
        pre = None
        pre_match = re.search(r"(\.?(a|b|c|rc|alpha|beta|preview))(\d*)", clean, re.IGNORECASE)
        if pre_match:
            pre_type = pre_match.group(2).lower()
            if pre_type in ("alpha", "a"):
                norm_type = "a"
            elif pre_type in ("beta", "b"):
                norm_type = "b"
            else:
                norm_type = "rc"
            pre_num = int(pre_match.group(3)) if pre_match.group(3) else 0
            pre = (norm_type, pre_num)
            clean = clean[:pre_match.start()]

        # Extract numeric components
        parts = []
        for segment in re.split(r"[._-]", clean):
            digits = "".join(ch for ch in segment if ch.isdigit())
            if digits:
                parts.append(int(digits))

        while len(parts) < 3:
            parts.append(0)

        return cls(
            epoch=epoch,
            release=tuple(parts),
            pre=pre,
            post=post,
            dev=dev,
            raw=raw or "0.0.0"
        )

    @property
    def major(self) -> int:
        return self.release[0] if len(self.release) > 0 else 0

    @property
    def minor(self) -> int:
        return self.release[1] if len(self.release) > 1 else 0

    @property
    def patch(self) -> int:
        return self.release[2] if len(self.release) > 2 else 0

    @property
    def is_prerelease(self) -> bool:
        return self.pre is not None or self.dev is not None

    def __str__(self) -> str:
        return self.raw or ".".join(str(x) for x in self.release)


# ==============================================================================
# 2. Specifier and Constraint Logic
# ==============================================================================

@dataclass
class Specifier:
    """Represents a single version constraint clause (e.g. >=2.31.0, <3.0.0)."""
    operator: str
    target_version: Version

    def is_satisfied_by(self, version: Version) -> bool:
        """Evaluates if a candidate version satisfies this specifier clause."""
        v = version
        t = self.target_version

        # Truncate comparison lengths for wildcard / prefix matching if needed
        v_rel = v.release
        t_rel = t.release

        if self.operator == "==":
            return v.release == t.release and v.pre == t.pre
        elif self.operator == "!=":
            return not (v.release == t.release and v.pre == t.pre)
        elif self.operator == "<":
            return v < t
        elif self.operator == "<=":
            return v <= t
        elif self.operator == ">":
            return v > t
        elif self.operator == ">=":
            return v >= t
        elif self.operator == "~=":
            # Compatible release clause (~= X.Y or ~= X.Y.Z)
            # ~= 2.31.0 means >= 2.31.0, == 2.31.* (same major & minor)
            # ~= 2.31 means >= 2.31, == 2.* (same major)
            if v < t:
                return False
            # Check prefix boundary
            if len(t.release) >= 3:
                # Same major and minor
                return v.major == t.major and v.minor == t.minor
            else:
                # Same major
                return v.major == t.major
        return True


@dataclass
class Requirement:
    """Represents a dependency line with package name and constraints."""
    name: str
    current_version: Optional[Version] = None
    specifiers: List[Specifier] = field(default_factory=list)
    raw_line: str = ""
    comment: str = ""

    @classmethod
    def parse(cls, line: str) -> Optional["Requirement"]:
        """Parses a requirements line into a structured Requirement."""
        raw_line = line.strip()
        if not raw_line or raw_line.startswith("#"):
            return None

        # Strip inline comments
        comment = ""
        if " #" in raw_line:
            code_part, comment_part = raw_line.split(" #", 1)
            raw_line = code_part.strip()
            comment = comment_part.strip()

        # Remove markers (e.g., ; python_version >= '3.8')
        raw_spec = raw_line.split(";")[0].strip()

        # Parse package name vs constraints
        pattern = r"^([A-Za-z0-9_\-\.]+)(.*)$"
        match = re.match(pattern, raw_spec)
        if not match:
            return None

        name = match.group(1).strip()
        constraints_str = match.group(2).strip()

        specifiers: List[Specifier] = []
        current_version: Optional[Version] = None

        if constraints_str:
            clauses = [c.strip() for c in constraints_str.split(",") if c.strip()]
            for clause in clauses:
                spec_match = re.match(r"^(==|!=|<=|>=|<|>|~=)\s*(.*)$", clause)
                if spec_match:
                    op = spec_match.group(1)
                    ver_str = spec_match.group(2).strip()
                    ver = Version.parse(ver_str)
                    specifiers.append(Specifier(operator=op, target_version=ver))
                    if op == "==" and current_version is None:
                        current_version = ver
                    elif op == ">=" and current_version is None:
                        current_version = ver

        return cls(
            name=name,
            current_version=current_version,
            specifiers=specifiers,
            raw_line=line,
            comment=comment
        )

    def satisfies_all(self, version: Version) -> bool:
        """Returns True if the candidate version meets all defined constraints."""
        return all(spec.is_satisfied_by(version) for spec in self.specifiers)


# ==============================================================================
# 3. PyPI Package Metadata Client
# ==============================================================================

class PyPIClient:
    """Fetches package metadata and release lists from PyPI."""

    def __init__(self, timeout_sec: int = 5):
        self.timeout_sec = timeout_sec
        self._cache: Dict[str, dict] = {}

    def fetch_package_data(self, package_name: str) -> Optional[dict]:
        """Queries PyPI JSON API for package details."""
        if package_name.lower() in self._cache:
            return self._cache[package_name.lower()]

        url = f"https://pypi.org/pypi/{package_name}/json"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "SahkaarX-Dependency-Update-Workflow/2.0"}
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    self._cache[package_name.lower()] = data
                    return data
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
            return None
        return None

    def get_releases(self, package_name: str) -> List[Version]:
        """Returns sorted list of available releases (ascending)."""
        data = self.fetch_package_data(package_name)
        if not data or "releases" not in data:
            return []

        versions: List[Version] = []
        for ver_str in data["releases"].keys():
            try:
                v = Version.parse(ver_str)
                # Ignore empty release lists (yanked or file-less releases)
                if data["releases"][ver_str]:
                    versions.append(v)
            except Exception:
                continue

        versions.sort()
        return versions

    def get_dependencies(self, package_name: str, version_str: str) -> List[str]:
        """Extracts required dependencies declared by a package release."""
        data = self.fetch_package_data(package_name)
        if not data or "info" not in data:
            return []
        requires_dist = data["info"].get("requires_dist")
        if requires_dist:
            return requires_dist
        return []


# ==============================================================================
# 4. Update Analysis and Pinning Strategy
# ==============================================================================

@dataclass
class UpdateAnalysis:
    """Holds comparison results and upgrade recommendations for a package."""
    requirement: Requirement
    current_version: Optional[Version]
    latest_compatible: Optional[Version]
    latest_overall: Optional[Version]
    update_type: str  # "UP_TO_DATE", "PATCH", "MINOR", "MAJOR_BREAKING", "UNKNOWN"
    is_compatible: bool
    status_message: str
    breaking_change_warning: bool = False


class DependencyUpdateWorkflow:
    """
    Main workflow orchestrator:
    - Analyzes dependencies
    - Enforces constraint pinning
    - Prevents breaking changes
    - Validates compatibility
    - Updates requirement files and lockfiles
    """

    def __init__(self, pypi_client: Optional[PyPIClient] = None):
        self.pypi = pypi_client or PyPIClient()

    def analyze_requirement(self, req: Requirement) -> UpdateAnalysis:
        """Analyzes a single requirement against PyPI releases and constraints."""
        releases = self.pypi.get_releases(req.name)
        current = req.current_version

        if not releases:
            # Fallback when offline or package not found
            return UpdateAnalysis(
                requirement=req,
                current_version=current,
                latest_compatible=current,
                latest_overall=current,
                update_type="UP_TO_DATE",
                is_compatible=True,
                status_message="Up-to-date (No newer remote releases or offline mode)"
            )

        # Exclude pre-releases unless current is pre-release
        valid_releases = [
            v for v in releases
            if not v.is_prerelease or (current and current.is_prerelease)
        ]
        if not valid_releases:
            valid_releases = releases

        latest_overall = valid_releases[-1] if valid_releases else None

        # Filter releases satisfying existing constraints
        compatible_releases = [v for v in valid_releases if req.satisfies_all(v)]
        latest_compatible = compatible_releases[-1] if compatible_releases else current

        # Determine update classification
        update_type = "UP_TO_DATE"
        breaking_warning = False
        status_msg = "Up-to-date"

        if current and latest_compatible and latest_compatible > current:
            if latest_compatible.major > current.major:
                update_type = "MAJOR_BREAKING"
                breaking_warning = True
                status_msg = f"Breaking upgrade available: {current} -> {latest_compatible}"
            elif latest_compatible.minor > current.minor:
                update_type = "MINOR"
                status_msg = f"Safe minor feature update: {current} -> {latest_compatible}"
            elif latest_compatible.patch > current.patch:
                update_type = "PATCH"
                status_msg = f"Safe patch bug fix: {current} -> {latest_compatible}"

        # Check if constraints blocked an even newer major release
        if current and latest_overall and latest_compatible:
            if latest_overall > latest_compatible and latest_overall.major > current.major:
                breaking_warning = True
                if update_type == "UP_TO_DATE":
                    status_msg = f"Constraints blocked breaking change ({latest_overall.raw}); remaining on {current}"
                else:
                    status_msg += f" (Blocked breaking {latest_overall.raw} by constraint)"

        return UpdateAnalysis(
            requirement=req,
            current_version=current,
            latest_compatible=latest_compatible,
            latest_overall=latest_overall,
            update_type=update_type,
            is_compatible=True,
            status_message=status_msg,
            breaking_change_warning=breaking_warning
        )

    def validate_compatibility(self, analyses: List[UpdateAnalysis]) -> Tuple[bool, List[str]]:
        """
        Validates cross-package dependency compatibility before suggesting upgrades.
        Detects known conflicting dependency ranges.
        """
        issues: List[str] = []
        is_valid = True

        packages_map = {
            a.requirement.name.lower(): (a.latest_compatible or a.current_version)
            for a in analyses
        }

        # Inspect known inter-dependency constraints (e.g. requests vs urllib3)
        # requests 2.31.0 requires urllib3<3,>=1.21.1
        for analysis in analyses:
            pkg_name = analysis.requirement.name.lower()
            target_ver = analysis.latest_compatible or analysis.current_version
            if not target_ver:
                continue

            # Query PyPI for declared required distributions
            dists = self.pypi.get_dependencies(pkg_name, target_ver.raw)
            for dist_str in dists:
                # Match required distribution
                sub_req = Requirement.parse(dist_str)
                if not sub_req:
                    continue
                dep_name = sub_req.name.lower()
                if dep_name in packages_map:
                    dep_ver = packages_map[dep_name]
                    if dep_ver and not sub_req.satisfies_all(dep_ver):
                        is_valid = False
                        msg = (
                            f"Compatibility conflict: {pkg_name} {target_ver} requires "
                            f"{sub_req.raw_line}, but target plan has {dep_name} {dep_ver}"
                        )
                        issues.append(msg)

        return is_valid, issues

    def build_updated_line(
        self,
        analysis: UpdateAnalysis,
        strategy: str = "compatible",
        pin_type: str = "lock"
    ) -> str:
        """
        Applies version pinning logic to generate updated requirement line:
        - For 'lock' (e.g. requirements.lock): strictly pin exact version (==X.Y.Z)
        - For 'spec' (e.g. requirements.in): respect safe upper-bound constraints (>=X.Y.Z, <(X+1).0.0)
        """
        req = analysis.requirement
        target = analysis.latest_compatible or analysis.current_version

        if not target:
            return req.raw_line

        # Respect user update strategy filters
        if strategy == "patch" and analysis.update_type not in ("PATCH", "UP_TO_DATE"):
            target = analysis.current_version or target
        elif strategy == "minor" and analysis.update_type not in ("PATCH", "MINOR", "UP_TO_DATE"):
            target = analysis.current_version or target

        if pin_type == "lock":
            # Exact deterministic pin for production reproducibility
            line = f"{req.name}=={target.raw}"
            if req.comment:
                line += f"  # {req.comment}"
            return line
        else:
            # Flexible safe specification for requirements.in
            # e.g.: requests>=2.32.0,<3.0.0
            next_major = target.major + 1
            line = f"{req.name}>={target.raw},<{next_major}.0.0"
            if req.comment:
                line += f"  # {req.comment}"
            return line


# ==============================================================================
# 5. Requirement File Parsers & Exporters
# ==============================================================================

def load_requirements_file(file_path: Path) -> List[Requirement]:
    """Reads requirement declarations from a requirements file."""
    if not file_path.exists():
        return []

    requirements = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            req = Requirement.parse(line)
            if req:
                requirements.append(req)
    return requirements


def write_requirements_file(
    file_path: Path,
    original_lines: List[str],
    analyses_map: Dict[str, UpdateAnalysis],
    workflow: DependencyUpdateWorkflow,
    strategy: str = "compatible",
    pin_type: str = "spec"
) -> None:
    """Updates requirement file in-place preserving formatting and comments."""
    output_lines = []
    for line in original_lines:
        req = Requirement.parse(line)
        if req and req.name.lower() in analyses_map:
            analysis = analyses_map[req.name.lower()]
            new_line = workflow.build_updated_line(analysis, strategy=strategy, pin_type=pin_type)
            output_lines.append(new_line + "\n")
        else:
            output_lines.append(line)

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(output_lines)


# ==============================================================================
# 6. Reporting and CLI Interface
# ==============================================================================

def format_ascii_table(rows: List[List[str]], headers: List[str]) -> str:
    """Renders a clean formatted ASCII table for terminal output."""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(val)))

    sep = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
    header_str = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"

    lines = [sep, header_str, sep]
    for row in rows:
        r_str = "| " + " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(headers))) + " |"
        lines.append(r_str)
    lines.append(sep)
    return "\n".join(lines)


def run_workflow(
    input_file: Path,
    lock_file: Optional[Path],
    update: bool,
    strategy: str,
    dry_run: bool,
    validate_only: bool,
    as_json: bool
) -> int:
    """Executes the complete dependency update workflow."""
    if not input_file.exists():
        print(f"Error: Requirements file not found at {input_file}", file=sys.stderr)
        return 1

    requirements = load_requirements_file(input_file)
    if not requirements:
        print(f"Warning: No valid dependencies found in {input_file}")
        return 0

    workflow = DependencyUpdateWorkflow()

    print(f"\n=======================================================")
    print(f"  Dependency Update & Pinning Workflow")
    print(f"  Target File : {input_file.name}")
    print(f"  Strategy    : {strategy.upper()} updates")
    print(f"  Action      : {'DRY RUN' if dry_run else ('UPDATE' if update else 'CHECK')}")
    print(f"=======================================================\n")

    analyses: List[UpdateAnalysis] = []
    analyses_map: Dict[str, UpdateAnalysis] = {}

    for req in requirements:
        analysis = workflow.analyze_requirement(req)
        analyses.append(analysis)
        analyses_map[req.name.lower()] = analysis

    # Step 1: Compatibility Validation
    is_valid, comp_issues = workflow.validate_compatibility(analyses)

    if as_json:
        report = {
            "is_compatible": is_valid,
            "issues": comp_issues,
            "dependencies": [
                {
                    "name": a.requirement.name,
                    "current": str(a.current_version) if a.current_version else "None",
                    "latest_compatible": str(a.latest_compatible) if a.latest_compatible else "None",
                    "latest_overall": str(a.latest_overall) if a.latest_overall else "None",
                    "type": a.update_type,
                    "status": a.status_message,
                    "breaking_prevented": a.breaking_change_warning
                }
                for a in analyses
            ]
        }
        print(json.dumps(report, indent=2))
        return 0 if is_valid else 1

    # Step 2: Render Summary Table
    table_headers = ["Package", "Current", "Compatible", "Latest PyPI", "Update Type", "Constraint Status"]
    table_rows = []

    for a in analyses:
        table_rows.append([
            a.requirement.name,
            str(a.current_version) if a.current_version else "unpinned",
            str(a.latest_compatible) if a.latest_compatible else "n/a",
            str(a.latest_overall) if a.latest_overall else "n/a",
            a.update_type,
            "SAFE" if not a.breaking_change_warning else "PROTECTED (< breaking)"
        ])

    print(format_ascii_table(table_rows, table_headers))

    # Compatibility Results
    print("\nCompatibility Check:")
    if is_valid:
        print("  [PASSED] All planned dependency upgrades satisfy mutual constraints.")
    else:
        print("  [FAILED] Compatibility conflicts detected:")
        for issue in comp_issues:
            print(f"    - {issue}")
        if not update:
            return 1

    # Step 3: Apply Updates if requested
    if update or dry_run:
        print("\nProposed Changes:")
        with open(input_file, "r", encoding="utf-8") as f:
            original_lines = f.readlines()

        for req in requirements:
            analysis = analyses_map[req.name.lower()]
            curr_str = str(analysis.current_version) if analysis.current_version else "unpinned"
            target_str = str(analysis.latest_compatible) if analysis.latest_compatible else curr_str
            if curr_str != target_str:
                new_line = workflow.build_updated_line(analysis, strategy=strategy, pin_type="spec")
                print(f"  * {req.name}: {req.raw_line.strip()}  -->  {new_line}")

        if dry_run:
            print("\n[DRY RUN] No files were modified on disk.")
        else:
            if not is_valid:
                print("\n[ABORTED] Update halted to prevent breaking changes due to compatibility conflicts.")
                return 1

            write_requirements_file(input_file, original_lines, analyses_map, workflow, strategy=strategy, pin_type="spec")
            print(f"\n[UPDATED] Successfully updated {input_file}")

            # Also update lock file if provided
            if lock_file:
                with open(lock_file, "r", encoding="utf-8") if lock_file.exists() else [] as f:
                    orig_lock = f.readlines() if lock_file.exists() else []
                write_requirements_file(lock_file, orig_lock, analyses_map, workflow, strategy=strategy, pin_type="lock")
                print(f"[UPDATED] Successfully synced lockfile at {lock_file}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Automated Dependency Update Workflow with Safe Pinning and Compatibility Checks."
    )
    parser.add_argument(
        "--file", "-f",
        type=Path,
        default=Path("requirements.in"),
        help="Path to input requirements specification (default: requirements.in)"
    )
    parser.add_argument(
        "--lock-file", "-l",
        type=Path,
        default=Path("requirements.lock"),
        help="Path to output pinned lockfile (default: requirements.lock)"
    )
    parser.add_argument(
        "--check", "-c",
        action="store_true",
        help="Check for outdated packages without making modifications"
    )
    parser.add_argument(
        "--update", "-u",
        action="store_true",
        help="Apply updates respecting defined constraint boundaries"
    )
    parser.add_argument(
        "--strategy", "-s",
        choices=["patch", "minor", "compatible", "all"],
        default="compatible",
        help="Update strategy: 'patch' (bug fixes only), 'minor' (minor + patch), 'compatible' (respect < next major), 'all'"
    )
    parser.add_argument(
        "--validate", "-v",
        action="store_true",
        help="Perform compatibility validation between packages"
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Simulate updates and display diff without writing to disk"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format for CI/CD integration"
    )

    args = parser.parse_args()

    # Default action if neither --check, --update, --validate, or --dry-run specified
    if not (args.check or args.update or args.validate or args.dry_run):
        args.check = True

    status_code = run_workflow(
        input_file=args.file,
        lock_file=args.lock_file,
        update=args.update,
        strategy=args.strategy,
        dry_run=args.dry_run,
        validate_only=args.validate,
        as_json=args.json
    )
    sys.exit(status_code)


if __name__ == "__main__":
    main()
