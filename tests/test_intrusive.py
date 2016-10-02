from __future__ import print_function

import pytest

from xmlserdes import XMLSerializable, XMLSerializableNamedTuple
from xmlserdes.utils import str_from_xml_elt
from xmlserdes.errors import XMLSerDesError, XMLSerDesWrongChildrenError


from collections import OrderedDict
import numpy as np
from lxml import etree
import sys
import six


class AutoSubclassesMeta(type):
    """
    Create 'ochre' and 'purple' subclasses of any classes having this meta-class.

    But only one level deep, to avoid engaging sorcerer's apprentice mode.
    """
    def __new__(meta, cls_name, bases, cls_dict):
        cls = super(AutoSubclassesMeta, meta).__new__(meta, cls_name, bases, cls_dict)
        cls_is_base = not hasattr(cls, 'colour')
        if cls_is_base:
            cls.__subclass_from_colour__ = {}
            module_name = cls.__module__
            module = sys.modules[module_name]
            for colour in ['ochre', 'purple']:
                subcls_name = '_'.join([cls_name, colour])
                subcls = type(subcls_name, (cls,), {'colour': colour})
                subcls.__module__ = module_name
                setattr(module, subcls_name, subcls)
                cls.__subclass_from_colour__[colour] = subcls
        return cls

    def __getitem__(cls, key):
        return cls.__subclass_from_colour__[key]


class XMLSerdesAutoSubclassesMeta(AutoSubclassesMeta, type(XMLSerializableNamedTuple)):
    pass


class PaintPot(six.with_metaclass(XMLSerdesAutoSubclassesMeta, XMLSerializableNamedTuple)):
    xml_descriptor = [('diameter', int)]
    xml_default_tag = 'paint-pot'

    @classmethod
    def height(cls):
        return 5


class TestPaintPotSubclasses(object):
    @staticmethod
    def expected_xml(tag):
        return '<{0}><diameter>100</diameter></{0}>'.format(tag)

    def parametrize_for_colours():
        # flake8 doesn't realise that PaintPot_ochre and PaintPot_purple
        # have been magically created; can't really blame it.  Hence the
        # 'noqa' annotations.
        return pytest.mark.parametrize('colour, paint_pot_cls',
                                       [('ochre', PaintPot_ochre),  # noqa
                                        ('purple', PaintPot_purple)],  # noqa
                                       ids=['ochre', 'purple'])

    @parametrize_for_colours()
    def test_subclass_properties(self, colour, paint_pot_cls):
        assert paint_pot_cls.height() == 5
        assert paint_pot_cls.colour == colour
        assert PaintPot[colour] is paint_pot_cls

    @parametrize_for_colours()
    @pytest.mark.parametrize(
        'tag,tag_for_expected',
        [(None, 'paint-pot'), ('pot-of-paint', 'pot-of-paint')],
        ids=['default-tag', 'explicit-tag'])
    def test_round_trip(self, colour, paint_pot_cls, tag, tag_for_expected):
        pp = paint_pot_cls(100)
        pp_xml = pp.as_xml(tag)
        assert str_from_xml_elt(pp_xml) == self.expected_xml(tag_for_expected)
        pp1 = paint_pot_cls.from_xml(pp_xml, tag_for_expected)
        assert type(pp1) is type(pp)
        assert pp1 == pp


class Rectangle(XMLSerializable):
    xml_descriptor = [('width', int), ('height', int)]
    xml_default_tag = 'rect'

    def __init__(self, wd, ht):
        self.width = wd
        self.height = ht

    def __eq__(self, other):
        return self.width == other.width and self.height == other.height


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

    def test_derived_xml_inheriting_tag(self):
        class RoundedRectangle(Rectangle):
            corner_radius = 5

        rounded_rect = RoundedRectangle(42, 100)
        assert rounded_rect.corner_radius == 5
        assert rounded_rect.as_xml_str(pretty_print=False) == self.expected_xml('rect')

    def test_derived_xml_overriding_tag(self):
        class RoundedRectangle(Rectangle):
            xml_default_tag = 'round-rect'
            corner_radius = 5

        rounded_rect = RoundedRectangle(42, 100)
        assert rounded_rect.as_xml_str(pretty_print=False) == self.expected_xml('round-rect')


class TestNullaryNamedTuple(object):
    def test_xml(self):
        class NullaryNamedTuple(XMLSerializableNamedTuple):
            pass

        nullary_tuple = NullaryNamedTuple()
        xml_str = nullary_tuple.as_xml_str(pretty_print=False)
        assert xml_str == '<NullaryNamedTuple/>'


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

    def test_derived_xml_inheriting_tag(self):
        class ThickCircle(Circle):
            line_thickness = 18

        c = ThickCircle(42, 'orange')
        assert c.line_thickness == 18
        assert c.as_xml_str(pretty_print=False) == self.expected_xml('circle')


class RightAngledTriangle(XMLSerializableNamedTuple):
    xml_descriptor = [('a', int), ('b', int), ('c', int)]
    xml_default_tag = None


class TestNamedTupleSuppressInferredDefaultTag(object):
    def test_tag_not_supplied_caught(self):
        rat = RightAngledTriangle(4684659, 4684660, 6625109)
        with pytest.raises_regexp(AttributeError, 'xml_default_tag'):
            rat.as_xml()


class Pattern(XMLSerializableNamedTuple):
    xml_descriptor = [('size', int),
                      ('circles', [Circle, 'circle'])]
    xml_default_tag = 'pattern'


class TestNestedNamedTuple(object):
    @staticmethod
    def expected_xml(tag):
        return ('<{0}>'
                '<size>33</size>'
                '<circles>'
                '<circle><radius>10</radius><colour>blue</colour></circle>'
                '<circle><radius>12</radius><colour>red</colour></circle>'
                '</circles>'
                '</{0}>').format(tag)

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


class TestListImplicitTag(object):
    def test_rectangles(self):
        rc = RectangleCollection('Arthur Jackson',
                                 [Rectangle(12, 34), Rectangle(56, 78)])
        exp_txt = ('<rectangle-collection>'
                   '<creator>%s</creator>'
                   '<rectangles>%s</rectangles>'
                   '</rectangle-collection>'
                   % (rc.creator,
                      ''.join('<rect><width>%d</width><height>%d</height></rect>'
                              % (r.width, r.height)
                              for r in rc.rectangles)))
        assert rc.as_xml_str('rectangle-collection', pretty_print=False) == exp_txt


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
                '<minor-radius>42</minor-radius>'
                '<major-radius>99</major-radius>'
                '<colour>red</colour>'
                '</{0}>').format(tag)

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

    @pytest.mark.parametrize(
        'class_fun,exc_re',
        [(build_bad_class_wrong_value_from_slot, 'must be simple')],
        ids=['wrong-value-from-slot'])
    #
    def test_bad_construction(self, class_fun, exc_re):
        with pytest.raises_regexp(ValueError, exc_re):
            class_fun()


class TestBadMethodUsage(object):
    def test_wrong_n_children(self):
        bad_xml = etree.fromstring('<rect><a>1</a><b>1</b><c>1</c></rect>')
        with pytest.raises_regexp(XMLSerDesWrongChildrenError,
                                  'mismatched children',
                                  xpath=['rect']):
            Rectangle.from_xml(bad_xml, 'rect')

    @pytest.mark.parametrize(
        'bad_dict_items,cmp_txt',
        [([('a', 1), ('b', 2), ('c', 3)],
          r'\[missing: radius, missing: colour, unexpected: a, unexpected: b, unexpected: c\]'),
         ([('a', 1), ('b', 2)],
          r'\[missing: radius, missing: colour, unexpected: a, unexpected: b\]'),
         ([('radius', 1), ('b', 2)],
          r'\[as-expected: radius, missing: colour, unexpected: b\]')],
        ids=['wrong-n-children', 'wrong-tags', 'one-wrong-tag'])
    #
    def test_bad_ordered_dict(self, bad_dict_items, cmp_txt):
        # Shouldn't occur in normal use because from_xml() checks on
        # construction of the dictionary that tags are as expected.
        bad_dict = OrderedDict(bad_dict_items)
        with pytest.raises_regexp(XMLSerDesWrongChildrenError,
                                  'mismatched children: ' + cmp_txt,
                                  xpath=[]):
            Circle.from_xml_dict(bad_dict)

    def test_wrong_top_level_tag(self):
        bad_xml = etree.fromstring('<rectangle><width>1</width><height>2</height></rectangle>')
        with pytest.raises_regexp(ValueError, 'expected tag "rect" but got "rectangle"'):
            Rectangle.from_xml(bad_xml, 'rect')


class TestDeepError(object):
    def test_from_xml(self):
        class Chair(XMLSerializableNamedTuple):
            xml_default_tag = 'chair'
            xml_descriptor = [('colour', str)]

        class Room(XMLSerializableNamedTuple):
            xml_default_tag = 'room'
            xml_descriptor = [('chairs', [Chair])]

        class Building(XMLSerializableNamedTuple):
            xml_default_tag = 'building'
            xml_descriptor = [('rooms', [Room])]

        bad_xml = etree.fromstring("""<building>
                                        <rooms>
                                          <room>
                                            <chairs>
                                              <chair><colour>red</colour></chair>
                                              <chair><colour>blue</colour></chair>
                                            </chairs>
                                          </room>
                                          <room>
                                            <chairs>
                                              <chair><colour>red</colour></chair>
                                              <chair><colour>blue</colour></chair>
                                              <chair><size>42</size></chair>
                                            </chairs>
                                          </room>
                                        </rooms>
                                      </building>""")

        with pytest.raises_regexp(XMLSerDesError,
                                  'expected tag "colour" but got "size"',
                                  ['building', 'rooms', 'room[2]', 'chairs', 'chair[3]']):
            Building.from_xml(bad_xml, 'building')

    def test_as_xml(self):
        class Chair(XMLSerializableNamedTuple):
            xml_default_tag = 'chair'
            xml_descriptor = [('dimensions', (np.ndarray, np.int16))]

        class Room(XMLSerializableNamedTuple):
            xml_default_tag = 'room'
            xml_descriptor = [('chairs', [Chair])]

        class Building(XMLSerializableNamedTuple):
            xml_default_tag = 'building'
            xml_descriptor = [('rooms', [Room])]

        chairs = [Chair(np.array([1, 2, 3], dtype=np.int16)),
                  Chair(np.array([4, 5, 6], dtype=np.int16))]

        building = Building([Room(chairs),
                             Room(chairs + [Chair(np.array([100, 200, 300], dtype=np.int32))])])

        with pytest.raises_regexp(XMLSerDesError,
                                  'expected dtype .*int16.* but got "int32"',
                                  ['building',
                                   'rooms', 'room[2]',
                                   'chairs', 'chair[3]',
                                   'dimensions']):
            building.as_xml()


class TestBadMetaclassUse(object):
    def test_no_xml_descriptor(self):
        """
        Normally, derivation from XMLSerializable ensures the class being built has an
        'xml_descriptor' attribute.  To get full test coverage, we need to purposefully
        attempt to create a class with XMLSerializableMeta as its metaclass but with no
        'xml_descriptor'.  Furthermore, that test needs an intermediate base class
        lacking the attribute.
        """
        with pytest.raises_regexp(ValueError, 'no "xml_descriptor" in "NoXmlDescriptor"'):
            class Nop(object):
                pass

            class NoXmlDescriptor(six.with_metaclass(type(XMLSerializable), Nop)):
                pass


@pytest.mark.skipif(sys.version_info < (3, 4),
                    reason='requires Python 3.4 or higher')
class TestEnum(object):
    def test_round_trip(self):
        from enum import Enum
        Animal = Enum('Animal', 'Cat Dog Rabbit')

        class PetDetails(XMLSerializableNamedTuple):
            xml_descriptor = [('type', Animal), ('weight', float)]

        pd = PetDetails(Animal.Dog, 42.5)
        pd_xml = pd.as_xml('pet-details')
        assert str_from_xml_elt(pd_xml) == ('<pet-details><type>Dog</type>'
                                            '<weight>42.5</weight></pet-details>')
        pd1 = PetDetails.from_xml(pd_xml, 'pet-details')
        assert pd1 == pd
