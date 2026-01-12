from setuptools import setup, find_packages

setup(
    name="solarconflux",
    version="0.1",
    description="This module defines the `Geometry` class, which analyzes the spatial relationships between spacecraft and celestial bodies using their trajectories. It checks for specific geometric alignments such as Opposition, Cone, Quadrature, Arbitrary Angle, and Parker Spiral.",
    author="Emma Vellard",
    author_email="emma.vellard@outlook.fr",
    url="https://github.com/EmmaVellard/SolarConflux",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "numpy",
        "matplotlib",
        "astropy",
        "sunpy",
        "astroquery",
    ],
    include_package_data=True,
)