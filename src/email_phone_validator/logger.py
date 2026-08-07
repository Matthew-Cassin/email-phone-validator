"""Centralized logging setup for email-phone-validator.

Following standard library-logging practice, this module does not
configure handlers, formatters, or levels on import -- that decision
belongs to the consuming application, not the library. A
:class:`logging.NullHandler` is attached to the package logger so that,
absent any application configuration, the library stays silent instead of
triggering Python's "No handlers could be found" warning.

Library modules should call :func:`get_logger` rather than using
``print`` or the root logger directly.
"""

from __future__ import annotations

import logging
from typing import Optional

__all__ = ["get_logger", "configure_logging"]

_PACKAGE_LOGGER_NAME = "email_phone_validator"

_package_logger = logging.getLogger(_PACKAGE_LOGGER_NAME)
_package_logger.addHandler(logging.NullHandler())


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return the package logger, or a named child of it.

    Args:
        name: Optional dotted suffix identifying the calling submodule,
            e.g. ``"email_validator"``. When given, returns a child
            logger named ``"email_phone_validator.<name>"``. When
            omitted, returns the package's top-level logger.

    Returns:
        A standard :class:`logging.Logger`.

    Example:
        >>> logger = get_logger("email_validator")
        >>> logger.name
        'email_phone_validator.email_validator'
    """
    if name:
        return _package_logger.getChild(name)
    return _package_logger


def configure_logging(level: int = logging.INFO) -> None:
    """Attach a console handler to the package logger.

    A convenience for scripts, demos, and interactive use -- library code
    itself never calls this. Applications that already manage their own
    logging configuration (via :func:`logging.basicConfig`, a logging
    config file, etc.) should rely on that instead of calling this
    function, since it adds a second handler on top of anything already
    configured.

    Args:
        level: The logging level to enable on the package logger, e.g.
            ``logging.INFO`` or ``logging.DEBUG``. Defaults to
            ``logging.INFO``.

    Example:
        >>> from email_phone_validator.logger import configure_logging
        >>> configure_logging()  # doctest: +SKIP
    """
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    )
    _package_logger.addHandler(handler)
    _package_logger.setLevel(level)
