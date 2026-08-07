"""email-phone-validator: production-grade email and phone validation.

Public API:
    EmailValidator: Validates and normalizes email addresses, with
        optional MX record checking.
    PhoneValidator: Validates and formats international phone numbers.
    ValidationResult: The structured result both validators return.
    ValidationError: Raised for unrecoverable errors (bad configuration
        or malformed input), as distinct from a merely invalid value --
        see its docstring for the exact boundary.

Example:
    >>> from email_phone_validator import EmailValidator
    >>> EmailValidator(check_mx=False).validate("user@example.com").is_valid
    True
"""

from .email_validator import EmailValidator
from .models import ValidationError, ValidationResult
from .phone_validator import PhoneValidator

__version__ = "0.1.0"

__all__ = [
    "EmailValidator",
    "PhoneValidator",
    "ValidationResult",
    "ValidationError",
    "__version__",
]
