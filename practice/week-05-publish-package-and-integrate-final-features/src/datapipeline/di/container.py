"""Dependency Injection Container implementation.

Provides an enterprise-grade Inversion of Control (IoC) container supporting:
- Lifetime scopes (Singleton, Transient, Scoped)
- Type-hint and name-based dependency resolution
- Decorator-based parameter injection (@inject)
- Circular dependency detection
- Child containers for test mocking and lifecycle isolation
"""

import functools
import inspect
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union, get_type_hints

T = TypeVar("T")


class Scope(Enum):
    """Lifecycle scopes for registered dependencies."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class CircularDependencyError(Exception):
    """Raised when a circular reference is encountered during resolution."""
    pass


class DependencyResolutionError(Exception):
    """Raised when a required dependency cannot be satisfied."""
    pass


class Provider:
    """Wrapper encapsulating dependency creation logic and lifecycle management."""

    def __init__(
        self,
        factory_or_cls: Union[Type, Callable[..., Any]],
        scope: Scope = Scope.SINGLETON,
        instance: Optional[Any] = None,
    ):
        self.factory_or_cls = factory_or_cls
        self.scope = scope
        self.instance = instance

    def resolve(self, container: "Container") -> Any:
        if self.scope == Scope.SINGLETON:
            if self.instance is None:
                self.instance = container._instantiate(self.factory_or_cls)
            return self.instance
        elif self.scope == Scope.TRANSIENT:
            return container._instantiate(self.factory_or_cls)
        elif self.scope == Scope.SCOPED:
            # Managed at container-scoped dictionary level
            return container._instantiate(self.factory_or_cls)
        raise DependencyResolutionError(f"Unsupported scope: {self.scope}")


class Container:
    """Inversion of Control (IoC) Container."""

    def __init__(self, parent: Optional["Container"] = None):
        self._providers: Dict[Any, Provider] = {}
        self._scoped_instances: Dict[Any, Any] = {}
        self._resolution_chain: List[Any] = []
        self._parent = parent

    def register_singleton(
        self,
        service_type: Any,
        implementation: Optional[Union[Type, Callable[..., Any], Any]] = None,
    ) -> "Container":
        """Register a service with Singleton lifetime (one shared instance)."""
        target = implementation if implementation is not None else service_type
        if not callable(target) and not isinstance(target, type):
            # Pre-instantiated object passed
            self._providers[service_type] = Provider(lambda: target, Scope.SINGLETON, instance=target)
        else:
            self._providers[service_type] = Provider(target, Scope.SINGLETON)
        return self

    def register_transient(
        self,
        service_type: Any,
        implementation: Optional[Union[Type, Callable[..., Any]]] = None,
    ) -> "Container":
        """Register a service with Transient lifetime (fresh instance per resolution)."""
        target = implementation if implementation is not None else service_type
        self._providers[service_type] = Provider(target, Scope.TRANSIENT)
        return self

    def register_scoped(
        self,
        service_type: Any,
        implementation: Optional[Union[Type, Callable[..., Any]]] = None,
    ) -> "Container":
        """Register a service with Scoped lifetime (one instance per child container)."""
        target = implementation if implementation is not None else service_type
        self._providers[service_type] = Provider(target, Scope.SCOPED)
        return self

    def register_instance(self, service_type: Any, instance: Any) -> "Container":
        """Register an existing instantiated object directly."""
        self._providers[service_type] = Provider(lambda: instance, Scope.SINGLETON, instance=instance)
        return self

    def has(self, service_type: Any) -> bool:
        """Check if service type is registered in this container or its parent."""
        if service_type in self._providers:
            return True
        if self._parent is not None:
            return self._parent.has(service_type)
        return False

    def resolve(self, service_type: Any) -> Any:
        """Resolve an instance for the requested service type or key."""
        if service_type in self._resolution_chain:
            chain = " -> ".join(str(s) for s in self._resolution_chain + [service_type])
            raise CircularDependencyError(f"Circular dependency detected: {chain}")

        provider = self._providers.get(service_type)
        if provider is None and self._parent is not None:
            return self._parent.resolve(service_type)

        if provider is None:
            # If it's a concrete class, attempt auto-wiring
            if isinstance(service_type, type) and not inspect.isabstract(service_type):
                return self._instantiate(service_type)
            raise DependencyResolutionError(f"No provider registered for {service_type}")

        if provider.scope == Scope.SCOPED:
            if service_type not in self._scoped_instances:
                self._resolution_chain.append(service_type)
                try:
                    self._scoped_instances[service_type] = provider.resolve(self)
                finally:
                    self._resolution_chain.pop()
            return self._scoped_instances[service_type]

        self._resolution_chain.append(service_type)
        try:
            return provider.resolve(self)
        finally:
            self._resolution_chain.pop()

    def _instantiate(self, target: Union[Type, Callable[..., Any]]) -> Any:
        """Inspect dependencies of callable/constructor and resolve each parameter."""
        if not callable(target) and not isinstance(target, type):
            return target

        try:
            # If it's a class, inspect __init__
            fn = target.__init__ if isinstance(target, type) else target
            sig = inspect.signature(fn)
        except (ValueError, TypeError):
            return target()

        try:
            type_hints = get_type_hints(fn) if inspect.isfunction(fn) or inspect.ismethod(fn) else {}
        except Exception:
            type_hints = {}

        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            # Skip *args or **kwargs
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue

            param_type = type_hints.get(param_name, param.annotation)
            
            # Check if registered by type hint
            if param_type is not inspect.Parameter.empty and self.has(param_type):
                kwargs[param_name] = self.resolve(param_type)
            # Check if registered by parameter name
            elif self.has(param_name):
                kwargs[param_name] = self.resolve(param_name)
            # Check if parameter has default value
            elif param.default is not inspect.Parameter.empty:
                kwargs[param_name] = param.default
            # If type is a concrete class, try auto-wiring
            elif isinstance(param_type, type) and not inspect.isabstract(param_type):
                kwargs[param_name] = self.resolve(param_type)
            else:
                raise DependencyResolutionError(
                    f"Cannot resolve parameter '{param_name}' of type {param_type} for {target}"
                )

        return target(**kwargs)

    def create_child_container(self) -> "Container":
        """Create an isolated child container inheriting parent registrations."""
        return Container(parent=self)

    def clear(self) -> None:
        """Clear all registered providers and cache."""
        self._providers.clear()
        self._scoped_instances.clear()
        self._resolution_chain.clear()


# Global default container instance
_DEFAULT_CONTAINER: Optional[Container] = None


def get_default_container() -> Container:
    """Retrieve or initialize the global container singleton."""
    global _DEFAULT_CONTAINER
    if _DEFAULT_CONTAINER is None:
        _DEFAULT_CONTAINER = Container()
    return _DEFAULT_CONTAINER


def set_default_container(container: Container) -> None:
    """Set the active global container."""
    global _DEFAULT_CONTAINER
    _DEFAULT_CONTAINER = container


def inject(container_override: Optional[Container] = None):
    """Decorator to inject parameters into functions or methods via container."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            container = container_override or get_default_container()
            sig = inspect.signature(func)
            bound_args = sig.bind_partial(*args, **kwargs)
            
            try:
                type_hints = get_type_hints(func)
            except Exception:
                type_hints = {}

            injected_kwargs = dict(kwargs)
            for param_name, param in sig.parameters.items():
                if param_name in bound_args.arguments:
                    continue
                if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                    continue

                param_type = type_hints.get(param_name, param.annotation)
                if param_type is not inspect.Parameter.empty and container.has(param_type):
                    injected_kwargs[param_name] = container.resolve(param_type)
                elif container.has(param_name):
                    injected_kwargs[param_name] = container.resolve(param_name)
                elif param.default is not inspect.Parameter.empty:
                    injected_kwargs[param_name] = param.default

            return func(*args, **injected_kwargs)
        return wrapper
    return decorator
