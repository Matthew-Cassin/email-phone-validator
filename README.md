# Email & Phone Validator

[![CI](https://github.com/Matthew-Cassin/email-phone-validator/actions/workflows/ci.yml/badge.svg)](https://github.com/Matthew-Cassin/email-phone-validator/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Types](https://img.shields.io/badge/types-mypy%20strict-brightgreen)

A Python library for validating and normalizing email addresses (with MX record checks) and international phone numbers (with E.164 formatting), returning structured, inspectable results instead of raw booleans.

## Installation

```bash
# Install directly from GitHub
pip install git+https://github.com/Matthew-Cassin/email-phone-validator.git

# Or clone and install locally for development
git clone https://github.com/Matthew-Cassin/email-phone-validator.git
cd email-phone-validator
pip install -e .
```

## Quick Start

### 1. Basic email validation

```python
from email_phone_validator import EmailValidator

validator = EmailValidator()  # check_mx=True by default
result = validator.validate("someone@gmail.com")

print(result.is_valid)   # True
print(result.formatted)  # "someone@gmail.com"
print(result.details)    # {'format_valid': True, 'mx_valid': True, 'domain': 'gmail.com', 'suggestions': None}
```

### 2. Email with MX checking disabled

Useful for offline use, bulk/batch validation, or tests, where you only care about syntax:

```python
from email_phone_validator import EmailValidator

validator = EmailValidator(check_mx=False)
result = validator.validate("User@Example.com")

print(result.is_valid)   # True
print(result.formatted)  # "user@example.com"  (normalized: lowercased, stripped)
print(result.details["mx_valid"])  # None -- not checked
```

### 3. Basic phone validation

```python
from email_phone_validator import PhoneValidator

validator = PhoneValidator()  # default_country="US"
result = validator.validate("(415) 858-6273")

print(result.is_valid)   # True
print(result.formatted)  # "+14158586273"  (E.164)
print(result.details["carrier_type"])  # "FIXED_LINE_OR_MOBILE"
```

### 4. Phone with a custom country

```python
from email_phone_validator import PhoneValidator

validator = PhoneValidator(default_country="GB")
result = validator.validate("020 7031 3000")

print(result.is_valid)          # True
print(result.formatted)         # "+442070313000"
print(result.details["country"])  # "GB"

# A leading '+' is always auto-detected, regardless of default_country:
result = PhoneValidator(default_country="US").validate("+442070313000")
print(result.details["country"])  # "GB"
```

### 5. Handling `ValidationError`

`ValidationError` is only raised for things the caller must fix in *code* --
bad configuration or the wrong input type. An email or phone number that's
simply incorrect is never an exception; it's a `ValidationResult` with
`is_valid=False`. See [Error Handling](#error-handling) below for the full
distinction.

```python
from email_phone_validator import PhoneValidator, ValidationError

try:
    validator = PhoneValidator(default_country="ZZ")  # not a real region code
except ValidationError as exc:
    print(f"Configuration error: {exc}")
    # Configuration error: default_country must be a supported ISO region code, got 'ZZ'
```

## API Reference

### `EmailValidator`

```python
EmailValidator(check_mx: bool = True, timeout: int = 5)
```

| Parameter  | Type   | Default | Description                                                        |
|------------|--------|---------|----------------------------------------------------------------------|
| `check_mx` | `bool` | `True`  | Perform a DNS MX lookup on the domain after syntax validation passes. |
| `timeout`  | `int`  | `5`     | Timeout in seconds for the MX lookup. Must be positive.              |

**`validate(email: str) -> ValidationResult`**

Validates and normalizes a single email address. Raises `ValidationError` if `email` is not a `str`.

`details` keys: `format_valid`, `mx_valid` (`None` if `check_mx=False`), `domain`, `suggestions` (likely-intended domain(s) if this one looks like a typo of a common provider, e.g. `gmial.com` → `["gmail.com"]`).

### `PhoneValidator`

```python
PhoneValidator(default_country: str = "US")
```

| Parameter         | Type  | Default | Description                                                        |
|-------------------|-------|---------|----------------------------------------------------------------------|
| `default_country` | `str` | `"US"`  | ISO 3166-1 alpha-2 region code used when a number has no `+` prefix and no `country` override. |

**`validate(phone: str, country: Optional[str] = None) -> ValidationResult`**

Validates and formats a phone number to E.164. `country` overrides `default_country` for this call only, and is itself overridden by a leading `+` in `phone` (which already encodes its own country code). Raises `ValidationError` if `phone` is not a `str`, or if `country` is given but isn't a recognized region code.

`details` keys: `country_code`, `national_number`, `country`, `carrier_type` (e.g. `"MOBILE"`, `"FIXED_LINE"`, `"VOIP"`), `is_mobile`. These are populated whenever the number could be parsed, even if it then fails validation, so you can see why an unsuccessful number looked the way it did.

### `ValidationResult`

A dataclass returned by both validators:

| Field       | Type             | Description                                                  |
|-------------|------------------|----------------------------------------------------------------|
| `is_valid`  | `bool`           | Whether the input passed validation.                          |
| `formatted` | `Optional[str]`  | Normalized email or E.164 phone number; `None` if invalid.    |
| `errors`    | `List[str]`      | Human-readable error messages; empty if valid.                |
| `details`   | `Dict[str, Any]` | Validator-specific metadata (see above).                      |

## Configuration

| Setting             | Where                       | Effect                                                                                   |
|----------------------|------------------------------|-------------------------------------------------------------------------------------------|
| `check_mx=False`     | `EmailValidator(...)`        | Skip the DNS MX lookup entirely -- faster, works offline, but won't catch a domain with no mail server. |
| `timeout=<seconds>`  | `EmailValidator(...)`        | How long to wait for the MX lookup before treating it as a graceful (not exceptional) failure. |
| `default_country`    | `PhoneValidator(...)`        | Region assumed for numbers without a `+` prefix and no per-call `country`.               |
| `country=<code>`     | `PhoneValidator().validate()`| Per-call override of `default_country`; ignored if the number starts with `+`.           |

## Error Handling

This library draws a sharp line between two kinds of failure:

* **The value is invalid.** This is the everyday case -- a typo'd email, a
  disconnected phone number, a domain with no mail server. It is *always*
  reported as `ValidationResult(is_valid=False, errors=[...])`, never an
  exception. No try/except is needed for ordinary bad input.
* **Validation couldn't be attempted at all.** Bad validator configuration
  (an unsupported `default_country`, a non-positive `timeout`) or a call
  with the wrong argument type (`None` instead of a string). These raise
  `ValidationError`, since there's no meaningful result to hand back.

```python
from email_phone_validator import EmailValidator, ValidationError

validator = EmailValidator(check_mx=True, timeout=5)

try:
    result = validator.validate(user_supplied_value)
except ValidationError as exc:
    # user_supplied_value wasn't even a string -- a bug upstream, not a bad email
    log.error("Bad call to validate(): %s", exc)
else:
    if not result.is_valid:
        # A completely normal outcome -- show the user what to fix
        print("Please fix:", "; ".join(result.errors))
        if result.details.get("suggestions"):
            print("Did you mean:", result.details["suggestions"][0], "?")
```

## Development

```bash
pip install -e .
pip install pytest flake8

pytest                              # run the test suite
flake8 --max-line-length=100 src/ tests/  # lint
```

## License

MIT -- see [LICENSE](LICENSE) for the full text.

## Contributing

Contributions are welcome. Please open an issue to discuss a change before submitting a pull request, and make sure `pytest` and `flake8` are clean.
