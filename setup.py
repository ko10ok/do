#!/usr/bin/env python3
"""Setup script for doq package."""

import os
import sys

from setuptools import find_packages, setup


def get_version(filename='doq/version'):
    return open(filename, "r").read().strip()

# Read README for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

# Platform-specific scripts
def get_platform_scripts():
    """Return appropriate scripts based on platform."""
    if sys.platform == "win32":
        return ["scripts/doq.ps1"]
    else:
        return ["scripts/doq_unix"]

# Platform-specific entry points
def get_platform_entry_points():
    """Return appropriate entry points based on platform."""
    if sys.platform == "win32":
        return {
            "console_scripts": [
                "doq=doq.main:main",  # Windows will use PowerShell script, but entry point for compatibility
            ],
        }
    else:
        return {
            "console_scripts": [
                "doq=doq.main:main",  # Unix simple version
            ],
        }

setup(
    name="do",
    version=get_version(),
    description="A command-line interface for various LLM providers (Claude, ChatGPT, DeepSeek)",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Yuriy Sagitov",
    author_email="home_r@mail.ru",
    url="https://github.com/ko10ok/do",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "anthropic>=0.3.0",
        "openai>=1.0.0",
        "requests>=2.25.0",
        "pyyaml>=6.0",
        "click>=8.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-asyncio>=0.18.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.910",
        ]
    },
    # Platform-specific scripts
    scripts=get_platform_scripts(),
    entry_points=get_platform_entry_points(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="llm ai cli claude chatgpt deepseek anthropic openai",
    license="Apache-2.0",
    package_data={
        'doq': ['version'],
    },
)
