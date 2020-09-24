import setuptools
import os

# You cannot easily pass arguments to this script
# Thus using this simple env variable hack
version = os.getenv("VERSION")
if version is None:
    raise Exception("No version specified as VERSION env param, exiting")

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="papiea-sdk",
    version=version,
    author="Shlomi Vaknin",
    description="Papiea python SDK",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nutanix/papiea-js",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=["aiohttp>=3.6.2"],
)
