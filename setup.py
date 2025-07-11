import os

from setuptools import find_packages, setup

setup(
    name="chidian",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "pydantic>=2.10.6,<3.0.0",
    ],
    author="Chidian Contributors",
    description="A cross-language framework for composable, readable, and sharable data mappings",
    long_description=open("../README.md").read()
    if os.path.exists("../README.md")
    else "",
    long_description_content_type="text/markdown",
)
