"""Tests for naming utilities."""

from apps_generator.utils.naming import (
    camel_case,
    kebab_case,
    package_to_path,
    pascal_case,
    snake_case,
    title_case,
    upper_snake_case,
)


def test_camel_case():
    assert camel_case("order-service") == "orderService"
    assert camel_case("my_cool_app") == "myCoolApp"
    assert camel_case("OrderService") == "orderService"


def test_pascal_case():
    assert pascal_case("order-service") == "OrderService"
    assert pascal_case("my_cool_app") == "MyCoolApp"


def test_snake_case():
    assert snake_case("order-service") == "order_service"
    assert snake_case("OrderService") == "order_service"


def test_kebab_case():
    assert kebab_case("OrderService") == "order-service"
    assert kebab_case("my_cool_app") == "my-cool-app"


def test_upper_snake_case():
    assert upper_snake_case("order-service") == "ORDER_SERVICE"


def test_package_to_path():
    assert package_to_path("com.example.app") == "com/example/app"


def test_title_case():
    assert title_case("order-service") == "Order Service"
