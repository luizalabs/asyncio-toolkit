import os

from setuptools import find_packages, setup


def read(fname):
    path = os.path.join(os.path.dirname(__file__), fname)
    with open(path) as f:
        return f.read()


setup(
    name='luizalabs-asyncio-toolkit',
    version='0.2.1',
    description=(
        'The LuizaLabs set of tools '
        'to ease asyncio development'
    ),
    long_description=read('README.rst'),
    author='Luizalabs',
    author_email='pypi@luizalabs.com',
    url='https://github.com/luizalabs/asyncio-toolkit',
    keywords='asyncio tools utils circuit breaker',
    install_requires=[],
    packages=find_packages(exclude=[
        'tests*'
    ]),
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
    ]
)
