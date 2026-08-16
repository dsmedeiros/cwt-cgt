"""Metadata-only design template for a future external active-loop study.

This package intentionally contains no outcome loader, response reducer, or
confirmation command.  It can validate and freeze design metadata only.
"""

from .template_model import TemplateState, validate_template

__all__ = ["TemplateState", "validate_template"]
