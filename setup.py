from setuptools import setup, find_packages

setup(
    name="smartmeds",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "smartmeds=smartmeds.cli.commands:main",
        ],
    },
)
