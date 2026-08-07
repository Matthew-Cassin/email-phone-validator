"""Tests for email_phone_validator.email_validator."""

from unittest.mock import MagicMock, patch

import dns.exception
import dns.resolver
import pytest

from email_phone_validator.email_validator import EmailValidator
from email_phone_validator.models import ValidationError, ValidationResult


class TestEmailValidatorValidFormats:
    """Emails that should validate successfully (check_mx disabled)."""

    def test_standard_email(self):
        result = EmailValidator(check_mx=False).validate("user@example.com")
        assert result.is_valid is True
        assert result.formatted == "user@example.com"
        assert result.errors == []

    def test_email_with_subdomain(self):
        result = EmailValidator(check_mx=False).validate("user@mail.example.co.uk")
        assert result.is_valid is True
        assert result.details["domain"] == "mail.example.co.uk"

    def test_email_with_plus_tag(self):
        result = EmailValidator(check_mx=False).validate("user+newsletter@example.com")
        assert result.is_valid is True

    def test_email_with_new_style_tld(self):
        result = EmailValidator(check_mx=False).validate("hello@example.dev")
        assert result.is_valid is True
        assert result.details["domain"] == "example.dev"

    def test_normalizes_case_and_surrounding_whitespace(self):
        result = EmailValidator(check_mx=False).validate("  User@EXAMPLE.com  ")
        assert result.is_valid is True
        assert result.formatted == "user@example.com"


class TestEmailValidatorInvalidFormats:
    """Malformed emails that should be rejected, with a reported error."""

    def test_missing_at_symbol(self):
        result = EmailValidator(check_mx=False).validate("userexample.com")
        assert result.is_valid is False
        assert result.errors

    def test_multiple_at_symbols(self):
        result = EmailValidator(check_mx=False).validate("user@@example.com")
        assert result.is_valid is False

    def test_contains_spaces(self):
        result = EmailValidator(check_mx=False).validate("user name@example.com")
        assert result.is_valid is False

    def test_special_characters_after_address(self):
        result = EmailValidator(check_mx=False).validate("user<>@example.com")
        assert result.is_valid is False

    def test_empty_local_part(self):
        result = EmailValidator(check_mx=False).validate("@example.com")
        assert result.is_valid is False

    def test_malformed_domain_double_dot(self):
        result = EmailValidator(check_mx=False).validate("user@example..com")
        assert result.is_valid is False

    def test_invalid_email_has_no_formatted_value(self):
        result = EmailValidator(check_mx=False).validate("not-an-email")
        assert result.formatted is None


class TestEmailValidatorEdgeCases:
    """Empty input, very long input, and unicode input."""

    def test_empty_string(self):
        result = EmailValidator(check_mx=False).validate("")
        assert result.is_valid is False
        assert "empty" in result.errors[0].lower()

    def test_whitespace_only_string(self):
        result = EmailValidator(check_mx=False).validate("   ")
        assert result.is_valid is False

    def test_extremely_long_email_is_invalid(self):
        # RFC 5321 caps the full address at 254 octets; comfortably
        # exceed that rather than sit near the boundary.
        local_part = "a" * 254
        result = EmailValidator(check_mx=False).validate(f"{local_part}@example.com")
        assert result.is_valid is False
        assert result.errors

    def test_non_string_input_raises_validation_error(self):
        with pytest.raises(ValidationError):
            EmailValidator(check_mx=False).validate(None)  # type: ignore[arg-type]

    def test_non_string_number_input_raises_validation_error(self):
        with pytest.raises(ValidationError):
            EmailValidator(check_mx=False).validate(12345)  # type: ignore[arg-type]

    def test_unicode_local_part_is_valid_and_preserved(self):
        result = EmailValidator(check_mx=False).validate("josé@example.com")
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.formatted == "josé@example.com"


class TestEmailValidatorMxChecking:
    """MX lookups, mocked so tests don't depend on network access."""

    def test_mx_valid_when_records_found(self):
        validator = EmailValidator(check_mx=True, timeout=1)
        fake_answers = [MagicMock()]
        with patch.object(dns.resolver.Resolver, "resolve", return_value=fake_answers):
            result = validator.validate("user@example.com")
        assert result.is_valid is True
        assert result.details["mx_valid"] is True

    def test_mx_invalid_on_nxdomain(self):
        validator = EmailValidator(check_mx=True, timeout=1)
        with patch.object(dns.resolver.Resolver, "resolve", side_effect=dns.resolver.NXDOMAIN()):
            result = validator.validate("user@example-domain-that-does-not-exist.com")
        assert result.is_valid is False
        assert result.details["mx_valid"] is False
        assert result.errors

    def test_mx_invalid_when_no_records(self):
        validator = EmailValidator(check_mx=True, timeout=1)
        with patch.object(dns.resolver.Resolver, "resolve", side_effect=dns.resolver.NoAnswer()):
            result = validator.validate("user@example.com")
        assert result.is_valid is False
        assert result.details["mx_valid"] is False
        assert "MX records not found" in result.errors

    def test_mx_check_times_out_gracefully(self):
        validator = EmailValidator(check_mx=True, timeout=1)
        with patch.object(dns.resolver.Resolver, "resolve", side_effect=dns.exception.Timeout()):
            result = validator.validate("user@example.com")
        assert result.is_valid is False
        assert any("timed out" in e.lower() for e in result.errors)

    def test_mx_check_skipped_when_disabled(self):
        validator = EmailValidator(check_mx=False)
        with patch.object(dns.resolver.Resolver, "resolve") as mock_resolve:
            result = validator.validate("user@example.com")
        mock_resolve.assert_not_called()
        assert result.details["mx_valid"] is None
        assert result.is_valid is True


class TestEmailValidatorConfiguration:
    """Constructor validation."""

    def test_rejects_zero_timeout(self):
        with pytest.raises(ValidationError):
            EmailValidator(timeout=0)

    def test_rejects_negative_timeout(self):
        with pytest.raises(ValidationError):
            EmailValidator(timeout=-1)

    def test_accepts_check_mx_disabled_by_default_settings(self):
        validator = EmailValidator(check_mx=False)
        assert validator.check_mx is False
        assert validator.timeout == 5


class TestEmailValidatorSuggestions:
    """Domain typo suggestions in details['suggestions']."""

    def test_suggests_close_common_domain(self):
        result = EmailValidator(check_mx=False).validate("user@gmial.com")
        assert result.details["suggestions"] == ["gmail.com"]

    def test_no_suggestion_for_already_common_domain(self):
        result = EmailValidator(check_mx=False).validate("user@gmail.com")
        assert result.details["suggestions"] is None

    def test_no_suggestion_for_unrelated_domain(self):
        result = EmailValidator(check_mx=False).validate("user@my-own-company-domain.io")
        assert result.details["suggestions"] is None
