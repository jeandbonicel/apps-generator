"""Naming convention utilities for template variable transformation."""

import re


def to_words(s: str) -> list[str]:
    """Split a string into words, handling kebab-case, snake_case, camelCase, PascalCase."""
    # Replace hyphens and underscores with spaces
    s = s.replace("-", " ").replace("_", " ")
    # Insert space before uppercase letters in camelCase/PascalCase
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    return [w for w in s.split() if w]


def camel_case(s: str) -> str:
    """Convert to camelCase: 'order-service' -> 'orderService'."""
    words = to_words(s)
    if not words:
        return ""
    return words[0].lower() + "".join(w.capitalize() for w in words[1:])


def pascal_case(s: str) -> str:
    """Convert to PascalCase: 'order-service' -> 'OrderService'."""
    return "".join(w.capitalize() for w in to_words(s))


def snake_case(s: str) -> str:
    """Convert to snake_case: 'order-service' -> 'order_service'."""
    return "_".join(w.lower() for w in to_words(s))


def kebab_case(s: str) -> str:
    """Convert to kebab-case: 'OrderService' -> 'order-service'."""
    return "-".join(w.lower() for w in to_words(s))


def upper_snake_case(s: str) -> str:
    """Convert to UPPER_SNAKE_CASE: 'order-service' -> 'ORDER_SERVICE'."""
    return "_".join(w.upper() for w in to_words(s))


def package_to_path(s: str) -> str:
    """Convert Java package to path: 'com.example.app' -> 'com/example/app'."""
    return s.replace(".", "/")


def capitalize_first(s: str) -> str:
    """Capitalize first letter: 'hello' -> 'Hello'."""
    if not s:
        return ""
    return s[0].upper() + s[1:]


def title_case(s: str) -> str:
    """Convert to Title Case: 'order-service' -> 'Order Service'."""
    return " ".join(w.capitalize() for w in to_words(s))
