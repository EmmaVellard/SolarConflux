from setuptools import setup, find_packages

setup(
    name="solarconflux",
    version="0.1.0",
    description="Approximate heliocentric trajectory geometry and Parker-spiral alignment screening for coordinated solar observations.",
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
    entry_points={"console_scripts": ["solarconflux=solarconflux.cli:main"]},
)
