"""Generation context model — holds all parameters for template rendering."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GenerationContext(BaseModel):
    """All parameters available during template rendering.

    Includes user-provided params, defaults, derived variants, and feature flags.
    """

    params: dict[str, Any] = Field(default_factory=dict)
    features: dict[str, bool] = Field(default_factory=dict)

    def as_template_vars(self) -> dict[str, Any]:
        """Return a flat dict suitable for Jinja2 rendering."""
        result = dict(self.params)
        result["features"] = self.features
        return result
