#!/usr/bin/env python3
"""Build script generating standard Python distribution packages (.whl and .tar.gz)."""

import hashlib
import io
import os
import tarfile
import zipfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
DIST_DIR = os.path.join(BASE_DIR, "dist")

PACKAGE_NAME = "secure_data_pipeline"
VERSION = "1.0.0"

os.makedirs(DIST_DIR, exist_ok=True)


def build_wheel():
    whl_filename = f"{PACKAGE_NAME}-{VERSION}-py3-none-any.whl"
    whl_path = os.path.join(DIST_DIR, whl_filename)
    dist_info = f"{PACKAGE_NAME}-{VERSION}.dist-info"

    metadata_content = f"""Metadata-Version: 2.1
Name: secure-data-pipeline
Version: {VERSION}
Summary: Production-grade data pipeline framework with dependency injection and validated APIs
Home-page: https://github.com/organization/secure-data-pipeline
Author: Engineering & Platform Security Team
Author-email: engineering@example.com
License: MIT
Classifier: Development Status :: 5 - Production/Stable
Classifier: License :: OSI Approved :: MIT License
Classifier: Programming Language :: Python :: 3
Requires-Python: >=3.9
Requires-Dist: requests>=2.31.0
Requires-Dist: urllib3>=2.0.7
Requires-Dist: jinja2>=3.1.4
Requires-Dist: cryptography>=42.0.5

Production-ready data pipeline framework featuring dependency injection and secure validated endpoints.
"""

    wheel_content = """Wheel-Version: 1.0
Generator: bdist_wheel (0.42.0)
Root-Is-Purelib: true
Tag: py3-none-any
"""

    entry_points_content = """[console_scripts]
datapipeline = datapipeline.api.app:main
datapipeline-verify = datapipeline.verify_install:main
"""

    top_level_content = "datapipeline\n"

    records = []

    with zipfile.ZipFile(whl_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add src/datapipeline files
        for root, _, files in os.walk(SRC_DIR):
            for file in files:
                if file.endswith(".pyc") or "__pycache__" in root:
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, SRC_DIR).replace("\\", "/")
                with open(full_path, "rb") as f:
                    data = f.read()
                zf.writestr(rel_path, data)
                h = hashlib.sha256(data).digest()
                h_b64 = hashlib.sha256(data).hexdigest()
                records.append(f"{rel_path},sha256={h_b64},{len(data)}")

        # Add dist-info files
        extra_files = [
            (f"{dist_info}/METADATA", metadata_content.encode("utf-8")),
            (f"{dist_info}/WHEEL", wheel_content.encode("utf-8")),
            (f"{dist_info}/entry_points.txt", entry_points_content.encode("utf-8")),
            (f"{dist_info}/top_level.txt", top_level_content.encode("utf-8")),
        ]

        for path_name, content_bytes in extra_files:
            zf.writestr(path_name, content_bytes)
            h_b64 = hashlib.sha256(content_bytes).hexdigest()
            records.append(f"{path_name},sha256={h_b64},{len(content_bytes)}")

        # Add RECORD
        record_content = "\n".join(records) + f"\n{dist_info}/RECORD,,\n"
        zf.writestr(f"{dist_info}/RECORD", record_content.encode("utf-8"))

    print(f"[OK] Generated wheel: {whl_path} ({os.path.getsize(whl_path)} bytes)")
    return whl_path


def build_sdist():
    tar_filename = f"{PACKAGE_NAME}-{VERSION}.tar.gz"
    tar_path = os.path.join(DIST_DIR, tar_filename)
    prefix = f"{PACKAGE_NAME}-{VERSION}"

    with tarfile.open(tar_path, "w:gz") as tar:
        # Add pyproject.toml, setup.py, requirements.in, requirements.lock
        for f in ["pyproject.toml", "setup.py", "requirements.in", "requirements.lock"]:
            f_path = os.path.join(BASE_DIR, f)
            if os.path.exists(f_path):
                tar.add(f_path, arcname=f"{prefix}/{f}")

        # Add src
        tar.add(SRC_DIR, arcname=f"{prefix}/src")

    print(f"[OK] Generated sdist: {tar_path} ({os.path.getsize(tar_path)} bytes)")
    return tar_path


def main():
    print("Building distributions for release...")
    whl = build_wheel()
    sdist = build_sdist()
    print("Build complete. Artifacts located in 'dist/':")
    for f in os.listdir(DIST_DIR):
        print(f"  - {f} ({os.path.getsize(os.path.join(DIST_DIR, f))} bytes)")


if __name__ == "__main__":
    main()
