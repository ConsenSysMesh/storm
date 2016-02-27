#!/usr/bin/env python

from setuptools import setup, find_packages
import versioneer

CONSOLE_SCRIPTS = ['docker-storm=storm.storm:main']
LONG = """
Storm - Multi-cloud load-balanced orchestration for Docker
"""

setup(name="docker-storm",
      packages=find_packages("."),
      description='Multi-cloud load-balanced orchestration for Docker',
      long_description=LONG,
      author="caktux",
      author_email="caktux@gmail.com",
      url='https://github.com/ConsenSys/storm/',
      install_requires=[
          "boto",
          "azure",
          "pyyaml",
          "fabric",
          "futures",
          "argparse",
          "colorlog",
          "progressbar2",
      ],
      entry_points=dict(console_scripts=CONSOLE_SCRIPTS),
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      classifiers=[
          "Development Status :: 2 - Pre-Alpha",
          "Environment :: Console",
          "License :: OSI Approved :: MIT License",
          "Operating System :: MacOS :: MacOS X",
          "Operating System :: POSIX :: Linux",
          "Programming Language :: Python :: 2.7",
      ])
