"""Tests for the Jinja2 template engine."""

from apps_generator.core.engine import create_jinja_env, render_filename


def test_render_filename_simple():
    env = create_jinja_env()
    ctx = {"projectName": "order-service"}
    assert render_filename("__projectName__", env, ctx) == "order-service"


def test_render_filename_with_filter():
    env = create_jinja_env()
    ctx = {"projectName": "order-service"}
    assert render_filename("__projectName|pascal_case__Application.java", env, ctx) == "OrderServiceApplication.java"


def test_render_filename_package_to_path():
    env = create_jinja_env()
    ctx = {"basePackage": "com.example.orders"}
    assert render_filename("__basePackage|package_to_path__", env, ctx) == "com/example/orders"


def test_render_filename_no_vars():
    env = create_jinja_env()
    assert render_filename("README.md", env, {}) == "README.md"
