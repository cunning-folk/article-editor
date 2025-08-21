"""
Setup script for Article Editor.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file, "r", encoding="utf-8") as f:
        requirements = [
            line.strip() 
            for line in f 
            if line.strip() and not line.startswith("#")
        ]

setup(
    name="article-editor",
    version="1.0.0",
    description="AI-powered article editing using Claude API with intelligent chunking for large documents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Article Editor Development Team",
    author_email="contact@articleeditor.dev",
    url="https://github.com/yourusername/article-editor",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    package_data={
        "web": ["templates/*", "static/*", "static/css/*", "static/js/*"],
    },
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.7.0",
        ],
        "gui": [
            "PyQt6>=6.6.0",
        ],
    },
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "article-editor=cli.main:main",
            "article-editor-web=web.app:main",
            "article-editor-batch=cli.batch:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Text Processing",
        "Topic :: Text Processing :: Linguistic",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords=[
        "ai", "claude", "anthropic", "editing", "text-processing", 
        "article", "document", "nlp", "writing", "proofreading"
    ],
    project_urls={
        "Bug Reports": "https://github.com/yourusername/article-editor/issues",
        "Source": "https://github.com/yourusername/article-editor",
        "Documentation": "https://github.com/yourusername/article-editor/wiki",
    },
)