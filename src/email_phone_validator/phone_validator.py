"""International phone number validation via Google's ``phonenumbers`` library."""

from __future__ import annotations

from typing import Any

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat, PhoneNumberType

from .logger import get_logger
from .models import ValidationError, ValidationResult

logger = get_logger("phone_validator")

__all__ = ["PhoneValidator"]

# phonenumbers.PhoneNumberType values are plain integer constants, not a
# real enum, so there's no built-in `.name` to log or report -- this maps
# them to readable strings for ValidationResult.details["carrier_type"].
_NUMBER_TYPE_NAMES: dict[int, str] = {
    PhoneNumberType.FIXED_LINE: "FIXED_LINE",
    PhoneNumberType.MOBILE: "MOBILE",
    PhoneNumberType.FIXED_LINE_OR_MOBILE: "FIXED_LINE_OR_MOBILE",
    PhoneNumberType.TOLL_FREE: "TOLL_FREE",
    PhoneNumberType.PREMIUM_RATE: "PREMIUM_RATE",
    PhoneNumberType.SHARED_COST: "SHARED_COST",
    PhoneNumberType.VOIP: "VOIP",
    PhoneNumberType.PERSONAL_NUMBER: "PERSONAL_NUMBER",
    PhoneNumberType.PAGER: "PAGER",
    PhoneNumberType.UAN: "UAN",
    PhoneNumberType.VOICEMAIL: "VOICEMAIL",
    PhoneNumberType.UNKNOWN: "UNKNOWN",
}

# NANP-style numbers are frequently typed as FIXED_LINE_OR_MOBILE because
# the North American numbering plan doesn't separate the two ranges, so
# treating it as "mobile-ish" gives a more useful is_mobile flag than
# requiring an exact MOBILE match.
_MOBILE_TYPES = (PhoneNumberType.MOBILE, PhoneNumberType.FIXED_LINE_OR_MOBILE)

_PARSE_ERROR_MESSAGES: dict[int, str] = {
    NumberParseException.INVALID_COUNTRY_CODE: "Invalid country",
    NumberParseException.NOT_A_NUMBER: "Invalid format",
    NumberParseException.TOO_SHORT_AFTER_IDD: "Wrong length",
    NumberParseException.TOO_SHORT_NSN: "Wrong length",
    NumberParseException.TOO_LONG: "Wrong length",
}


class PhoneValidator:
    """Validates and formats international phone numbers.

    Wraps Google's ``phonenumbers`` library (a Python port of
    libphonenumber) to parse, validate, and reformat phone numbers to
    E.164, with automatic country detection for numbers that already
    include a ``+`` country-code prefix.

    Args:
        default_country: ISO 3166-1 alpha-2 region code (e.g. ``"US"``,
            ``"GB"``) used to interpret numbers that don't start with
            ``+`` and aren't given an explicit ``country`` at call time.
            Case-insensitive. Defaults to ``"US"``.

    Raises:
        ValidationError: If ``default_country`` is not a region code
            ``phonenumbers`` recognizes.

    Example:
        >>> validator = PhoneValidator(default_country="US")
        >>> result = validator.validate("(415) 858-6273")
        >>> result.formatted
        '+14158586273'
    """

    def __init__(self, default_country: str = "US") -> None:
        region = default_country.upper()
        if region not in phonenumbers.SUPPORTED_REGIONS:
            raise ValidationError(
                f"default_country must be a supported ISO region code, got {default_country!r}"
            )
        self.default_country = region

    def validate(self, phone: str, country: str | None = None) -> ValidationResult:
        """Validate and format a phone number.

        Args:
            phone: The phone number to validate, in any common format
                (e.g. ``"+1-555-555-0123"``, ``"(555) 555-0123"``,
                ``"5555550123"``).
            country: ISO region code to interpret ``phone`` against for
                this call only, overriding :attr:`default_country`.
                Ignored when ``phone`` starts with ``+``, since a leading
                ``+`` already encodes its own country code.

        Returns:
            A :class:`ValidationResult` whose ``formatted`` value is the
            E.164 representation (e.g. ``"+14158586273"``) when valid,
            and whose ``details`` contains:

            * ``country_code`` (Optional[int]): the numeric calling code,
              e.g. ``1``.
            * ``national_number`` (Optional[str]): the number without its
              country code.
            * ``country`` (Optional[str]): the detected/used ISO region
              code, e.g. ``"US"``.
            * ``carrier_type`` (Optional[str]): the line type, e.g.
              ``"MOBILE"``, ``"FIXED_LINE"``, ``"VOIP"``.
            * ``is_mobile`` (Optional[bool]): convenience flag derived
              from ``carrier_type``.

            These ``details`` are populated whenever the number could be
            parsed, even if it then fails validation, so callers can see
            *why* an unsuccessful number looked the way it did.

        Raises:
            ValidationError: If ``phone`` is not a string, or ``country``
                is given but isn't a recognized region code.
        """
        if not isinstance(phone, str):
            raise ValidationError(f"phone must be a string, got {type(phone).__name__}")

        region_hint = self.default_country
        if country is not None:
            region_hint = country.upper()
            if region_hint not in phonenumbers.SUPPORTED_REGIONS:
                raise ValidationError(
                    f"country must be a supported ISO region code, got {country!r}"
                )

        logger.info("Validating phone number against region hint %s", region_hint)

        errors: list[str] = []
        details: dict[str, Any] = {
            "country_code": None,
            "national_number": None,
            "country": None,
            "carrier_type": None,
            "is_mobile": None,
        }

        candidate = phone.strip()
        if not candidate:
            errors.append("Phone number is empty")
            logger.warning("Phone validation failed: empty input")
            return ValidationResult(is_valid=False, formatted=None, errors=errors, details=details)

        # A leading '+' already carries its own country code, so let
        # phonenumbers detect it rather than forcing a region hint.
        parse_region = None if candidate.startswith("+") else region_hint

        try:
            parsed = phonenumbers.parse(candidate, parse_region)
        except NumberParseException as exc:
            message = _PARSE_ERROR_MESSAGES.get(exc.error_type, "Invalid format")
            errors.append(f"{message}: {exc}")
            logger.warning("Phone validation failed: %s", exc)
            return ValidationResult(is_valid=False, formatted=None, errors=errors, details=details)

        details["country_code"] = parsed.country_code
        details["national_number"] = str(parsed.national_number)
        details["country"] = phonenumbers.region_code_for_number(parsed)

        number_type = phonenumbers.number_type(parsed)
        details["carrier_type"] = _NUMBER_TYPE_NAMES.get(number_type, "UNKNOWN")
        details["is_mobile"] = number_type in _MOBILE_TYPES

        if not phonenumbers.is_possible_number(parsed):
            errors.append("Wrong length for a phone number")
        elif not phonenumbers.is_valid_number(parsed):
            errors.append("Invalid phone number for its region")

        is_valid = not errors
        formatted = phonenumbers.format_number(parsed, PhoneNumberFormat.E164) if is_valid else None

        if is_valid:
            logger.info("Phone number validated successfully: %s", formatted)
        else:
            logger.warning("Phone validation failed: %s", "; ".join(errors))

        return ValidationResult(
            is_valid=is_valid, formatted=formatted, errors=errors, details=details
        )
