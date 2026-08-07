from setuptools import setup, find_packages

setup(
    name="email-phone-validator",
    version="0.1.0",
    description="A Python library for validating and normalizing email addresses and phone numbers.",
    author="Matt",
    author_email="m.cassin93@hotmail.com",
    license="MIT",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
)
