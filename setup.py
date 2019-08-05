import os
import re
import sys

from setuptools import find_packages
from setuptools import setup
from setuptools.command.test import test as TestCommand  # noqa


with open(
    os.path.join(
        os.path.dirname(__file__), "sqlalchemy_collectd", "__init__.py"
    )
) as file_:
    VERSION = (
        re.compile(r".*__version__ = [\"'](.*?)[\"']", re.S)
        .match(file_.read())
        .group(1)
    )


readme = os.path.join(os.path.dirname(__file__), "README.rst")

requires = ["SQLAlchemy>=1.1"]


class UseTox(TestCommand):
    RED = 31
    RESET_SEQ = "\033[0m"
    BOLD_SEQ = "\033[1m"
    COLOR_SEQ = "\033[1;%dm"

    def run_tests(self):
        sys.stderr.write(
            "%s%spython setup.py test is deprecated by PyPA.  Please invoke "
            "'tox' with no arguments for a basic test run.\n%s"
            % (self.COLOR_SEQ % self.RED, self.BOLD_SEQ, self.RESET_SEQ)
        )
        sys.exit(1)


setup(
    name="sqlalchemy-collectd",
    version=VERSION,
    description="Send database connection pool stats to collectd",
    long_description=open(readme).read(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Database :: Front-Ends",
    ],
    keywords="SQLAlchemy collectd",
    author="Mike Bayer",
    author_email="mike@zzzcomputing.com",
    url="https://github.com/sqlalchemy/sqlalchemy-collectd",
    license="MIT",
    packages=find_packages(".", exclude=["examples*", "*.tests"]),
    include_package_data=True,
    cmdclass={"test": UseTox},
    zip_safe=False,
    install_requires=requires,
    entry_points={
        "console_scripts": ["connmon = sqlalchemy_collectd.connmon.main:main"],
        "sqlalchemy.plugins": [
            "collectd = sqlalchemy_collectd.client.plugin:Plugin"
        ],
    },
)
