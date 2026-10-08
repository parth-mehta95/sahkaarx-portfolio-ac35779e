"""Unit tests for Dependency Injection Container and patterns."""

import pytest
from datapipeline.di.container import (
    CircularDependencyError,
    Container,
    DependencyResolutionError,
    Scope,
    inject,
    set_default_container,
)
from datapipeline.di.interfaces import IStorageService, INotificationService
from datapipeline.di.providers import InMemoryStorageService, ConsoleNotificationService


class ServiceA:
    def __init__(self, service_b: "ServiceB"):
        self.service_b = service_b


class ServiceB:
    def __init__(self, service_a: ServiceA):
        self.service_a = service_a


class DatabaseConnection:
    pass


class UserRepository:
    def __init__(self, db: DatabaseConnection):
        self.db = db


class MockStorageService(IStorageService):
    def __init__(self):
        self.mock_called = True

    def save(self, collection, item_id, data):
        return {"id": item_id, "mock": True}

    def get(self, collection, item_id):
        return {"id": item_id, "mock": True}

    def list(self, collection):
        return []

    def delete(self, collection, item_id):
        return True


class TestDependencyInjection:
    """Test suite for IoC container functionality."""

    def test_singleton_scope(self):
        container = Container()
        container.register_singleton(DatabaseConnection)
        
        instance1 = container.resolve(DatabaseConnection)
        instance2 = container.resolve(DatabaseConnection)
        assert instance1 is instance2

    def test_transient_scope(self):
        container = Container()
        container.register_transient(DatabaseConnection)
        
        instance1 = container.resolve(DatabaseConnection)
        instance2 = container.resolve(DatabaseConnection)
        assert instance1 is not instance2
        assert isinstance(instance1, DatabaseConnection)
        assert isinstance(instance2, DatabaseConnection)

    def test_auto_wiring_dependencies(self):
        container = Container()
        container.register_singleton(DatabaseConnection)
        container.register_singleton(UserRepository)

        repo = container.resolve(UserRepository)
        assert isinstance(repo, UserRepository)
        assert isinstance(repo.db, DatabaseConnection)

    def test_circular_dependency_detection(self):
        container = Container()
        container.register_transient(ServiceA)
        container.register_transient(ServiceB)

        with pytest.raises(CircularDependencyError) as exc_info:
            container.resolve(ServiceA)
        assert "Circular dependency detected" in str(exc_info.value)

    def test_unregistered_dependency_raises_error(self):
        container = Container()
        with pytest.raises(DependencyResolutionError):
            container.resolve("NonExistentService")

    def test_child_container_mock_override(self):
        parent = Container()
        parent.register_singleton(IStorageService, InMemoryStorageService)

        child = parent.create_child_container()
        child.register_singleton(IStorageService, MockStorageService)

        parent_storage = parent.resolve(IStorageService)
        child_storage = child.resolve(IStorageService)

        assert isinstance(parent_storage, InMemoryStorageService)
        assert isinstance(child_storage, MockStorageService)
        assert getattr(child_storage, "mock_called", False) is True

    def test_inject_decorator(self):
        container = Container()
        container.register_singleton(IStorageService, InMemoryStorageService)
        set_default_container(container)

        @inject()
        def perform_operation(name: str, storage: IStorageService):
            return f"Saved {name} using {storage.__class__.__name__}"

        result = perform_operation(name="test_record")
        assert "Saved test_record using InMemoryStorageService" in result
