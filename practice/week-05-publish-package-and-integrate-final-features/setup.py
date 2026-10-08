#!/usr/bin/env python3
"""Setup script for secure-data-pipeline package."""

from setuptools import setup, find_packages

setup(
    name="secure-data-pipeline",
    version="1.0.0",
    description="Production-grade data pipeline framework with dependency injection and validated APIs",
    long_description=open("PACKAGE_README.md", encoding="utf-8").read() if __import__("os").path.exists("PACKAGE_README.md") else "Secure Data Pipeline",
    long_description_content_type="text/markdown",
    author="Engineering & Platform Security Team",
    author_email="engineering@example.com",
    url="https://github.com/organization/secure-data-pipeline",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.31.0",
        "urllib3>=2.0.7",
        "jinja2>=3.1.4",
        "cryptography>=42.0.5",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "bandit>=1.7.5",
            "pip-audit>=2.7.3",
            "twine>=4.0.2",
            "build>=1.0.3",
        ],
        "security": [
            "pip-audit>=2.7.3",
            "safety>=3.2.0",
            "bandit>=1.7.5",
        ],
    },
    entry_points={
        "console_scripts": [
            "datapipeline=datapipeline.api.app:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Security",
    ],
)
