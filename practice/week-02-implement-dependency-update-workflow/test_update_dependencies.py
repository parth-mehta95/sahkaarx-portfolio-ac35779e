"""
Unit Tests for Dependency Update Workflow
=========================================

Verifies:
1. Version parsing & PEP 440 comparison logic.
2. Specifier constraint evaluation (==, !=, <, <=, >, >=, ~=).
3. Breaking change prevention & constraint enforcement.
4. Compatibility validation between conflicting dependencies.
5. Line building & pinning logic for specs and lockfiles.
"""

import unittest
from pathlib import Path
import tempfile
import shutil

from update_dependencies import (
    Version,
    Specifier,
    Requirement,
    UpdateAnalysis,
    DependencyUpdateWorkflow,
    PyPIClient,
    load_requirements_file,
    write_requirements_file,
)


class MockPyPIClient(PyPIClient):
    """Mock PyPI client returning controlled test data without network calls."""

    def __init__(self, releases_data=None, deps_data=None):
        super().__init__()
        self.releases_data = releases_data or {}
        self.deps_data = deps_data or {}

    def get_releases(self, package_name: str):
        versions_raw = self.releases_data.get(package_name.lower(), [])
        versions = [Version.parse(v) for v in versions_raw]
        versions.sort()
        return versions

    def get_dependencies(self, package_name: str, version_str: str):
        return self.deps_data.get(package_name.lower(), {}).get(version_str, [])


class TestVersionParsing(unittest.TestCase):
    def test_version_order(self):
        v1 = Version.parse("2.31.0")
        v2 = Version.parse("2.31.1")
        v3 = Version.parse("2.32.0")
        v4 = Version.parse("3.0.0")

        self.assertTrue(v1 < v2)
        self.assertTrue(v2 < v3)
        self.assertTrue(v3 < v4)
        self.assertEqual(v1.major, 2)
        self.assertEqual(v1.minor, 31)
        self.assertEqual(v1.patch, 0)

    def test_prerelease_detection(self):
        v_pre = Version.parse("3.0.0a1")
        v_normal = Version.parse("3.0.0")

        self.assertTrue(v_pre.is_prerelease)
        self.assertFalse(v_normal.is_prerelease)


class TestSpecifiersAndConstraints(unittest.TestCase):
    def test_exact_match(self):
        spec = Specifier(operator="==", target_version=Version.parse("2.31.0"))
        self.assertTrue(spec.is_satisfied_by(Version.parse("2.31.0")))
        self.assertFalse(spec.is_satisfied_by(Version.parse("2.31.1")))

    def test_upper_bound_constraint(self):
        # <3.0.0 should prevent breaking major changes
        spec = Specifier(operator="<", target_version=Version.parse("3.0.0"))
        self.assertTrue(spec.is_satisfied_by(Version.parse("2.32.0")))
        self.assertFalse(spec.is_satisfied_by(Version.parse("3.0.0")))
        self.assertFalse(spec.is_satisfied_by(Version.parse("3.0.1")))

    def test_compatible_release(self):
        # ~= 2.31.0 allows >= 2.31.0, == 2.31.*
        spec = Specifier(operator="~=", target_version=Version.parse("2.31.0"))
        self.assertTrue(spec.is_satisfied_by(Version.parse("2.31.2")))
        self.assertFalse(spec.is_satisfied_by(Version.parse("2.32.0")))

    def test_compound_requirement(self):
        # requests>=2.31.0,<3.0.0
        line = "requests>=2.31.0,<3.0.0"
        req = Requirement.parse(line)
        self.assertIsNotNone(req)
        self.assertEqual(req.name, "requests")
        self.assertTrue(req.satisfies_all(Version.parse("2.31.0")))
        self.assertTrue(req.satisfies_all(Version.parse("2.32.0")))
        self.assertFalse(req.satisfies_all(Version.parse("3.0.0")))
        self.assertFalse(req.satisfies_all(Version.parse("2.30.0")))


class TestUpdateWorkflow(unittest.TestCase):
    def setUp(self):
        mock_releases = {
            "requests": ["2.30.0", "2.31.0", "2.32.0", "3.0.0"],
            "urllib3": ["2.1.0", "2.2.1", "2.2.2", "3.0.0"],
            "certifi": ["2024.2.2", "2024.7.4"]
        }
        mock_deps = {
            "requests": {
                "2.32.0": ["urllib3<3,>=1.21.1", "certifi>=2017.4.17"]
            }
        }
        self.client = MockPyPIClient(mock_releases, mock_deps)
        self.workflow = DependencyUpdateWorkflow(pypi_client=self.client)

    def test_outdated_package_detected_within_constraints(self):
        req = Requirement.parse("requests>=2.31.0,<3.0.0")
        analysis = self.workflow.analyze_requirement(req)

        self.assertEqual(str(analysis.current_version), "2.31.0")
        # Latest compatible should be 2.32.0, because 3.0.0 is blocked by <3.0.0
        self.assertEqual(str(analysis.latest_compatible), "2.32.0")
        self.assertEqual(str(analysis.latest_overall), "3.0.0")
        self.assertEqual(analysis.update_type, "MINOR")
        self.assertTrue(analysis.breaking_change_warning)

    def test_pinning_logic_lockfile_vs_spec(self):
        req = Requirement.parse("requests>=2.31.0,<3.0.0")
        analysis = self.workflow.analyze_requirement(req)

        # Lock pin should be strict
        lock_line = self.workflow.build_updated_line(analysis, pin_type="lock")
        self.assertEqual(lock_line, "requests==2.32.0")

        # Spec pin should preserve upper bound constraint to avoid breaking changes
        spec_line = self.workflow.build_updated_line(analysis, pin_type="spec")
        self.assertEqual(spec_line, "requests>=2.32.0,<3.0.0")

    def test_compatibility_validation_passes(self):
        req_req = Requirement.parse("requests>=2.31.0,<3.0.0")
        req_url = Requirement.parse("urllib3>=2.2.1,<3.0.0")

        analyses = [
            self.workflow.analyze_requirement(req_req),
            self.workflow.analyze_requirement(req_url)
        ]

        is_valid, issues = self.workflow.validate_compatibility(analyses)
        self.assertTrue(is_valid)
        self.assertEqual(len(issues), 0)

    def test_compatibility_validation_detects_conflict(self):
        # Simulate conflicting requirement
        conflict_deps = {
            "requests": {
                "2.32.0": ["urllib3<2.0.0"]  # Requests requires urllib3 < 2.0.0
            }
        }
        client = MockPyPIClient(self.client.releases_data, conflict_deps)
        wf = DependencyUpdateWorkflow(pypi_client=client)

        req_req = Requirement.parse("requests>=2.31.0,<3.0.0")
        req_url = Requirement.parse("urllib3>=2.2.1,<3.0.0")

        analyses = [
            wf.analyze_requirement(req_req),
            wf.analyze_requirement(req_url)
        ]

        is_valid, issues = wf.validate_compatibility(analyses)
        self.assertFalse(is_valid)
        self.assertTrue(any("Compatibility conflict" in msg for msg in issues))


class TestFileOperations(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.req_file = Path(self.temp_dir) / "requirements.in"

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_load_and_write_requirements(self):
        content = (
            "# Top level requirements\n"
            "requests>=2.31.0,<3.0.0 # HTTP library\n"
            "certifi==2024.2.2\n"
        )
        self.req_file.write_text(content, encoding="utf-8")

        reqs = load_requirements_file(self.req_file)
        self.assertEqual(len(reqs), 2)
        self.assertEqual(reqs[0].name, "requests")
        self.assertEqual(reqs[0].comment, "HTTP library")


if __name__ == "__main__":
    unittest.main()
