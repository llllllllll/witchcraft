#!/usr/bin/env python
from setuptools import setup, find_packages
import sys


long_description = ''

if 'upload' in sys.argv:
    with open('README.rst') as f:
        long_description = f.read()


setup(
    name='witchcraft',
    version='0.1.0',
    description='Local music management utilities',
    author='Joe Jevnik',
    author_email='joejev@gmail.com',
    packages=find_packages(),
    long_description=long_description,
    license='GPLv3+',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',  # noqa
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Operating System :: POSIX',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Multimedia :: Sound/Audio :: Players',
    ],
    url='https://github.com/llllllllll/witchcraft',
    install_requires=[
        'click',
        'pytaglib',
        'python-dateutil',
        'sqlalchemy',
    ],
    extras_require={
        'dev': [
            'flake8==2.4.0',
            'pytest==2.8.4',
            'pytest-cov==2.2.1',
            'pytest-pep8==1.0.6',
        ],
    },
)
