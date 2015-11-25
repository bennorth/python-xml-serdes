# -*- coding: utf-8  -*-

from lxml import etree
import numpy as np
import re

import xmlserdes as X


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


class TestNamedTupleConstructor(object):
    def setup_method(self, method):
        xml_descriptor = X.SerDesDescriptor([('width', A_int32),
                                             ('height', A_int16),
                                             ('colour', A_str),
                                             ('stripes', X.NumpyAtomicVector(np.uint8))])
        self.FancyRectangle = X.NamedTuple('FancyRectangle', xml_descriptor)

    def test_class_properties(self):
        assert self.FancyRectangle.__name__ == 'FancyRectangle'
        assert self.FancyRectangle._fields == ('width', 'height', 'colour', 'stripes')

    def make_example(self):
        return self.FancyRectangle(99, 100, 'red', np.array([3, 4, 5], dtype=np.uint8))

    def test_construction(self):
        obj = self.make_example()
        assert obj.width == 99
        assert obj.height == 100
        assert obj.colour == 'red'
        assert list(obj.stripes) == [3, 4, 5]

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
        assert xml_str == exp_str

    def test_deserialization(self):
        xml_str = '''<fancy-rect>
                       <width>42</width>
                       <height>99</height>
                       <colour>blue</colour>
                       <stripes>30,40,50</stripes>
                     </fancy-rect>'''
        xml_elt = etree.fromstring(xml_str)
        obj = X.Deserialize(self.FancyRectangle, xml_elt, 'fancy-rect')
        assert obj.width == 42
        assert obj.height == 99
        assert obj.colour == 'blue'
        assert obj.stripes.dtype is np.dtype(np.uint8)
        assert obj.stripes.size == 3
        assert np.all(obj.stripes == np.array([30, 40, 50], dtype=np.uint8))
