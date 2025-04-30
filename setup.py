from setuptools import setup, find_packages

setup(
    name="SolarConflux",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'astropy',
        'sunpy',
        'matplotlib',
        'numpy'
    ],
    entry_points={
        'console_scripts': [
            'solarconflux=main:SolarConflux',
        ],
    },
    author="Emma Vellard",
    author_email="emma.vellard@outlook.fr",
    description="This module defines the `Geometry` class, which analyzes the spatial relationships between spacecraft and celestial bodies using their trajectories. It checks for specific geometric alignments such as Opposition, Cone, Quadrature, Arbitrary Angle, and Parker Spiral.",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url="https://github.com/EmmaVellard/SolarConflux",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)