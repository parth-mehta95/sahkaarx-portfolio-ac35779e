#!/usr/bin/env python3
"""Automated test runner executing the API validation and DI test suite."""

import os
import sys
import unittest

# Ensure src and tests directories are accessible
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
sys.path.insert(0, BASE_DIR)

import datapipeline
from datapipeline.api.app import PipelineApp
from datapipeline.api.client import PipelineClient
from datapipeline.di.container import Container, Scope, CircularDependencyError, inject, set_default_container
from datapipeline.di.interfaces import IStorageService, IAuthService, IMetricsCollector, IDataTransformer, INotificationService
from datapipeline.di.providers import (
    InMemoryStorageService,
    HmacAuthService,
    InMemoryMetricsCollector,
    StandardDataTransformer,
    ConsoleNotificationService,
)
from datapipeline.services.pipeline_service import PipelineService
from datapipeline.services.auth_service import AuthService


class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.container = Container()
        self.container.register_singleton(IStorageService, InMemoryStorageService)
        self.container.register_singleton(IAuthService, HmacAuthService)
        self.container.register_singleton(IMetricsCollector, InMemoryMetricsCollector)
        self.container.register_singleton(IDataTransformer, StandardDataTransformer)
        self.container.register_singleton(INotificationService, ConsoleNotificationService)
        self.container.register_singleton(PipelineService)
        self.container.register_singleton(AuthService)

        self.app = PipelineApp(self.container)
        self.client = PipelineClient(self.app)

        # Obtain valid token
        status, _, body = self.app.handle_request(
            "POST",
            "/api/v1/auth/token",
            body={"client_id": "admin-client", "client_secret": "secret-admin-token-key-prod-99"},
        )
        self.assertEqual(status, 200)
        self.token = body["data"]["access_token"]
        self.auth_headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def test_health_check(self):
        status, headers, body = self.app.handle_request("GET", "/api/v1/health")
        self.assertEqual(status, 200)
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["status"], "healthy")
        self.assertEqual(body["data"]["version"], "1.0.0")

    def test_auth_invalid_credentials(self):
        status, _, body = self.app.handle_request(
            "POST",
            "/api/v1/auth/token",
            body={"client_id": "admin-client", "client_secret": "invalid"},
        )
        self.assertEqual(status, 401)
        self.assertFalse(body["success"])

    def test_auth_missing_credentials(self):
        status, _, body = self.app.handle_request("POST", "/api/v1/auth/token", body={})
        self.assertEqual(status, 400)
        self.assertFalse(body["success"])

    def test_pipeline_crud_and_execution(self):
        # 1. Create pipeline
        pipe_payload = {
            "pipeline_id": "prod-etl-01",
            "name": "Production ETL Pipeline",
            "transform_operations": ["strip_whitespace", "lowercase_keys", "hash_pii"],
        }
        status, _, body = self.app.handle_request("POST", "/api/v1/pipelines", headers=self.auth_headers, body=pipe_payload)
        self.assertEqual(status, 201)
        self.assertTrue(body["success"])

        # 2. Get pipeline
        status, _, body = self.app.handle_request("GET", "/api/v1/pipelines/prod-etl-01", headers=self.auth_headers)
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["name"], "Production ETL Pipeline")

        # 3. List pipelines
        status, _, body = self.app.handle_request("GET", "/api/v1/pipelines", headers=self.auth_headers)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(body["data"]), 1)

        # 4. Run pipeline
        records = [
            {"Name": " John Smith ", "Email": "john.smith@domain.com"},
            {"Name": "  Sarah Connor  ", "Email": "sarah@domain.com"},
        ]
        status, _, body = self.app.handle_request(
            "POST",
            "/api/v1/pipelines/prod-etl-01/run",
            headers=self.auth_headers,
            body={"records": records},
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["success"])
        output = body["data"]["output"]
        self.assertEqual(len(output), 2)
        self.assertEqual(output[0]["name"], "John Smith")
        self.assertIn("email_hash", output[0])
        self.assertNotIn("Email", output[0])

    def test_dataset_validation(self):
        valid_dataset = {
            "dataset_id": "dataset-batch-99",
            "records": [{"colA": 100, "colB": "test"}],
        }
        status, _, body = self.app.handle_request("POST", "/api/v1/datasets/validate", headers=self.auth_headers, body=valid_dataset)
        self.assertEqual(status, 200)
        self.assertTrue(body["success"])

        invalid_dataset = {
            "dataset_id": "empty",
            "records": [],
        }
        status, _, body = self.app.handle_request("POST", "/api/v1/datasets/validate", headers=self.auth_headers, body=invalid_dataset)
        self.assertEqual(status, 422)

    def test_metrics_endpoint(self):
        status, _, body = self.app.handle_request("GET", "/api/v1/metrics")
        self.assertEqual(status, 200)
        self.assertIn("counters", body["data"])


class TestDependencyInjectionSuite(unittest.TestCase):
    def test_singleton_lifetime(self):
        container = Container()
        container.register_singleton(InMemoryStorageService)
        inst1 = container.resolve(InMemoryStorageService)
        inst2 = container.resolve(InMemoryStorageService)
        self.assertIs(inst1, inst2)

    def test_transient_lifetime(self):
        container = Container()
        container.register_transient(InMemoryStorageService)
        inst1 = container.resolve(InMemoryStorageService)
        inst2 = container.resolve(InMemoryStorageService)
        self.assertIsNot(inst1, inst2)

    def test_circular_dependency(self):
        class NodeA:
            def __init__(self, b: "NodeB"):
                self.b = b

        class NodeB:
            def __init__(self, a: NodeA):
                self.a = a

        container = Container()
        container.register_transient(NodeA)
        container.register_transient(NodeB)

        with self.assertRaises(CircularDependencyError):
            container.resolve(NodeA)


def main():
    print("=" * 70)
    print("   RUNNING SECURE DATA PIPELINE TEST SUITE")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestAPIEndpoints))
    suite.addTests(loader.loadTestsFromTestCase(TestDependencyInjectionSuite))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print(f"Tests Run: {result.testsRun} | Failures: {len(result.failures)} | Errors: {len(result.errors)}")
    if result.wasSuccessful():
        print("ALL TESTS PASSED SUCCESSFULLY! (100% PASS RATE)")
        print("=" * 70)
        return 0
    else:
        print("TEST SUITE FAILED!")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
