from __future__ import print_function

import pytest

from xmlserdes import XMLSerializable, XMLSerializableNamedTuple
from xmlserdes.utils import str_from_xml_elt

import numpy as np

class Rectangle(XMLSerializable):
    xml_descriptor = [('width', int), ('height', int)]
    xml_default_tag = 'rect'

    def __init__(self, wd, ht):
        self.width = wd
        self.height = ht

    def __eq__(self, other):
        return self.width == other.width and self.height == other.height

    @classmethod
    def from_xml_dict(cls, dict):
        if list(dict.keys()) != ['width', 'height']:
            raise ValueError('wrong tags')
        return cls(*dict.values())


class TestRectangle(object):
    def test_equality(self):
        r0 = Rectangle(10, 20)
        r1 = Rectangle(10, 20)
        assert r0 is not r1
        assert r0 == r1

    @staticmethod
    def expected_xml(tag):
        return '<{0}><width>42</width><height>100</height></{0}>'.format(tag)

    @pytest.mark.parametrize(
        'tag,tag_for_expected',
        [(None, 'rect'), ('rectangle', 'rectangle')],
        ids=['default-tag', 'explicit-tag'])
    #
    def test_round_trip(self, tag, tag_for_expected):
        r = Rectangle(42, 100)
        r_xml = r.as_xml(tag)
        assert str_from_xml_elt(r_xml) == self.expected_xml(tag_for_expected)
        r1 = Rectangle.from_xml(r_xml, tag_for_expected)
        assert r1 == r


class Circle(XMLSerializableNamedTuple):
    xml_descriptor = [('radius', np.uint16), ('colour', str)]
    xml_default_tag = 'circle'


class TestNamedTuple(object):
    def test_equality(self):
        c0 = Circle(10, 'blue')
        c1 = Circle(10, 'blue')
        c2 = Circle(11, 'red')
        assert c0 is not c1
        assert c0 is not c2
        assert c1 is not c2
        assert c0 == c1
        assert not c0 == c2
        assert not c1 == c2

    @staticmethod
    def expected_xml(tag):
        return '<{0}><radius>42</radius><colour>orange</colour></{0}>'.format(tag)

    @pytest.mark.parametrize(
        'tag,tag_for_expected',
        [(None, 'circle'), ('round-shape', 'round-shape')],
        ids=['default-tag', 'explicit-tag'])
    #
    def test_round_trip(self, tag, tag_for_expected):
        c = Circle(42, 'orange')
        c_xml = c.as_xml(tag)
        assert str_from_xml_elt(c_xml) == self.expected_xml(tag_for_expected)
        c1 = Circle.from_xml(c_xml, tag_for_expected)
        assert c1 == c
