# -*- coding: utf-8  -*-

import pytest

import collections
import itertools

from lxml import etree
import numpy as np
import xmlserdes as X
import xmlserdes.utils as XU

make_TD = X.TypeDescriptor.from_terse

import re


def list_product(*args):
    return list(itertools.product(*args))


class TestAtomicTypes(object):
    @pytest.mark.parametrize('td_func',
                             [X.Atomic, make_TD],
                             ids=['verbose', 'terse'])
    #
    def test_type_descriptor(self, td_func):
        for tp, val, exp_txt in [(int, 42, '42'),
                                 (float, 3.5, '3.5'),
                                 (str, '3 < 5', '3 &lt; 5'),
                                 (np.uint8, np.uint8(42), '42')]:
            td = td_func(tp)
            elt = td.xml_element(val, 'foo')
            assert XU.str_from_xml_elt(elt) == '<foo>%s</foo>' % exp_txt
            val_round_trip = td.extract_from(elt, 'foo')
            assert type(val_round_trip) is tp
            assert val_round_trip == val

    @pytest.mark.parametrize(
        'dtype_str',
        ['i1', 'i2', 'i4', 'u1', 'u2', 'u4'])
    #
    def test_terse_string_descriptors(self, dtype_str):
        td = make_TD(dtype_str)
        tp = np.dtype(dtype_str).type

        elt = td.xml_element(19, 'foo')
        assert '<foo>19</foo>' == XU.str_from_xml_elt(elt)
        val_round_trip = td.extract_from(elt, 'foo')
        assert tp is type(val_round_trip)
        assert val_round_trip == 19

    def test_bad_terse_string_descriptors(self):
        with pytest.raises_regexp(TypeError, 'data type .* not understood'):
            make_TD('not-a-real-dtype-code')

    def test_bool(self):
        td = make_TD(bool)

        elt = td.xml_element(True, 'foo')
        assert XU.str_from_xml_elt(elt) == '<foo>true</foo>'
        assert td.extract_from(elt, 'foo') is True

        elt = td.xml_element(False, 'foo')
        assert XU.str_from_xml_elt(elt) == '<foo>false</foo>'
        assert td.extract_from(elt, 'foo') is False

    def test_bool_bad_serialize_values(self):
        td = make_TD(bool)

        with pytest.raises_regexp(ValueError, 'expected True or False but got "42"'):
            td.xml_element(42, 'foo')

    def test_bool_bad_deserialize_values(self):
        td = make_TD(bool)

        with pytest.raises_regexp(ValueError,
                                  'expected text "true" or "false" but got "banana"'):
            #
            bad_xml = etree.fromstring('<foo>banana</foo>')
            td.extract_from(bad_xml, 'foo')


class BareRectangle(collections.namedtuple('BareRectangle', 'width height')):
    pass


class TestListTypes(object):
    @pytest.mark.parametrize('td',
                             [X.List(X.Atomic(int), 'wd'),
                              make_TD([int, 'wd'])],
                             ids=['verbose', 'terse'])
    #
    def test_type_descriptor(self, td):
        val = [42, 100, 99, 123]
        elt = td.xml_element(val, 'widths')
        assert XU.str_from_xml_elt(elt) == \
               '<widths>%s</widths>' % ''.join('<wd>%d</wd>' % x for x in val)
        val_round_trip = td.extract_from(elt, 'widths')
        assert val_round_trip == val

    @pytest.mark.parametrize('list_descr,exc_re',
                             [([1, 2, 3], 'expected 1 or 2 elements'),
                              ([], 'expected 1 or 2 elements'),
                              ([BareRectangle], '1-elt list: .* has no "xml_default_tag"')],
                             ids=['three-elt', 'empty', 'no-default-tag'])
    #
    def test_bad_construction(self, list_descr, exc_re):
        with pytest.raises_regexp(ValueError, exc_re):
            make_TD(list_descr)


class TestNestedListTypes(object):
    @pytest.mark.parametrize('td',
                             [X.List(X.List(X.Atomic(int), 'wd'), 'stripe-group'),
                              make_TD([[int, 'wd'], 'stripe-group'])],
                             ids=['verbose', 'terse'])
    #
    def test_type_descriptor(self, td):
        groups = [[1, 2], [3, 4, 5]]

        elt = td.xml_element(groups, 'stripe-groups')

        exp_txt = ('<stripe-groups>%s</stripe-groups>'
                   % ''.join(('<stripe-group>%s</stripe-group>'
                              % ''.join('<wd>%d</wd>' % x for x in grp))
                             for grp in groups))

        assert exp_txt == XU.str_from_xml_elt(elt)

        groups_round_trip = td.extract_from(elt, 'stripe-groups')
        assert groups == groups_round_trip


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

    @pytest.mark.parametrize('td',
                             [X.Instance(Rectangle),
                              make_TD(Rectangle)],
                             ids=['verbose', 'terse'])
    #
    def test_type_descriptor(self, td):
        rect = Rectangle(42, 100)
        elt = td.xml_element(rect, 'rect')
        assert XU.str_from_xml_elt(elt) == expected_rect_xml(42, 100)

        rect_round_trip = td.extract_from(elt, 'rect')
        assert rect_round_trip == rect

    @pytest.mark.parametrize(
        'xml_str,err_re',
        [('<rect><a>42</a><b>100</b><c>123</c></rect>', 'expected 2 children but got 3'),
         ('<rect><a>42</a><b>100</b></rect>', 'expected tag "width" but got "a"')],
        ids=['wrong-n-children', 'wrong-tag'])
    #
    def test_bad_xml(self, xml_str, err_re):
        td = X.Instance(Rectangle)
        bad_xml = etree.fromstring(xml_str)
        with pytest.raises_regexp(ValueError, err_re):
            td.extract_from(bad_xml, 'rect')


class _TestNumpyBase(object):
    @pytest.mark.parametrize(
        'x,regexp',
        [('hello', 'not ndarray'),
         (np.array([[1, 2], [3, 4]]), 'not 1-dimensional'),
         (np.zeros((12,), dtype=np.float32), 'expected dtype')],
        ids=['string', 'multi-dml', 'wrong-dtype'])
    #
    def test_bad_value(self, x, regexp):
        with pytest.raises_regexp(ValueError, regexp):
            self.td.xml_element(x, 'values')


class TestNumpyAtomic(_TestNumpyBase):
    def setup_method(self, method):
        self.td = X.NumpyAtomicVector(np.int32)

    def round_trip_1(self, xs, td):
        elt = td.xml_element(xs, 'values')
        xs_round_trip = td.extract_from(elt, 'values')
        assert xs_round_trip.shape == xs.shape
        assert np.all(xs_round_trip == xs)

    dtypes_to_test = [np.uint8, np.uint16, np.uint32, np.uint64,
                      np.int8, np.int16, np.int32, np.int64,
                      np.float32, np.float64]

    @pytest.mark.parametrize(
        'dtype,td_func',
        list_product(dtypes_to_test,
                     [X.NumpyAtomicVector, lambda dt: make_TD((np.ndarray, dt))]),
        ids=['-'.join(flds)
             for flds in list_product([dt.__name__ for dt in dtypes_to_test],
                                      ['verbose', 'terse'])])
    #
    def test_round_trips(self, dtype, td_func):
        xs = np.array([-1.23, -9.99, 0.234, 42, 99, 100.11], dtype=dtype)
        self.round_trip_1(xs, td_func(dtype))

    def test_content(self):
        xs = np.array([32, 42, 100, 99, -100], dtype=np.int32)
        elt = self.td.xml_element(xs, 'values')
        assert XU.str_from_xml_elt(elt) == '<values>32,42,100,99,-100</values>'


class TestNumpyAtomicConvenience(TestNumpyAtomic):
    def setup_method(self, method):
        self.td = X.NumpyVector(np.int32)


RectangleDType = np.dtype([('width', np.int32), ('height', np.int32)])

RectanglePairDType = np.dtype([('big', RectangleDType), ('small', RectangleDType)])


def remove_whitespace(s):
    return re.sub(r'\s+', '', s)


class TestNumpyRecordStructured(_TestNumpyBase):
    type_descr = X.NumpyRecordVectorStructured(RectangleDType, 'rect')

    def setup_method(self, method):
        self.td = TestNumpyRecordStructured.type_descr
        self.vals = np.array([(42, 100), (99, 12)], dtype=RectangleDType)

    @pytest.mark.parametrize('td',
                             [type_descr, make_TD((np.ndarray, RectangleDType, 'rect'))],
                             ids=['verbose', 'terse'])
    #
    def test_type_descriptor(self, td):
        xml_elt = td.xml_element(self.vals, 'rects')
        expected_xml = remove_whitespace(
            """<rects>
                 <rect><width>42</width><height>100</height></rect>
                 <rect><width>99</width><height>12</height></rect>
               </rects>""")
        assert XU.str_from_xml_elt(xml_elt) == expected_xml
        vals_rt = td.extract_from(xml_elt, 'rects')
        assert vals_rt.dtype == self.vals.dtype
        assert vals_rt.shape == self.vals.shape
        assert np.all(vals_rt == self.vals)

    @pytest.mark.parametrize(
        'bad_inner_str,exc_re',
        [('<rect><width>42</width><height>100</height><depth>99</depth></rect>',
          'expected 2 sub-elements but got 3'),
         ('<rect><wd>42</wd><ht>100</ht></rect>',
          'expected tag "width" but got "wd"')],
        ids=['wrong-n-elts', 'wrong-child-tag'])
    #
    def test_bad_xml(self, bad_inner_str, exc_re):
        bad_str = '<rect>%s</rect>' % bad_inner_str
        bad_xml = etree.fromstring(bad_str)
        with pytest.raises_regexp(ValueError, exc_re):
            self.td.extract_from(bad_xml, 'rect')


class TestNumpyDTypeScalar(object):
    atomics_td = X.DTypeScalar(RectangleDType)
    atomics_val = np.array((42, 100), dtype=RectangleDType)[()]
    atomics_exp = '<rect><width>42</width><height>100</height></rect>'

    nested_td = X.DTypeScalar(RectanglePairDType)
    nested_val = np.array(((42, 100), (4, 10)), dtype=RectanglePairDType)[()]
    nested_exp = remove_whitespace(
        """<rect-pair>
               <big><width>42</width><height>100</height></big>
               <small><width>4</width><height>10</height></small>
           </rect-pair>""")

    @pytest.mark.parametrize(
        'type_descr,val,exp_xml,tag',
        [(atomics_td, atomics_val, atomics_exp, 'rect'),
         (nested_td, nested_val, nested_exp, 'rect-pair')],
        ids=['atomics', 'nested'])
    #
    def test_round_trip(self, type_descr, val, exp_xml, tag):
        assert val.shape == ()

        xml_elt = type_descr.xml_element(val, tag)
        assert XU.str_from_xml_elt(xml_elt) == exp_xml

        val_rt = type_descr.extract_from(xml_elt, tag)
        assert type(val_rt) == np.ndarray
        assert val_rt.dtype == val.dtype
        assert val_rt.shape == val.shape
        assert val_rt == val

    ColourDType = np.dtype([('r', np.uint8), ('g', np.uint8), ('b', np.uint8)])

    @pytest.mark.parametrize(
        'x,regexp',
        [('hello', 'not numpy scalar'),
         (np.array([1, 2]), 'not numpy scalar'),
         (np.array([[1, 2], [3, 4]]), 'not numpy scalar'),
         (np.array((12,), dtype=np.float32)[()], 'not numpy scalar'),
         (np.array((10, 20, 30), dtype=ColourDType)[()], 'expected dtype')],
        ids=['string', 'vector', 'multi-dml', 'wrong-dtype-atomic', 'wrong-dtype-structured'])
    #
    def test_bad_value(self, x, regexp):
        with pytest.raises_regexp(ValueError, regexp):
            self.atomics_td.xml_element(x, 'values')


class TestNumpyRecordStructuredNested(object):
    type_descr = X.NumpyRecordVectorStructured(RectanglePairDType, 'rect-pair')
    vals = np.array([((420, 100), (42, 10)), ((430, 110), (43, 11))],
                    dtype=RectanglePairDType)

    def test_round_trip(self):
        xml_elt = self.type_descr.xml_element(self.vals, 'rect-pairs')
        expected_xml = remove_whitespace(
            """<rect-pairs>
                 <rect-pair>
                     <big><width>420</width><height>100</height></big>
                     <small><width>42</width><height>10</height></small>
                 </rect-pair>
                 <rect-pair>
                     <big><width>430</width><height>110</height></big>
                     <small><width>43</width><height>11</height></small>
                 </rect-pair>
               </rect-pairs>""")
        assert expected_xml == XU.str_from_xml_elt(xml_elt)
        vals_rt = self.type_descr.extract_from(xml_elt, 'rect-pairs')
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

    @pytest.mark.parametrize(
        'descriptor_tup,exp_tag,exp_vslot',
        [(('width', X.Atomic(int)), 'width', 'width'),
         (('wd', 'width', X.Atomic(int)), 'wd', 'width'),
         (('wd', (lambda x: x.width), X.Atomic(int)), 'wd', None)],
        ids=['pair', 'triple-attr-name', 'triple-function'])
    #
    def test_tuple_construction(self, descriptor_tup, exp_tag, exp_vslot):
        elt_descriptor = X.ElementDescriptor.new_from_tuple(descriptor_tup)
        val = 42
        assert elt_descriptor.tag == exp_tag
        assert elt_descriptor.value_from(self.rect) == val
        assert elt_descriptor.value_slot == exp_vslot
        xml_elt = elt_descriptor.xml_element(self.rect)
        assert XU.str_from_xml_elt(xml_elt) == '<%s>%d</%s>' % (exp_tag, val, exp_tag)
        round_trip_val = elt_descriptor.extract_from(xml_elt)
        assert round_trip_val == val

    @pytest.mark.parametrize(
        'bad_arg,exc_tp,exc_re',
        [((1, 2, 3, 4), ValueError, 'length'),
         (42, TypeError, 'object .* has no len')],
        ids=['wrong-length', 'wrong-type'])
    #
    def test_bad_construction(self, bad_arg, exc_tp, exc_re):
        with pytest.raises_regexp(exc_tp, exc_re):
            X.ElementDescriptor.new_from_tuple(bad_arg)


def expected_rect_xml(w, h):
    return '<rect><width>%d</width><height>%d</height></rect>' % (w, h)


class TestObject(object):
    def setup_method(self, method):
        self.rect = Rectangle(42, 123)

    def test_1(self):
        serialized_xml = X.serialize(self.rect, 'rect')
        assert XU.str_from_xml_elt(serialized_xml) == expected_rect_xml(42, 123)

        rect_round_trip = X.deserialize(Rectangle, serialized_xml, 'rect')
        assert rect_round_trip == self.rect

    @pytest.mark.parametrize(
        'xml_str,des_tag,exc_re',
        [('<rect><width>99</width></rect>', 'rect', 'expected 2 children but got 1'),
         (expected_rect_xml(42, 100), 'rectangle', 'expected tag .* but got')],
        ids=['wrong-n-children', 'wrong-tag'])
    #
    def test_bad_input(self, xml_str, des_tag, exc_re):
        bad_xml = etree.fromstring(xml_str)
        with pytest.raises_regexp(ValueError, exc_re):
            X.deserialize(Rectangle, bad_xml, des_tag)


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
        xml_str = XU.str_from_xml_elt(xml)
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


class TestTerseErrorInputs(object):
    @pytest.mark.parametrize(
        'bad_tup,exc_re',
        [((), 'empty tuple'),
         ((42, 'hello', 'world'), 'numpy.ndarray as first'),
         ((np.ndarray, BareRectangle), 'atomic numpy type as second'),
         ((np.ndarray, 'foo', 'bar'), 'numpy dtype as second'),
         ((np.ndarray, 2, 3, 4), 'expected 2 or 3 elements but got 4')],
        ids=['empty', 'wrong-first-elt', '2-elt-not-dtype', '3-elt-not-dtype', 'wrong-length'])
    #
    def test_numpy_descriptor(self, bad_tup, exc_re):
        with pytest.raises_regexp(ValueError, exc_re):
            make_TD(bad_tup)
