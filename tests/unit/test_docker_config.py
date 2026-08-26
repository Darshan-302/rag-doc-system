"""Test Docker Compose configuration."""

import yaml
import pytest


@pytest.fixture
def docker_compose_config():
    """Load docker-compose.yml"""
    with open("docker-compose.yml", "r") as f:
        return yaml.safe_load(f)


def test_docker_compose_is_valid_yaml(docker_compose_config):
    """Test that docker-compose.yml is valid YAML."""
    assert docker_compose_config is not None
    assert "services" in docker_compose_config


def test_all_services_have_memory_limits(docker_compose_config):
    """Test that all services have memory limits defined."""
    services = docker_compose_config["services"]

    # Services that should have memory limits
    critical_services = ["ollama", "weaviate", "postgres", "redis", "minio"]

    for service_name in critical_services:
        assert service_name in services, f"Service {service_name} not found"
        service = services[service_name]
        assert "resources" in service, f"Service {service_name} has no resources defined"
        assert "limits" in service["resources"], f"Service {service_name} has no memory limit"
        assert "memory" in service["resources"]["limits"], f"Service {service_name} has no memory limit specified"


def test_ollama_has_gpu_support(docker_compose_config):
    """Test that Ollama has GPU device support configured."""
    ollama = docker_compose_config["services"]["ollama"]

    # Check for deploy section with GPU device
    assert "deploy" in ollama, "Ollama missing deploy section"
    assert "resources" in ollama["deploy"], "Ollama deploy missing resources"
    assert "reservations" in ollama["deploy"]["resources"], "Ollama deploy missing reservations"
    assert "devices" in ollama["deploy"]["resources"]["reservations"], "Ollama missing device definitions"


def test_ollama_has_sufficient_memory(docker_compose_config):
    """Test that Ollama has sufficient memory allocation."""
    ollama = docker_compose_config["services"]["ollama"]
    memory_limit = ollama["resources"]["limits"]["memory"]

    # Parse memory value (e.g., "32G" -> 32)
    memory_gb = int(memory_limit.rstrip("G"))

    assert memory_gb >= 16, f"Ollama memory limit {memory_gb}G is too low (minimum 16G for 7B models)"


def test_weaviate_has_sufficient_memory(docker_compose_config):
    """Test that Weaviate has sufficient memory allocation."""
    weaviate = docker_compose_config["services"]["weaviate"]
    memory_limit = weaviate["resources"]["limits"]["memory"]
    memory_gb = int(memory_limit.rstrip("G"))

    assert memory_gb >= 2, f"Weaviate memory limit {memory_gb}G is too low"


def test_services_have_reservations(docker_compose_config):
    """Test that services have memory reservations."""
    services = docker_compose_config["services"]

    for service_name in ["postgres", "redis", "weaviate", "minio"]:
        service = services[service_name]
        assert "reservations" in service["resources"], f"{service_name} missing reservations"
        assert "memory" in service["resources"]["reservations"], f"{service_name} missing memory reservation"


def test_cpu_limits_defined(docker_compose_config):
    """Test that CPU limits are defined for services."""
    services = docker_compose_config["services"]

    for service_name in ["ollama", "postgres", "redis", "weaviate"]:
        service = services[service_name]
        assert "cpus" in service["resources"]["limits"], f"{service_name} missing CPU limit"
        assert "cpus" in service["resources"]["reservations"], f"{service_name} missing CPU reservation"
