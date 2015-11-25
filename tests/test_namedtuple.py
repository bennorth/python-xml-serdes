# -*- coding: utf-8  -*-

from lxml import etree
import numpy as np
import re

import XMLserdes as X

import unittest
from unittest import TestCase

A_int16 = X.Atomic(np.int16)
A_int32 = X.Atomic(np.int32)
A_str = X.Atomic(str)

try:
    etree_encoding = unicode
except NameError:
    etree_encoding = str


def to_unicode(elt):
    return etree.tostring(elt, encoding=etree_encoding)


def remove_whitespace(s):
    return re.sub(r'\s+', '', s)

class TestNamedTupleConstructor(TestCase):
    def setUp(self):
        xml_descriptor = X.SerDesDescriptor([('width', A_int32),
                                             ('height', A_int16),
                                             ('colour', A_str),
                                             ('stripes', X.NumpyAtomicVector(np.uint8))])
        self.FancyRectangle = X.NamedTuple('FancyRectangle', xml_descriptor)

    def test_class_properties(self):
        self.assertEqual('FancyRectangle', self.FancyRectangle.__name__)
        self.assertEqual(('width', 'height', 'colour', 'stripes'),
                         self.FancyRectangle._fields)

    def make_example(self):
        return self.FancyRectangle(99, 100, 'red', np.array([3, 4, 5], dtype=np.uint8))

    def test_construction(self):
        obj = self.make_example()
        self.assertEqual(99, obj.width)
        self.assertEqual(100, obj.height)
        self.assertEqual('red', obj.colour)
        self.assertEqual([3, 4, 5], list(obj.stripes))

    def test_serialization(self):
        obj = self.make_example()
        xml_elt = X.Serialize(obj, 'fancy-rect')
        xml_str = to_unicode(xml_elt)
        exp_str = remove_whitespace(
            '''<fancy-rect>
                 <width>99</width>
                 <height>100</height>
                 <colour>red</colour>
                 <stripes>3,4,5</stripes>
               </fancy-rect>''')
        self.assertEqual(exp_str, xml_str)

    def test_deserialization(self):
        xml_str = '''<fancy-rect>
                       <width>42</width>
                       <height>99</height>
                       <colour>blue</colour>
                       <stripes>30,40,50</stripes>
                     </fancy-rect>'''
        xml_elt = etree.fromstring(xml_str)
        obj = X.Deserialize(self.FancyRectangle, xml_elt, 'fancy-rect')
        self.assertEqual(42, obj.width)
        self.assertEqual(99, obj.height)
        self.assertEqual('blue', obj.colour)
        self.assertEqual(np.uint8, obj.stripes.dtype)
        self.assertEqual(3, obj.stripes.size)
        self.assertTrue(np.all(np.array([30, 40, 50], dtype = np.uint8) == obj.stripes))


if __name__ == '__main__':
    unittest.main()
