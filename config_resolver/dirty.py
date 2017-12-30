'''
This module contains the "dirty" stuff. It exists mainly to silence linters
which for one reason or another complain about things they should not complain
about!
'''
# pylint: disable=unused-import

# pylint is unable to find "version" in distutils when using a virtual-env.
# See https://github.com/PyCQA/pylint/issues/73
from distutils.version import StrictVersion  # pylint: disable=import-error,no-name-in-module
