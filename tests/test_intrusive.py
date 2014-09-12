from __future__ import print_function

import pytest

from xmlserdes import XMLSerializable
from xmlserdes.utils import str_from_xml_elt

class Rectangle(XMLSerializable):
    xml_descriptor = [('width', int), ('height', int)]
    xml_default_tag = 'rect'

    def __init__(self, wd, ht):
        self.width = wd
        self.height = ht

    def __eq__(self, other):
        return self.width == other.width and self.height == other.height

    @classmethod
    def from_xml_dict(cls):
        pass


class TestRectangle(object):
    @staticmethod
    def expected_xml(tag):
        return '<{0}><width>42</width><height>100</height></{0}>'.format(tag)

    @pytest.mark.parametrize(
        'tag,tag_for_expected',
        [(None, 'rect'), ('rectangle', 'rectangle')],
        ids=['default-tag', 'explicit-tag'])
    #
    def test_serialization(self, tag, tag_for_expected):
        r = Rectangle(42, 100)
        assert str_from_xml_elt(r.as_xml(tag)) == self.expected_xml(tag_for_expected)
