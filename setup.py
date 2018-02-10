from setuptools import setup
from setuptools import find_packages
import os
import re


with open(
    os.path.join(
        os.path.dirname(__file__), 'sqlalchemy_collectd', '__init__.py')
) as file_:
    VERSION = re.compile(
        r".*__version__ = '(.*?)'", re.S).match(file_.read()).group(1)


readme = os.path.join(os.path.dirname(__file__), 'README.rst')

requires = [
    'SQLAlchemy>=1.1',
]

setup(
    name='sqlalchemy-collectd',
    version=VERSION,
    description="Send database connection pool stats to collectd",
    long_description=open(readme).read(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Database :: Front-Ends',
    ],
    keywords='SQLAlchemy collectd',
    author='Mike Bayer',
    author_email='mike@zzzcomputing.com',
    url='http://github.org/sqlalchemy/sqlalchemy-collectd',
    license='MIT',
    packages=find_packages(".", exclude=["*.tests"]),
    include_package_data=True,
    tests_require=['pytest', 'mock'],
    setup_requires=['pytest-runner'],
    zip_safe=False,
    install_requires=requires,
    entry_points={
        'sqlalchemy.plugins': [
            'collectd = sqlalchemy_collectd.client.plugin:Plugin'
        ]
    }
)
