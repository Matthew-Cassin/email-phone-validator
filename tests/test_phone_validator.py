"""Tests for email_phone_validator.phone_validator."""

import pytest

from email_phone_validator.models import ValidationError, ValidationResult
from email_phone_validator.phone_validator import PhoneValidator


class TestPhoneValidatorValidNumbers:
    """Numbers that should validate successfully, across formats and regions."""

    def test_valid_e164_us_number(self):
        result = PhoneValidator().validate("+14158586273")
        assert result.is_valid is True
        assert result.formatted == "+14158586273"

    @pytest.mark.parametrize(
        "raw",
        ["(415) 858-6273", "415-858-6273", "415.858.6273", "4158586273"],
    )
    def test_valid_us_number_in_various_local_formats(self, raw):
        result = PhoneValidator(default_country="US").validate(raw)
        assert result.is_valid is True
        assert result.formatted == "+14158586273"

    def test_default_country_fallback_when_no_plus_prefix(self):
        result = PhoneValidator(default_country="GB").validate("020 7031 3000")
        assert result.is_valid is True
        assert result.formatted == "+442070313000"
        assert result.details["country"] == "GB"

    def test_explicit_country_param_overrides_default(self):
        validator = PhoneValidator(default_country="US")
        result = validator.validate("020 7031 3000", country="GB")
        assert result.is_valid is True
        assert result.details["country"] == "GB"

    def test_plus_prefix_auto_detects_country_over_default(self):
        validator = PhoneValidator(default_country="US")
        result = validator.validate("+442070313000")
        assert result.is_valid is True
        assert result.details["country"] == "GB"

    def test_formatted_output_is_clean_e164(self):
        result = PhoneValidator().validate("+1 (415) 858-6273")
        assert result.formatted.startswith("+")
        assert " " not in result.formatted
        assert "(" not in result.formatted
        assert "-" not in result.formatted

    def test_number_with_extension_still_validates(self):
        result = PhoneValidator().validate("+1 415-858-6273 ext. 123")
        assert result.is_valid is True
        assert result.formatted == "+14158586273"


class TestPhoneValidatorInvalidNumbers:
    """Numbers that should be rejected, with a reported error."""

    def test_too_short_number(self):
        result = PhoneValidator(default_country="US").validate("555")
        assert result.is_valid is False
        assert result.errors

    def test_unparseable_junk_input(self):
        result = PhoneValidator().validate("@#$%^&*")
        assert result.is_valid is False
        assert result.formatted is None
        assert result.errors

    def test_invalid_number_has_no_formatted_value(self):
        result = PhoneValidator(default_country="US").validate("123")
        assert result.formatted is None


class TestPhoneValidatorEdgeCases:
    """Empty input and non-string input."""

    def test_empty_string(self):
        result = PhoneValidator().validate("")
        assert result.is_valid is False
        assert "empty" in result.errors[0].lower()

    def test_whitespace_only_string(self):
        result = PhoneValidator().validate("    ")
        assert result.is_valid is False

    def test_non_string_none_input_raises_validation_error(self):
        with pytest.raises(ValidationError):
            PhoneValidator().validate(None)  # type: ignore[arg-type]

    def test_non_string_number_input_raises_validation_error(self):
        with pytest.raises(ValidationError):
            PhoneValidator().validate(4158586273)  # type: ignore[arg-type]

    def test_returns_validation_result_instance(self):
        result = PhoneValidator().validate("+14158586273")
        assert isinstance(result, ValidationResult)


class TestPhoneValidatorDetails:
    """The details dict: country_code, national_number, country, carrier_type, is_mobile."""

    def test_country_code_and_national_number(self):
        result = PhoneValidator().validate("+14158586273")
        assert result.details["country_code"] == 1
        assert result.details["national_number"] == "4158586273"

    def test_carrier_type_and_is_mobile_present_for_valid_number(self):
        result = PhoneValidator().validate("+14158586273")
        assert result.details["carrier_type"] is not None
        assert isinstance(result.details["is_mobile"], bool)

    def test_details_populated_even_when_number_is_invalid(self):
        # "555" parses (as a partial NANP number under region US) but is
        # too short to be valid -- country_code should still reflect the
        # region hint even though a definitive region can't be resolved.
        result = PhoneValidator(default_country="US").validate("555")
        assert result.details["country_code"] == 1
        assert result.details["country"] is None

    def test_details_are_all_none_for_empty_input(self):
        result = PhoneValidator().validate("")
        assert result.details == {
            "country_code": None,
            "national_number": None,
            "country": None,
            "carrier_type": None,
            "is_mobile": None,
        }


class TestPhoneValidatorConfiguration:
    """Constructor and per-call region validation."""

    def test_rejects_unsupported_default_country(self):
        with pytest.raises(ValidationError):
            PhoneValidator(default_country="ZZ")

    def test_rejects_unsupported_country_param(self):
        with pytest.raises(ValidationError):
            PhoneValidator().validate("4158586273", country="ZZ")

    def test_default_country_is_stored_uppercased(self):
        validator = PhoneValidator(default_country="us")
        assert validator.default_country == "US"

    def test_default_country_defaults_to_us(self):
        assert PhoneValidator().default_country == "US"
