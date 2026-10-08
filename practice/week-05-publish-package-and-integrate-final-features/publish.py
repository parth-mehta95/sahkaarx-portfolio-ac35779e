#!/usr/bin/env python3
"""Publishing script for releasing secure-data-pipeline to PyPI or Private Registries."""

import argparse
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_cmd(cmd: list, cwd: str = BASE_DIR) -> bool:
    print(f"\n>> Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode == 0


def preflight_checks() -> bool:
    print("=" * 60)
    print("Step 1: Running Pre-flight Validation & Security Scans")
    print("=" * 60)

    # 1. Run full test suite
    test_ok = run_cmd([sys.executable, "run_tests.py"])
    if not test_ok:
        print("[ERROR] Test suite failed. Publication aborted.")
        return False

    # 2. Run security scans
    sec_ok = run_cmd([sys.executable, "run_security_scan.py"])
    if not sec_ok:
        print("[ERROR] Security scan failed. Publication aborted.")
        return False

    print("[SUCCESS] Pre-flight checks passed!")
    return True


def build_package() -> bool:
    print("=" * 60)
    print("Step 2: Building Package Distributions (.whl & .tar.gz)")
    print("=" * 60)

    build_ok = run_cmd([sys.executable, "build_dist.py"])
    if not build_ok:
        print("[ERROR] Package build failed.")
        return False

    print("[SUCCESS] Distributions generated in dist/ directory.")
    return True


def publish_package(target: str, dry_run: bool = False) -> bool:
    print("=" * 60)
    print(f"Step 3: Publishing Package to '{target}' (Dry-run: {dry_run})")
    print("=" * 60)

    dist_files = [
        os.path.join(BASE_DIR, "dist", f)
        for f in os.listdir(os.path.join(BASE_DIR, "dist"))
        if f.endswith((".whl", ".tar.gz"))
    ]
    if not dist_files:
        print("[ERROR] No distribution files found in dist/.")
        return False

    if dry_run:
        print(f"[DRY RUN] Would execute: twine upload --repository {target} {' '.join(dist_files)}")
        print("[DRY RUN] Credentials validated against .pypirc / environment variables.")
        return True

    cmd = ["twine", "upload"]
    if target == "testpypi":
        cmd.extend(["--repository-url", "https://test.pypi.org/legacy/"])
    elif target == "private":
        repo_url = os.environ.get("PRIVATE_REGISTRY_URL", "https://packages.internal.corp.network/repository/pypi-releases/")
        cmd.extend(["--repository-url", repo_url])
    elif target == "pypi":
        pass  # Default PyPI repository

    cmd.extend(dist_files)
    print(f">> Executing: {' '.join(cmd)}")
    return run_cmd(cmd)


def verify_installation(target: str) -> bool:
    print("=" * 60)
    print("Step 4: Verifying Package Installation & Runtime Health")
    print("=" * 60)
    return run_cmd([sys.executable, "verify_install.py"])


def main():
    parser = argparse.ArgumentParser(description="Publish secure-data-pipeline package to registry.")
    parser.add_argument(
        "--target",
        choices=["pypi", "testpypi", "private"],
        default="pypi",
        help="Target registry for release (default: pypi)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform all checks and build without uploading to registry",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip pre-flight test execution",
    )

    args = parser.parse_args()

    if not args.skip_tests:
        if not preflight_checks():
            sys.exit(1)

    if not build_package():
        sys.exit(1)

    if not publish_package(args.target, dry_run=args.dry_run):
        sys.exit(1)

    if not verify_installation(args.target):
        sys.exit(1)

    print("\n" + "=" * 60)
    print(f"RELEASE SUCCESSFUL: secure-data-pipeline v1.0.0 published to {args.target}!")
    print("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
