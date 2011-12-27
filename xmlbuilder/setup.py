from setuptools import setup, find_packages

setup(
    name='xmlbuilder',
    version='1.0',
    description="pythonic way to create xml/(x)html files",
    author='Kostiantyn Danylov aka koder',
    author_email='koder.mail@gmail.com',
    packages=find_packages(),
    license='LGPL v3',
    long_description=open('README.txt').read(),
)
