from setuptools import setup

setup(
    name="cert_asa_install",
    version="2.0",
    description="A tool for installation Let's Encrypt certificate on Cisco ASA.",
    author="@nomyownnet",
    download_url=""
    packages=["cert_asa_install"],
    scripts=["scripts/certasainstall.py"],
)