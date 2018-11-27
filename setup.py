from setuptools import setup
from setuptools import find_packages
from setuptools.command.test import test as TestCommand  # noqa
import os
import re
import sys


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


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


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
    url='https://github.com/sqlalchemy/sqlalchemy-collectd',
    license='MIT',
    packages=find_packages(".", exclude=["examples*", "*.tests"]),
    include_package_data=True,
    tests_require=['pytest', 'mock'],
    cmdclass={'test': PyTest},
    zip_safe=False,
    install_requires=requires,
    entry_points={
        'sqlalchemy.plugins': [
            'collectd = sqlalchemy_collectd.client.plugin:Plugin'
        ]
    }
)
