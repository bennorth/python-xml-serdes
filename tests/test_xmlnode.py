import pytest

import xmlserdes as X

make_TD = X.TypeDescriptor.from_terse


class TestBadElement(object):
    def test_request_element_when_attribute(self):
        td = make_TD(int)
        with pytest.raises_regexp(ValueError, 'expected element but got attribute'):
            td.xml_element(42, '@height')
