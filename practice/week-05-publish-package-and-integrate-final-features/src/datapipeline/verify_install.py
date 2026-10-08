"""Runtime verification script to validate installation, DI container, and API functionality."""

import sys
import time

def verify_installation() -> bool:
    print("=" * 60)
    print("   SECURE DATA PIPELINE - INSTALLATION VERIFICATION")
    print("=" * 60)

    try:
        import datapipeline
        print(f"[OK] Package imported successfully (v{datapipeline.__version__})")
    except ImportError as e:
        print(f"[FAIL] Could not import datapipeline: {e}")
        return False

    # Test Dependency Injection Container
    try:
        container = datapipeline.Container()
        container.register_singleton(datapipeline.IStorageService, datapipeline.di.providers.InMemoryStorageService)
        container.register_singleton(datapipeline.IAuthService, datapipeline.di.providers.HmacAuthService)
        container.register_singleton(datapipeline.IMetricsCollector, datapipeline.di.providers.InMemoryMetricsCollector)
        container.register_singleton(datapipeline.IDataTransformer, datapipeline.di.providers.StandardDataTransformer)
        container.register_singleton(datapipeline.INotificationService, datapipeline.di.providers.ConsoleNotificationService)
        container.register_singleton(datapipeline.PipelineService)
        container.register_singleton(datapipeline.AuthService)

        pipe_svc = container.resolve(datapipeline.PipelineService)
        assert pipe_svc is not None
        print("[OK] Dependency Injection container wiring and resolution validated")
    except Exception as e:
        print(f"[FAIL] Dependency Injection verification failed: {e}")
        return False

    # Test API Application
    try:
        app = datapipeline.PipelineApp(container)
        status, _, body = app.handle_request("GET", "/api/v1/health")
        assert status == 200, f"Expected 200 health status, got {status}"
        assert body["data"]["status"] == "healthy"
        print("[OK] Health endpoint (/api/v1/health) validated")
    except Exception as e:
        print(f"[FAIL] Health endpoint check failed: {e}")
        return False

    # Test Authentication API
    try:
        status, _, body = app.handle_request(
            "POST",
            "/api/v1/auth/token",
            body={"client_id": "admin-client", "client_secret": "secret-admin-token-key-prod-99"},
        )
        assert status == 200
        token = body["data"]["access_token"]
        assert token.startswith("dpt_")
        print("[OK] Authentication endpoint (/api/v1/auth/token) validated")
    except Exception as e:
        print(f"[FAIL] Auth endpoint check failed: {e}")
        return False

    # Test Pipeline CRUD and Execution
    try:
        headers = {"Authorization": f"Bearer {token}"}
        status, _, body = app.handle_request(
            "POST",
            "/api/v1/pipelines",
            headers=headers,
            body={
                "pipeline_id": "verify-pipeline-01",
                "name": "Verification Pipeline",
                "transform_operations": ["strip_whitespace", "lowercase_keys", "hash_pii"],
            },
        )
        assert status == 201
        print("[OK] Pipeline registration (/api/v1/pipelines) validated")

        status, _, body = app.handle_request(
            "POST",
            "/api/v1/pipelines/verify-pipeline-01/run",
            headers=headers,
            body={
                "records": [
                    {"User": " Alice ", "Email": "alice@example.com"},
                    {"User": " Bob ", "Email": "bob@example.com"},
                ]
            },
        )
        assert status == 200
        assert body["data"]["records_out"] == 2
        print("[OK] Pipeline execution (/api/v1/pipelines/{id}/run) validated")
    except Exception as e:
        print(f"[FAIL] Pipeline execution check failed: {e}")
        return False

    print("=" * 60)
    print("   ALL VERIFICATION CHECKS PASSED: PACKAGE PRODUCTION READY")
    print("=" * 60)
    return True


def main():
    success = verify_installation()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
