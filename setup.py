import re
from os import path
from setuptools import find_packages, setup
import re


version_file = 'tracker/__init__.py'
with open('tracker/__init__.py', 'rt') as fd:
    vsre = r"^__version__ = ['\"]([^'\"]*)['\"]"
    mo = re.search(vsre, fd.read(), re.MULTILINE)
    if mo:
        version = mo.group(1)
    else:
        raise RuntimeError(
            f'Unable to find version string in {version_file}'
        )


with open('requirements.txt') as f:
    requirements = f.readlines()

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md')) as f:
    long_description = f.read()

setup(
    name='vg_price_tracker',
    version=version,
    author='Alex Constantinou',
    author_email='a_constantinou@hotmail.co.uk',
    url='https://github.com/aconstantinou123/game_price_tracker',
    description='Package for keeping track of game collection prices.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='MIT',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'vgpt = tracker.tracker:main'
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords='games collection pandas BeautifulSoup python package',
    install_requires=requirements,
    zip_safe=False
)
