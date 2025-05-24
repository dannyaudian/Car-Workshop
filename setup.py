from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# get version from __version__ variable in car_workshop/__init__.py
from car_workshop import __version__ as version

setup(
    name="car_workshop",
    version=version,
    description="ERPNext module app for managing automotive workshop operations",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
    required_apps=['frappe'],
)