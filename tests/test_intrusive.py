from __future__ import print_function

import pytest

from xmlserdes import XMLSerializable, XMLSerializableNamedTuple
from xmlserdes.utils import str_from_xml_elt

from collections import OrderedDict
import numpy as np
from lxml import etree


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


class Pattern(XMLSerializableNamedTuple):
    xml_descriptor = [('size', int),
                      ('circles', [Circle, 'circle'])]
    xml_default_tag = 'pattern'


class TestNestedNamedTuple(object):
    @staticmethod
    def expected_xml(tag):
        return ('<{0}>'
                + '<size>33</size>'
                + '<circles>'
                + '<circle><radius>10</radius><colour>blue</colour></circle>'
                + '<circle><radius>12</radius><colour>red</colour></circle>'
                + '</circles>'
                + '</{0}>').format(tag)

    @pytest.mark.parametrize(
        'tag,tag_for_expected',
        [(None, 'pattern'), ('circle-picture', 'circle-picture')],
        ids=['default-tag', 'explicit-tag'])
    #
    def test_round_trip(self, tag, tag_for_expected):
        p = Pattern(33, [Circle(10, 'blue'), Circle(12, 'red')])
        p_xml = p.as_xml(tag)
        assert str_from_xml_elt(p_xml) == self.expected_xml(tag_for_expected)
        p1 = Pattern.from_xml(p_xml, tag_for_expected)
        assert p1 == p

    @pytest.mark.parametrize('tag, kwargs', [
        (None, {}),
        ('circle-picture', {'pretty_print': False})
    ])
    def test_as_xml_str(self, tag, kwargs):
        if 'pretty_print' not in kwargs:
            kwargs['pretty_print'] = True
        p = Pattern(33, [Circle(10, 'blue'), Circle(12, 'red')])
        assert str_from_xml_elt(p.as_xml(tag), **kwargs) == p.as_xml_str(tag, **kwargs)


class RectangleCollection(XMLSerializableNamedTuple):
    xml_descriptor = [('creator', str),
                      ('rectangles', [Rectangle])]


def TestListImplicitTag(object):
    def test_rectangles(self):
        rc = RectangleCollection('Arthur Jackson',
                                 [Rectangle(12, 34), Rectangle(56, 78)])
        exp_txt = ('<rectangle-collection>'
                   + '<creator>%s</creator>'
                   + '<rectangles>%s</rectangles>'
                   + '</rectangle-collection>'
                   % (rc.creator,
                      ''.join('<rect><width>%d</width><height>%d</height></rect>'
                              % (r.width, r.height)
                              for r in rc.rectangles)))
        assert str_from_xml_elt(rc.as_xml('rectangle-collection')) == exp_txt


class Ellipse(XMLSerializableNamedTuple):
    xml_descriptor = [('minor-radius', 'radius0', np.uint16),
                      ('major-radius', 'radius1', np.uint16),
                      ('colour', str)]
    xml_default_tag = 'ellipse'


class TestNamedTupleDifferentTags(object):
    @classmethod
    def setup_class(cls):
        cls.e = Ellipse(42, 99, 'red')

    @staticmethod
    def expected_xml(tag):
        return ('<{0}>'
                + '<minor-radius>42</minor-radius>'
                + '<major-radius>99</major-radius>'
                + '<colour>red</colour>'
                + '</{0}>').format(tag)

    def test_attributes(self):
        assert self.e.radius0 == 42
        assert self.e.radius1 == 99
        assert self.e.colour == 'red'

    def test_indexing(self):
        assert self.e[0] == 42
        assert self.e[1] == 99
        assert self.e[2] == 'red'

    def test_str(self):
        assert str(self.e) == "Ellipse(radius0=42, radius1=99, colour='red')"

    @pytest.mark.parametrize(
        'tag,tag_for_expected',
        [(None, 'ellipse'), ('oval', 'oval')],
        ids=['default-tag', 'explicit-tag'])
    #
    def test_round_trip(self, tag, tag_for_expected):
        e = Ellipse(42, 99, 'red')
        e_xml = e.as_xml(tag)
        assert str_from_xml_elt(e_xml) == self.expected_xml(tag_for_expected)
        e1 = Ellipse.from_xml(e_xml, tag_for_expected)
        assert e1 == e


class TestBadNamedTupleConstruction(object):
    def build_bad_class_wrong_value_from_slot():
        class Foo(XMLSerializableNamedTuple):
            xml_descriptor = [('foo', lambda x: x.foo, str)]
        return Foo

    def build_bad_class_no_descr():
        class Foo(XMLSerializableNamedTuple):
            pass
        return Foo

    @pytest.mark.parametrize(
        'class_fun,exc_re',
        [(build_bad_class_wrong_value_from_slot, 'must be simple'),
         (build_bad_class_no_descr, 'no "xml_descriptor"')],
        ids=['wrong-value-from-slot', 'no-xml-descriptor'])
    #
    def test_bad_construction(self, class_fun, exc_re):
        with pytest.raises_regexp(ValueError, exc_re):
            foo_cls = class_fun()


class TestBadMethodUsage(object):
    def test_wrong_n_children(self):
        bad_xml = etree.fromstring('<rect><a>1</a><b>1</b><c>1</c></rect>')
        with pytest.raises_regexp(ValueError, 'expected 2 children but got 3'):
            obj = Rectangle.from_xml(bad_xml, 'rect')

    @pytest.mark.parametrize(
        'bad_dict_items,exc_re',
        [([('a', 1), ('b', 2), ('c', 3)],
          'expected 2 children but got 3'),
         ([('a', 1), ('b', 2)],
          'unexpected tags: 2 differ;.* "radius" .* "a" at posn 0')],
        ids=['wrong-n-children', 'wrong-tags'])
    #
    def test_bad_ordered_dict(self, bad_dict_items, exc_re):
        # Shouldn't occur in normal use because from_xml() checks on
        # construction of the dictionary that tags are as expected.
        bad_dict = OrderedDict(bad_dict_items)
        with pytest.raises_regexp(ValueError, exc_re):
            obj = Circle.from_xml_dict(bad_dict)

    def test_wrong_top_level_tag(self):
        bad_xml = etree.fromstring('<rectangle><width>1</width><height>2</height></rectangle>')
        with pytest.raises_regexp(ValueError, 'expected tag "rect" but got "rectangle"'):
            obj = Rectangle.from_xml(bad_xml, 'rect')
