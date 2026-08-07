from pathlib import Path

from setuptools import find_packages, setup

THIS_DIR = Path(__file__).parent
LONG_DESCRIPTION = (THIS_DIR / "README.md").read_text(encoding="utf-8")

setup(
    name="email-phone-validator",
    version="0.1.0",
    description=(
        "A Python library for validating and normalizing email addresses "
        "and phone numbers."
    ),
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author="Matt",
    license="MIT",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        "email-validator>=2.3.0,<3.0.0",
        "phonenumbers>=9.0.36,<10.0.0",
        "dnspython>=2.8.0,<3.0.0",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Communications :: Email",
    ],
    keywords="email validation phone validation e164 mx-record international",
)
