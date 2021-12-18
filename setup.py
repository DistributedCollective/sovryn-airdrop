import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()

requires = [
    'eth-utils',
    'eth-account',
    'eth-typing',
    'web3',
]

tests_require = [
    'pytest',
    'pytest-cov',
]

setup(
    name='sovryn_airdrop',
    version='0.0',
    description='sovryn_airdrop',
    long_description=README,
    classifiers=[
        'Programming Language :: Python',
    ],
    author='Sovryn Mutants',
    author_email='',
    url='',
    keywords='rsk bitcoin ethereum web3',
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    zip_safe=False,
    extras_require={
        'testing': tests_require,
    },
    install_requires=requires,
    entry_points={
        'paste.app_factory': [
            'main = sovryn_airdrop:main',
        ],
        'console_scripts': [
            'sovryn_airdrop=sovryn_airdrop.cli:main',
        ],
    },
)
