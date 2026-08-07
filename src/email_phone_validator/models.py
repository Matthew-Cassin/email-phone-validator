"""Core data structures shared by every validator in this package.

Both :class:`~email_phone_validator.email_validator.EmailValidator` and
:class:`~email_phone_validator.phone_validator.PhoneValidator` return the
same :class:`ValidationResult` shape, so callers can handle either kind of
input with identical code. :class:`ValidationError` is the single
exception type the package raises.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

__all__ = ["ValidationResult", "ValidationError"]


@dataclass
class ValidationResult:
    """The outcome of validating a single email address or phone number.

    Every validator in this package returns one of these, regardless of
    whether the input turned out to be valid. This keeps the "value was
    invalid" case an ordinary, inspectable return value rather than an
    exception -- callers only need to handle :class:`ValidationError` for
    genuinely exceptional situations (see that class's docstring).

    Attributes:
        is_valid: Whether the input passed validation.
        formatted: The normalized/formatted value -- a lowercased,
            stripped email address, or an E.164-formatted phone number.
            ``None`` when ``is_valid`` is ``False``, since there is no
            canonical form for an invalid value.
        errors: Human-readable validation error messages, e.g.
            ``["MX records not found"]``. Empty when ``is_valid`` is
            ``True``.
        details: Additional metadata describing the validation, such as
            ``domain`` and ``mx_valid`` for emails, or ``country`` and
            ``is_mobile`` for phone numbers. The exact keys depend on
            which validator produced the result -- see that validator's
            docstring for the full list.

    Example:
        >>> result = ValidationResult(
        ...     is_valid=False,
        ...     formatted=None,
        ...     errors=["MX records not found"],
        ...     details={"format_valid": True, "mx_valid": False},
        ... )
        >>> result.is_valid
        False
    """

    is_valid: bool
    formatted: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class ValidationError(Exception):
    """Raised when a value cannot be evaluated at all, not just when it's invalid.

    This is deliberately narrow. An email or phone number that is simply
    *incorrect* (bad format, no MX record, wrong length) is reported
    through a :class:`ValidationResult` with ``is_valid=False`` -- that is
    the expected, everyday outcome and callers should not need a
    try/except for it.

    ``ValidationError`` is reserved for cases the caller must fix in code
    before validation can even be attempted, such as:

    * Constructing a validator with invalid configuration (e.g. a
      non-positive ``timeout``, or a ``default_country`` that isn't a
      recognized region code).
    * Calling ``validate()`` with a value of the wrong type (e.g. ``None``
      or an ``int`` instead of ``str``).

    Example:
        >>> from email_phone_validator import PhoneValidator, ValidationError
        >>> try:
        ...     PhoneValidator(default_country="ZZ")
        ... except ValidationError as exc:
        ...     print(exc)
        default_country must be a supported ISO region code, got 'ZZ'
    """
