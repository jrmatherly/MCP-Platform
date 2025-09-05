"""
Integration tests for the Trino template.

These are focused, well-indented tests that assert the template.json and
supporting files use the canonical values required by the platform. The file
is intentionally small and authoritative: the template itself is the source of
truth and tests must reflect its canonical values.
"""

import json
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def template_dir() -> Path:
    return Path(__file__).parent.parent


def load_template(template_dir: Path) -> dict:
    path = template_dir / "template.json"
    with open(path, "r") as f:
        return json.load(f)


def test_template_required_fields(template_dir):
    data = load_template(template_dir)

    required = [
        "id",
        "name",
        "description",
        "version",
        "category",
        "docker_image",
        "docker_tag",
        "ports",
        "transport",
        "config_schema",
        "tools",
        "examples",
    ]

    for field in required:
        assert field in data, f"Missing required field: {field}"


def test_template_canonical_values(template_dir):
    data = load_template(template_dir)

    assert data["docker_image"] == "dataeverything/mcp-trino"
    assert data["docker_tag"] == "latest"

    transport = data["transport"]
    assert transport["default"] == "http"
    assert transport.get("port", 7090) == 7090
    assert "http" in transport["supported"]


def test_examples_and_http_endpoint(template_dir):
    data = load_template(template_dir)
    examples = data.get("examples", {})

    assert "http_endpoint" in examples
    assert "7090" in examples["http_endpoint"]


def test_config_schema_properties_have_env_mapping(template_dir):
    data = load_template(template_dir)
    props = data["config_schema"]["properties"]

    assert isinstance(props, dict)
    # spot check a few well-known properties
    for key in ("trino_host", "trino_user", "trino_port"):
        assert key in props
        assert "env_mapping" in props[key]


def test_dockerfile_contains_port_and_python(template_dir):
    df = template_dir / "Dockerfile"
    content = df.read_text()

    assert "python:" in content
    # MCP runtime port should be 7090
    assert "7090" in content
