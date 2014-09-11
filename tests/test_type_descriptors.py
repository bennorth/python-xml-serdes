# -*- coding: utf-8  -*-

import pytest

import collections

from lxml import etree
import numpy as np
import xmlserdes as X

make_TD = X.TypeDescriptor.from_terse

import re

try:
    etree_encoding = unicode
except NameError:
    etree_encoding = str


def to_unicode(elt):
    return etree.tostring(elt, encoding=etree_encoding)


class TestAtomicTypes(object):
    def test_verbose(self):
        self._test_type_descriptor(X.Atomic)

    def test_terse(self):
        self._test_type_descriptor(make_TD)

    def _test_type_descriptor(self, td_func):
        for tp, val, exp_txt in [(int, 42, '42'),
                                 (float, 3.5, '3.5'),
                                 (str, '3 < 5', '3 &lt; 5'),
                                 (np.uint8, np.uint8(42), '42')]:
            td = td_func(tp)
            elt = td.xml_element(val, 'foo')
            assert to_unicode(elt) == '<foo>%s</foo>' % exp_txt
            val_round_trip = td.extract_from(elt, 'foo')
            assert type(val_round_trip) is tp
            assert val_round_trip == val


class TestListTypes(object):
    def test_verbose(self):
        td = X.List(X.Atomic(int), 'wd')
        self._test_type_descriptor(td)

    def test_terse(self):
        td = make_TD([int, 'wd'])
        self._test_type_descriptor(td)

    def _test_type_descriptor(self, td):
        val = [42, 100, 99, 123]
        elt = td.xml_element(val, 'widths')
        assert to_unicode(elt) == '<widths>%s</widths>' % ''.join('<wd>%d</wd>' % x for x in val)
        val_round_trip = td.extract_from(elt, 'widths')
        assert val_round_trip == val


class TestNestedListTypes(object):
    def test_verbose(self):
        td = X.List(X.List(X.Atomic(int), 'wd'), 'stripe-group')
        self._test_type_descriptor(td)

    def test_terse(self):
        td = make_TD([[int, 'wd'], 'stripe-group'])
        self._test_type_descriptor(td)

    def _test_type_descriptor(self, td):
        groups = [[1, 2], [3, 4, 5]]

        elt = td.xml_element(groups, 'stripe-groups')

        exp_txt = ('<stripe-groups>%s</stripe-groups>'
                   % ''.join(('<stripe-group>%s</stripe-group>'
                              % ''.join('<wd>%d</wd>' % x for x in grp))
                             for grp in groups))

        assert exp_txt == to_unicode(elt)

        groups_round_trip = td.extract_from(elt, 'stripe-groups')
        assert groups == groups_round_trip


class BareRectangle(collections.namedtuple('BareRectangle', 'width height')):
    pass


class Rectangle(collections.namedtuple('BareRectangle', 'width height')):
    xml_descriptor = X.SerDesDescriptor([('width', X.Atomic(int)),
                                         ('height', X.Atomic(int))])


class TestRectangleEquality(object):
    def test_equality(self):
        r0 = Rectangle(42, 100)
        r1 = Rectangle(42, 100)
        assert r1 is not r0
        assert r1 == r0


class TestInstanceTypes(object):
    def test_bad_construction_verbose(self):
        with pytest.raises_regexp(ValueError, 'has no xml_descriptor'):
            X.Instance(BareRectangle)

    def test_bad_construction_terse(self):
        with pytest.raises_regexp(ValueError, 'no "xml_descriptor" attribute'):
            make_TD(BareRectangle)
        with pytest.raises_regexp(ValueError, 'unhandled terse descriptor'):
            make_TD(lambda x: x)

    def test_verbose(self):
        td = X.Instance(Rectangle)
        self._test_type_descriptor(td)

    def test_terse(self):
        td = make_TD(Rectangle)
        self._test_type_descriptor(td)

    def _test_type_descriptor(self, td):
        rect = Rectangle(42, 100)
        elt = td.xml_element(rect, 'rect')
        assert to_unicode(elt) == expected_rect_xml(42, 100)

        rect_round_trip = td.extract_from(elt, 'rect')
        assert rect_round_trip == rect

    def test_bad_xml_wrong_n_children(self):
        td = X.Instance(Rectangle)
        bad_xml = etree.fromstring('<rect><a>42</a><b>100</b><c>123</c></rect>')
        with pytest.raises_regexp(ValueError, 'expecting 2 children but got 3'):
            td.extract_from(bad_xml, 'rect')

    def test_bad_xml_wrong_tag(self):
        td = X.Instance(Rectangle)
        bad_xml = etree.fromstring('<rect><a>42</a><b>100</b></rect>')
        with pytest.raises_regexp(ValueError,
                                  'expected tag "width" but got "a"'):
            td.extract_from(bad_xml, 'rect')


class _TestNumpyBase(object):
    def bad_value_1(self, x, regexp):
        with pytest.raises_regexp(ValueError, regexp):
            self.td.xml_element(x, 'values')

    def test_bad_values(self):
        self.bad_value_1('hello', 'not ndarray')
        self.bad_value_1(np.array([[1, 2], [3, 4]]), 'not 1-dimensional')
        self.bad_value_1(np.zeros((12,), dtype=np.float32), 'expecting dtype')


class TestNumpyAtomic(_TestNumpyBase):
    def setup_method(self, method):
        self.td = X.NumpyAtomicVector(np.int32)

    def round_trip_1(self, xs, td):
        elt = td.xml_element(xs, 'values')
        xs_round_trip = td.extract_from(elt, 'values')
        assert xs_round_trip.shape == xs.shape
        assert np.all(xs_round_trip == xs)

    def test_round_trips_verbose(self):
        self._test_round_trips(X.NumpyAtomicVector)

    def test_round_trips_terse(self):
        def td_from_dtype(dtype):
            return make_TD((np.ndarray, dtype))
        self._test_round_trips(td_from_dtype)

    def _test_round_trips(self, td_func):
        for dtype in [np.uint8, np.uint16, np.uint32, np.uint64,
                      np.int8, np.int16, np.int32, np.int64,
                      np.float32, np.float64]:
            #
            xs = np.array([-1.23, -9.99, 0.234, 42, 99, 100.11], dtype=dtype)
            self.round_trip_1(xs, td_func(dtype))

    def test_content(self):
        xs = np.array([32, 42, 100, 99, -100], dtype=np.int32)
        elt = self.td.xml_element(xs, 'values')
        assert to_unicode(elt) == '<values>32,42,100,99,-100</values>'


class TestNumpyAtomicConvenience(TestNumpyAtomic):
    def setup_method(self, method):
        self.td = X.NumpyVector(np.int32)


RectangleDType = np.dtype([('width', np.int32), ('height', np.int32)])


def remove_whitespace(s):
    return re.sub(r'\s+', '', s)


class TestNumpyRecordStructured(_TestNumpyBase):
    def setup_method(self, method):
        self.td = X.NumpyRecordVectorStructured(RectangleDType, 'rect')
        self.vals = np.array([(42, 100), (99, 12)], dtype=RectangleDType)

    def test_verbose(self):
        self._test_type_descriptor(self.td)

    def test_terse(self):
        td = make_TD((np.ndarray, RectangleDType, 'rect'))
        self._test_type_descriptor(td)

    def _test_type_descriptor(self, td):
        xml_elt = td.xml_element(self.vals, 'rects')
        expected_xml = remove_whitespace(
            """<rects>
                 <rect><width>42</width><height>100</height></rect>
                 <rect><width>99</width><height>12</height></rect>
               </rects>""")
        assert to_unicode(xml_elt) == expected_xml
        vals_rt = td.extract_from(xml_elt, 'rects')
        assert vals_rt.dtype == self.vals.dtype
        assert vals_rt.shape == self.vals.shape
        assert np.all(vals_rt == self.vals)


class TestNumpyRecordStructuredConvenience(TestNumpyRecordStructured):
    def setup_method(self, method):
        TestNumpyRecordStructured.setup_method(self, method)
        self.td = X.NumpyVector(RectangleDType, 'rect')


class TestDescriptors(object):
    def setup_method(self, method):
        self.rect = BareRectangle(42, 100)

    def do_tests(self, descriptor_elt, exp_tag):
        val = 42
        assert descriptor_elt.tag == exp_tag
        assert descriptor_elt.value_from(self.rect) == val
        xml_elt = descriptor_elt.xml_element(self.rect)
        assert to_unicode(xml_elt) == '<%s>%d</%s>' % (exp_tag, val, exp_tag)
        round_trip_val = descriptor_elt.extract_from(xml_elt)
        assert round_trip_val == val

    def test_from_pair(self):
        self.do_tests(X.ElementDescriptor.new_from_tuple(('width', X.Atomic(int))),
                      'width')

    def test_from_triple_attr_name(self):
        self.do_tests(X.ElementDescriptor.new_from_tuple(('wd', 'width', X.Atomic(int))),
                      'wd')

    def test_from_triple_function(self):
        def getwd(x):
            return x.width

        self.do_tests(X.ElementDescriptor.new_from_tuple(('wd', getwd, X.Atomic(int))),
                      'wd')

    def test_bad_construction(self):
        with pytest.raises_regexp(ValueError, 'length'):
            X.ElementDescriptor.new_from_tuple((1, 2, 3, 4))
        with pytest.raises(TypeError):
            X.ElementDescriptor.new_from_tuple(42)


def expected_rect_xml(w, h):
    return '<rect><width>%d</width><height>%d</height></rect>' % (w, h)


class TestObject(object):
    def setup_method(self, method):
        self.rect = Rectangle(42, 123)

    def test_1(self):
        serialized_xml = X.serialize(self.rect, 'rect')
        assert to_unicode(serialized_xml) == expected_rect_xml(42, 123)

        rect_round_trip = X.deserialize(Rectangle, serialized_xml, 'rect')
        assert rect_round_trip == self.rect

    def test_bad_n_children(self):
        bad_xml = etree.fromstring('<rect><width>99</width></rect>')
        with pytest.raises_regexp(ValueError, 'expecting 2 children but got 1'):
            X.deserialize(Rectangle, bad_xml, 'rect')

    def test_bad_root_tag(self):
        bad_xml = etree.fromstring(expected_rect_xml(42, 100))
        with pytest.raises_regexp(ValueError, 'expected tag .* but got'):
            X.deserialize(Rectangle, bad_xml, 'rectangle')


class Layout(collections.namedtuple('Layout_', 'colour cornerprops stripes ids shape components')):
    xml_descriptor = X.SerDesDescriptor(
        [('colour', X.Atomic(str)),
         ('corner-properties', 'cornerprops', X.List(X.List(X.Atomic(str), 'prop'), 'corner')),
         ('stripes', X.List(X.Atomic(str), 'stripe-colour')),
         ('product-id-codes', 'ids', X.NumpyAtomicVector(np.uint32)),
         ('shape', X.Instance(Rectangle)),
         ('components', X.NumpyRecordVectorStructured(RectangleDType, 'rect'))])


class TestComplexObject(object):
    def test_1(self):
        layout = Layout('dark-blue',
                        [['rounded', 'red'],
                         ['chamfered', 'matt'],
                         ['pointy', 'anodized', 'black'],
                         ['bevelled', 'twisted', 'plastic-coated']],
                        ['red', 'burnt-ochre', 'orange'],
                        np.array([99, 42, 123], dtype=np.uint32),
                        Rectangle(210, 297),
                        np.array([(20, 30), (40, 50)], dtype=RectangleDType))
        xml = X.serialize(layout, 'layout')
        xml_str = to_unicode(xml)
        expected_str = remove_whitespace(
            """<layout>
                 <colour>dark-blue</colour>
                 <corner-properties>
                   <corner>
                     <prop>rounded</prop>
                     <prop>red</prop>
                   </corner>
                   <corner>
                     <prop>chamfered</prop>
                     <prop>matt</prop>
                   </corner>
                   <corner>
                     <prop>pointy</prop>
                     <prop>anodized</prop>
                     <prop>black</prop>
                   </corner>
                   <corner>
                     <prop>bevelled</prop>
                     <prop>twisted</prop>
                     <prop>plastic-coated</prop>
                   </corner>
                 </corner-properties>
                 <stripes>
                   <stripe-colour>red</stripe-colour>
                   <stripe-colour>burnt-ochre</stripe-colour>
                   <stripe-colour>orange</stripe-colour>
                 </stripes>
                 <product-id-codes>99,42,123</product-id-codes>
                 <shape>
                   <width>210</width>
                   <height>297</height>
                 </shape>
                 <components>
                   <rect>
                     <width>20</width>
                     <height>30</height>
                   </rect>
                   <rect>
                     <width>40</width>
                     <height>50</height>
                   </rect>
                 </components>
               </layout>""")
        assert xml_str == expected_str
        X.deserialize(Layout, xml, 'layout')
