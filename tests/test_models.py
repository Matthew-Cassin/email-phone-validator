"""Tests for email_phone_validator.models."""

import dataclasses

import pytest

from email_phone_validator.models import ValidationError, ValidationResult


class TestValidationResult:
    """Tests for the ValidationResult dataclass."""

    def test_minimal_construction_applies_defaults(self):
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.formatted is None
        assert result.errors == []
        assert result.details == {}

    def test_full_construction_keeps_all_fields(self):
        result = ValidationResult(
            is_valid=False,
            formatted=None,
            errors=["bad format"],
            details={"domain": "example.com"},
        )
        assert result.is_valid is False
        assert result.errors == ["bad format"]
        assert result.details == {"domain": "example.com"}

    def test_default_errors_list_not_shared_between_instances(self):
        first = ValidationResult(is_valid=True)
        second = ValidationResult(is_valid=True)
        first.errors.append("oops")
        assert second.errors == []

    def test_default_details_dict_not_shared_between_instances(self):
        first = ValidationResult(is_valid=True)
        second = ValidationResult(is_valid=True)
        first.details["x"] = 1
        assert second.details == {}

    def test_equal_field_values_compare_equal(self):
        first = ValidationResult(is_valid=True, formatted="x@example.com")
        second = ValidationResult(is_valid=True, formatted="x@example.com")
        assert first == second

    def test_is_a_dataclass_with_the_documented_fields(self):
        field_names = {f.name for f in dataclasses.fields(ValidationResult)}
        assert field_names == {"is_valid", "formatted", "errors", "details"}


class TestValidationError:
    """Tests for the ValidationError exception type."""

    def test_is_an_exception_subclass(self):
        assert issubclass(ValidationError, Exception)

    def test_raises_and_preserves_message(self):
        with pytest.raises(ValidationError, match="boom"):
            raise ValidationError("boom")

    def test_catchable_as_plain_exception(self):
        with pytest.raises(Exception):
            raise ValidationError("boom")
