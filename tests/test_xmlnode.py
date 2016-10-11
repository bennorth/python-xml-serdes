import pytest

import xmlserdes as X
import xmlserdes.nodes as XN

make_TD = X.TypeDescriptor.from_terse


class TestBadAppend(object):
    @pytest.mark.parametrize(
        'err_fragment, tag',
        [('child', 'height'), ('attribute', '@height')])
    #
    def test_append_to_attribute(self, err_fragment, tag):
        n = XN.make_XMLNode('@weight', '23 stone')
        with pytest.raises_regexp(ValueError, 'cannot append {0}'.format(err_fragment)):
            ch = XN.make_XMLNode(tag, '6 feet')
            ch.append_to(n)


class TestBadElement(object):
    def test_request_element_when_attribute(self):
        td = make_TD(int)
        with pytest.raises_regexp(ValueError, 'expected element but got attribute'):
            td.xml_element(42, '@height')
