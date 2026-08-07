"""Email address validation: RFC-compliant syntax checks plus MX lookups.

Format validation is delegated to the third-party ``email-validator``
package; MX record lookups are performed directly against ``dnspython``
so that lookup timeouts, missing records, and non-existent domains can
each be reported with a specific, actionable message.
"""

from __future__ import annotations

import difflib
from typing import Any, Dict, List, Optional, Tuple

import dns.exception
import dns.resolver

# The "email-validator" PyPI distribution is imported as top-level module
# ``email_validator``. Python 3's absolute-import semantics make this
# unambiguous even though *this* file also happens to be named
# ``email_validator.py`` inside the ``email_phone_validator`` package:
# a bare ``import email_validator`` always resolves via ``sys.path`` to
# the installed third-party package, never to this module itself.
import email_validator as _ev

from .logger import get_logger
from .models import ValidationError, ValidationResult

logger = get_logger("email_validator")

__all__ = ["EmailValidator"]

# Common email providers used to catch likely domain typos (e.g.
# "gmial.com"). Deliberately small and well-known rather than
# exhaustive -- the goal is a cheap, offline "did you mean?" hint, not a
# full-fledged authority on every real domain.
_COMMON_EMAIL_DOMAINS: Tuple[str, ...] = (
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "icloud.com",
    "aol.com",
    "protonmail.com",
    "live.com",
    "msn.com",
    "comcast.net",
)


def _suggest_domains(domain: Optional[str]) -> Optional[List[str]]:
    """Suggest likely-intended domains for a possibly mistyped one.

    Args:
        domain: The domain portion of an email address, or ``None``/empty
            if it could not be determined.

    Returns:
        Up to three close matches from a short list of common email
        providers (e.g. ``["gmail.com"]`` for ``"gmial.com"``), or
        ``None`` if ``domain`` is empty, already a common domain, or not
        close to any of them.
    """
    if not domain:
        return None
    domain = domain.strip().lower()
    if not domain or domain in _COMMON_EMAIL_DOMAINS:
        return None
    matches = difflib.get_close_matches(domain, _COMMON_EMAIL_DOMAINS, n=3, cutoff=0.8)
    return matches or None


class EmailValidator:
    """Validates and normalizes email addresses.

    Combines RFC-compliant syntax validation (via the ``email-validator``
    package) with an optional DNS MX record lookup (via ``dnspython``) to
    confirm the domain is actually configured to receive mail.

    Args:
        check_mx: Whether to perform an MX record lookup on the email's
            domain after syntax validation succeeds. Disable for offline
            use, faster bulk validation, or tests. Defaults to ``True``.
        timeout: Timeout in seconds for the MX DNS lookup. Must be
            positive. Defaults to ``5``.

    Raises:
        ValidationError: If ``timeout`` is not a positive number.

    Example:
        >>> validator = EmailValidator(check_mx=False)
        >>> result = validator.validate("User@Example.com")
        >>> result.is_valid
        True
        >>> result.formatted
        'user@example.com'
    """

    def __init__(self, check_mx: bool = True, timeout: int = 5) -> None:
        if timeout <= 0:
            raise ValidationError(f"timeout must be positive, got {timeout!r}")
        self.check_mx = check_mx
        self.timeout = timeout

    def validate(self, email: str) -> ValidationResult:
        """Validate and normalize a single email address.

        Args:
            email: The email address to validate.

        Returns:
            A :class:`ValidationResult` whose ``formatted`` value is the
            lowercased, stripped email when valid, and whose ``details``
            contains:

            * ``format_valid`` (bool): whether the syntax check passed.
            * ``mx_valid`` (Optional[bool]): whether an MX record was
              found; ``None`` if ``check_mx`` is ``False`` or the syntax
              check already failed.
            * ``domain`` (Optional[str]): the email's domain, when it
              could be determined.
            * ``suggestions`` (Optional[List[str]]): likely-intended
              domains if the given one looks like a typo of a common
              provider.

        Raises:
            ValidationError: If ``email`` is not a string.
        """
        if not isinstance(email, str):
            raise ValidationError(f"email must be a string, got {type(email).__name__}")

        logger.info("Validating email address")

        errors: List[str] = []
        details: Dict[str, Any] = {
            "format_valid": False,
            "mx_valid": None,
            "domain": None,
            "suggestions": None,
        }

        candidate = email.strip()
        if not candidate:
            errors.append("Email address is empty")
            logger.warning("Email validation failed: empty input")
            return ValidationResult(is_valid=False, formatted=None, errors=errors, details=details)

        try:
            # check_deliverability=False: we run our own MX lookup below
            # so we can report timeouts and missing records distinctly,
            # rather than deferring to the library's built-in check.
            checked = _ev.validate_email(candidate, check_deliverability=False)
        except _ev.EmailNotValidError as exc:
            errors.append(str(exc))
            guessed_domain = candidate.rpartition("@")[2] if "@" in candidate else None
            details["domain"] = guessed_domain or None
            details["suggestions"] = _suggest_domains(guessed_domain)
            logger.warning("Email validation failed: %s", exc)
            return ValidationResult(is_valid=False, formatted=None, errors=errors, details=details)

        normalized = checked.normalized.lower()
        domain = checked.domain
        details["format_valid"] = True
        details["domain"] = domain
        details["suggestions"] = _suggest_domains(domain)

        if self.check_mx:
            mx_valid, mx_error = self._check_mx(domain)
            details["mx_valid"] = mx_valid
            if not mx_valid:
                errors.append(mx_error or "MX records not found")

        is_valid = details["format_valid"] and details["mx_valid"] is not False
        if is_valid:
            logger.info("Email validated successfully: %s", normalized)
        else:
            logger.warning("Email validation failed: %s", "; ".join(errors))

        return ValidationResult(
            is_valid=is_valid,
            formatted=normalized if is_valid else None,
            errors=errors,
            details=details,
        )

    def _check_mx(self, domain: str) -> Tuple[bool, Optional[str]]:
        """Look up MX records for ``domain``, failing gracefully.

        Args:
            domain: The domain to look up, e.g. ``"example.com"``.

        Returns:
            A ``(mx_valid, error_message)`` tuple. ``error_message`` is
            ``None`` when ``mx_valid`` is ``True``, and a human-readable
            explanation (missing records, non-existent domain, or
            timeout) otherwise.
        """
        resolver = dns.resolver.Resolver()
        resolver.lifetime = self.timeout
        resolver.timeout = self.timeout
        try:
            answers = resolver.resolve(domain, "MX")
            if len(answers) > 0:
                return True, None
            return False, "MX records not found"
        except dns.resolver.NXDOMAIN:
            logger.warning("MX lookup failed: domain does not exist: %s", domain)
            return False, "Domain does not exist"
        except dns.resolver.NoAnswer:
            logger.warning("MX lookup failed: no MX records for domain: %s", domain)
            return False, "MX records not found"
        except dns.exception.Timeout:
            logger.warning("MX lookup timed out after %ss for domain: %s", self.timeout, domain)
            return False, f"MX lookup timed out after {self.timeout}s"
        except dns.exception.DNSException as exc:
            logger.warning("MX lookup failed for domain %s: %s", domain, exc)
            return False, f"MX lookup failed: {exc}"
