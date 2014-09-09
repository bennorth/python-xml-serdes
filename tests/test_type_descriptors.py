from collections import namedtuple

import sys
sys.path.append('..')

import unittest
from unittest import TestCase

from lxml import etree
import numpy as np
import XMLserdes as X

import re

try:
    etree_encoding = unicode
except NameError:
    etree_encoding = str

def to_unicode(elt):
    return etree.tostring(elt, encoding = etree_encoding)

class TestAtomicTypes(TestCase):
    def test_1(self):
        for tp, val, exp_txt in [(int, 42, '42'),
                                 (float, 3.5, '3.5'),
                                 (str, '3 < 5', '3 &lt; 5'),
                                 (np.uint8, np.uint8(42), '42')]:
            td = X.Atomic(tp)
            elt = td.xml_element(val, 'foo')
            self.assertEqual('<foo>%s</foo>' % exp_txt, to_unicode(elt))
            val_round_trip = td.extract_from(elt, 'foo')
            self.assertIs(tp, type(val_round_trip))
            self.assertEqual(val, val_round_trip)

class TestListTypes(TestCase):
    def test_1(self):
        val = [42, 100, 99, 123]
        td = X.List(X.Atomic(int), 'wd')
        elt = td.xml_element(val, 'widths')
        self.assertEqual('<widths>%s</widths>' % ''.join('<wd>%d</wd>' % x for x in val),
                         to_unicode(elt))
        val_round_trip = td.extract_from(elt, 'widths')
        self.assertEqual(val, val_round_trip)

class BareRectangle(namedtuple('BareRectangle', 'width height')):
    pass

class Rectangle(namedtuple('BareRectangle', 'width height')):
    XML_Descriptor = X.SerDesDescriptor([('width', X.Atomic(int)),
                                         ('height', X.Atomic(int))])

class TestRectangleEquality(TestCase):
    def test_equality(self):
        r0 = Rectangle(42, 100)
        r1 = Rectangle(42, 100)
        self.assertIsNot(r0, r1)
        self.assertEqual(r0, r1)

class TestInstanceTypes(TestCase):
    def test_bad_construction(self):
        with self.assertRaisesRegexp(ValueError, 'has no XML_Descriptor'):
            bad_instance = X.Instance(BareRectangle)

    def test_1(self):
        td = X.Instance(Rectangle)
        rect = Rectangle(42, 100)
        elt = td.xml_element(rect, 'rect')
        self.assertEqual(expected_rect_xml(42, 100), to_unicode(elt))

        rect_round_trip = td.extract_from(elt, 'rect')
        self.assertEqual(rect, rect_round_trip)

    def test_bad_xml_wrong_n_children(self):
        td = X.Instance(Rectangle)
        bad_xml = etree.fromstring('<rect><a>42</a><b>100</b><c>123</c></rect>')
        with self.assertRaisesRegexp(ValueError,
                                     'expecting 2 children but got 3'):
            bad_rect = td.extract_from(bad_xml, 'rect')

    def test_bad_xml_wrong_tag(self):
        td = X.Instance(Rectangle)
        bad_xml = etree.fromstring('<rect><a>42</a><b>100</b></rect>')
        with self.assertRaisesRegexp(ValueError,
                                     'expected tag "width" but got "a"'):
            bad_rect = td.extract_from(bad_xml, 'rect')

class TestNumpyBase:
    def bad_value_1(self, x, regexp):
        with self.assertRaisesRegexp(ValueError, regexp):
            bad_elt = self.td.xml_element(x, 'values')

    def test_bad_values(self):
        self.bad_value_1('hello', 'not ndarray')
        self.bad_value_1(np.array([[1, 2], [3, 4]]), 'not 1-dimensional')
        self.bad_value_1(np.zeros((12,), dtype = np.float32), 'expecting dtype')

class TestNumpyAtomic(TestCase, TestNumpyBase):
    def setUp(self):
        self.td = X.NumpyAtomicVector(np.int32)

    def round_trip_1(self, dtype):
        xs = np.array([-1.23, -9.99, 0.234, 42, 99, 100.11], dtype = dtype)
        td = X.NumpyAtomicVector(dtype)
        elt = td.xml_element(xs, 'values')
        xs_round_trip = td.extract_from(elt, 'values')
        self.assertEqual(xs.shape, xs_round_trip.shape)
        self.assertTrue(np.all(xs_round_trip == xs))

    def test_round_trips(self):
        for dtype in [np.uint8, np.uint16, np.uint32, np.uint64,
                      np.int8, np.int16, np.int32, np.int64,
                      np.float32, np.float64]:
            self.round_trip_1(dtype)

    def test_content(self):
        xs = np.array([32, 42, 100, 99, -100], dtype = np.int32)
        elt = self.td.xml_element(xs, 'values')
        self.assertEqual('<values>32,42,100,99,-100</values>', to_unicode(elt))

class TestNumpyAtomicConvenience(TestNumpyAtomic):
    def setUp(self):
        self.td = X.NumpyVector(np.int32)

RectangleDType = np.dtype([('width', np.int32), ('height', np.int32)])

def remove_whitespace(s):
    return re.sub(r'\s+', '', s)

class TestNumpyRecordStructured(TestCase, TestNumpyBase):
    def setUp(self):
        self.td = X.NumpyRecordVectorStructured(RectangleDType, 'rect')

    def test_1(self):
        vals = np.array([(42, 100), (99, 12)], dtype = RectangleDType)
        xml_elt = self.td.xml_element(vals, 'rects')
        expected_xml = remove_whitespace(
            """<rects>
                 <rect><width>42</width><height>100</height></rect>
                 <rect><width>99</width><height>12</height></rect>
               </rects>""")
        self.assertEqual(expected_xml, to_unicode(xml_elt))
        vals_rt = self.td.extract_from(xml_elt, 'rects')
        self.assertEqual(vals.dtype, vals_rt.dtype)
        self.assertEqual(vals.shape, vals_rt.shape)
        self.assertTrue(np.all(vals_rt == vals))

class TestNumpyRecordStructuredConvenience(TestNumpyRecordStructured):
    def setUp(self):
        self.td = X.NumpyVector(RectangleDType, 'rect')

class TestDescriptors(TestCase):
    def setUp(self):
        self.rect = BareRectangle(42, 100)

    def do_tests(self, descriptor_elt, exp_tag):
        val = 42
        self.assertEqual(exp_tag, descriptor_elt.tag)
        self.assertEqual(val, descriptor_elt.value_from(self.rect))
        xml_elt = descriptor_elt.xml_element(self.rect)
        self.assertEqual('<%s>%d</%s>' % (exp_tag, val, exp_tag), to_unicode(xml_elt))
        round_trip_val = descriptor_elt.extract_from(xml_elt)
        self.assertEqual(val, round_trip_val)

    def test_from_pair(self):
        self.do_tests(X.ElementDescriptor.new_from_tuple(('width', X.Atomic(int))),
                      'width')

    def test_from_triple_attr_name(self):
        self.do_tests(X.ElementDescriptor.new_from_tuple(('wd', 'width', X.Atomic(int))),
                      'wd')

    def test_from_triple_function(self):
        self.do_tests(X.ElementDescriptor.new_from_tuple(('wd', lambda x: x.width, X.Atomic(int))),
                      'wd')

    def test_bad_construction(self):
        with self.assertRaisesRegexp(ValueError, 'length'):
            de = X.ElementDescriptor.new_from_tuple((1, 2, 3, 4))
        with self.assertRaises(TypeError):
            de = X.ElementDescriptor.new_from_tuple(42)





def expected_rect_xml(w, h):
    return '<rect><width>%d</width><height>%d</height></rect>' % (w, h)



class TestObject(TestCase):
    def setUp(self):
        self.rect = Rectangle(42, 123)

    def test_1(self):
        serialized_xml = X.Serialize(self.rect, 'rect')
        self.assertEqual(expected_rect_xml(42, 123),
                         to_unicode(serialized_xml))

        rect_round_trip = X.Deserialize(Rectangle, serialized_xml, 'rect')
        self.assertEqual(self.rect, rect_round_trip)

    def test_bad_n_children(self):
        bad_xml = etree.fromstring('<rect><width>99</width></rect>')
        with self.assertRaisesRegexp(ValueError, 'expecting 2 children but got 1'):
            bad_rect = X.Deserialize(Rectangle, bad_xml, 'rect')

    def test_bad_root_tag(self):
        bad_xml = etree.fromstring(expected_rect_xml(42, 100))
        with self.assertRaisesRegexp(ValueError, 'expected tag .* but got'):
            bad_rect = X.Deserialize(Rectangle, bad_xml, 'rectangle')


class Layout(namedtuple('Layout_', 'colour cornerprops stripes ids shape components')):
    XML_Descriptor = X.SerDesDescriptor(
        [('colour', X.Atomic(str)),
         ('corner-properties', 'cornerprops', X.List(X.List(X.Atomic(str), 'prop'), 'corner')),
         ('stripes', X.List(X.Atomic(str), 'stripe-colour')),
         ('product-id-codes', 'ids', X.NumpyAtomicVector(np.uint32)),
         ('shape', X.Instance(Rectangle)),
         ('components', X.NumpyRecordVectorStructured(RectangleDType, 'rect'))])

class TestComplexObject(TestCase):
    def test_1(self):
        layout = Layout('dark-blue',
                        [['rounded', 'red'],
                         ['chamfered', 'matt'],
                         ['pointy', 'anodized', 'black'],
                         ['bevelled', 'twisted', 'plastic-coated']],
                        ['red', 'burnt-ochre', 'orange'],
                        np.array([99, 42, 123], dtype = np.uint32),
                        Rectangle(210, 297),
                        np.array([(20, 30), (40, 50)], dtype = RectangleDType))
        xml = X.Serialize(layout, 'layout')
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
        self.assertEqual(expected_str, xml_str)
        layout_rt = X.Deserialize(Layout, xml, 'layout')






if __name__ == '__main__':
    unittest.main()
