from setuptools import find_packages, setup

setup(
    name="ai-contentgen-pro",
    version="0.1.0",
    description="Modular AI content generator with prompt engineering and Flask GUI",
    author="AI-ContentGen-Pro Contributors",
    license="MIT",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.10",
    install_requires=[
        "openai>=1.12.0",
        "python-dotenv>=1.0.0",
        "flask>=3.0.0",
        "requests>=2.31.0",
        "prettytable>=3.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ]
    },
    entry_points={"console_scripts": ["contentgen=src.content_generator:main"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,
)
