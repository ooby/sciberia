import pathlib
from setuptools import setup

HERE = pathlib.Path(__file__).parent

README = (HERE / "README.md").read_text()

setup(
    name="sciberia",
    version="0.1.1",
    description="Sciberia helper libraries",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/sciberia-llc/sciberia",
    author="Sciberia, LLC",
    author_email="info@sciberia.io",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    packages=["sciberia"],
    include_package_data=True,
    install_requires=[
        "numpy",
        "pydicom",
        "pytest",
        "scipy"
    ]
)
