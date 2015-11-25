# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import re
import py.code
import pytest


def pytest_namespace():
    return {'raises_regexp': raises_regexp}


class raises_regexp(object):
    def __init__(self, expected_exception, regexp):
        self.exception = expected_exception
        self.regexp = regexp
        self.excinfo = None

    def __enter__(self):
        self.excinfo = object.__new__(py.code.ExceptionInfo)
        return self.excinfo

    def __exit__(self, exc_type, exc_val, exc_tb):
        __tracebackhide__ = True
        if exc_type is None:
            pytest.fail('DID NOT RAISE {0}'.format(self.exception))

        self.excinfo.__init__((exc_type, exc_val, exc_tb))

        if not issubclass(exc_type, self.exception):
            pytest.fail('{0} RAISED instead of {1}\n{2}'.format(exc_type,
                                                                self.exception,
                                                                repr(exc_val)))

        if not re.search(self.regexp, str(exc_val)):
            pytest.fail('Pattern "{0}" not found in "{1}"'.format(self.regexp,
                                                                  str(exc_val)))

        return True
