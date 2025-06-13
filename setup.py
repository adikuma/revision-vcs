from setuptools import setup, find_packages

setup(
    name="revision-vcs",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "rev = rev.__main__:main",
        ],
    },
    install_requires=[],
    author="aditya kumar",
    author_email="adityakuma0308@gmail.com",
    description="a minimal version control system",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/adikuma/revision-vcs",
    classifiers=[
        "programming language :: python :: 3",
        "license :: osi approved :: mit license",
    ],
)