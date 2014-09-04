from collections import namedtuple
from operator import attrgetter

import numpy as np
from lxml import etree

AtomicTypes = (int, float, str,
               np.int8, np.int16, np.int32, np.int64,
               np.uint8, np.uint16, np.uint32, np.uint64)

class DescriptorElement(namedtuple('_DescriptorElement', 'tag value_from type_descr')):
    # TODO Better names.  'SimpleDescriptor', 'CompoundDescriptor'? Sth to indicate
    # that Descriptor (below) knows how to construct a class from the tuple?  If it does.
    @classmethod
    def new_from_tuple(cls, tup):
        if len(tup) == 2:
            tag, td = tup
            return cls(tag, attrgetter(tag), td)
        elif len(tup) == 3:
            tag, vf, td = tup
            if isinstance(vf, str):
                vf = attrgetter(vf)
            return cls(tag, vf, td)
        else:
            raise ValueError('bad tuple length')

    def xml_element(self, obj):
        return self.type_descr.xml_element(self.value_from(obj), self.tag)

    def extract_from(self, elt):
        return self.type_descr.extract_from(elt, self.tag)


class Descriptor(namedtuple('_Descriptor', 'children')):
    # TODO: Add 'ctor_name' slot
    @classmethod
    def new_from_abbreviated_args(cls, *args):
        raw_descriptor = cls._make(args)
        return raw_descriptor._replace(children = map(DescriptorElement.new_from_tuple,
                                                      raw_descriptor.children))

SerDesDescriptor = Descriptor.new_from_abbreviated_args

class TypeDescriptor(object):
    def verify_tag(self, elt, expected_tag):
        if elt.tag != expected_tag:
            raise ValueError('expected tag "%s" but got "%s"'
                             % (expected_tag, elt.tag))

class Atomic(TypeDescriptor):
    def __init__(self, inner_type):
        self.inner_type = inner_type

    def xml_element(self, obj, tag):
        elt = etree.Element(tag)
        elt.text = str(obj)
        return elt

    def extract_from(self, elt, expected_tag):
        self.verify_tag(elt, expected_tag)
        return self.inner_type(elt.text)

class List(TypeDescriptor):
    def __init__(self, contained_descriptor, contained_tag):
        self.contained_descriptor = contained_descriptor
        self.contained_tag = contained_tag

    def xml_element(self, obj, tag):
        elt = etree.Element(tag)
        for obj_elt in obj:
            elt.append(self.contained_descriptor.xml_element(obj_elt, self.contained_tag))
        return elt

    def extract_from(self, elt, expected_tag):
        self.verify_tag(elt, expected_tag)
        return [self.contained_descriptor.extract_from(child_elt, self.contained_tag)
                for child_elt in elt]

class Instance(TypeDescriptor):
    def __init__(self, cls):
        if not hasattr(cls, 'XML_Descriptor'):
            raise ValueError('class "%s" has no XML_Descriptor' % cls.__name__)

        self.cls = cls

    def xml_element(self, obj, tag):
        elt = etree.Element(tag)
        for child in self.cls.XML_Descriptor.children:
            child_elt = child.xml_element(obj)
            elt.append(child_elt)
        return elt

    def extract_from(self, elt, expected_tag):
        self.verify_tag(elt, expected_tag)
        descr = self.cls.XML_Descriptor
        if len(elt) != len(descr.children):
            raise ValueError('XML element has %d children but expecting %d'
                             % (len(elt), len(descr.children)))

        # TODO: Allow alternative constructors
        ctor = self.cls
        ctor_args = [descr_elt.extract_from(child_elt)
                     for child_elt, descr_elt in zip(elt, descr.children)]

        return ctor(*ctor_args)

class NumpyVectorBase(TypeDescriptor):
    def xml_element(self, obj, tag):
        if not isinstance(obj, np.ndarray):
            raise ValueError('object not ndarray')
        if obj.ndim != 1:
            raise ValueError('ndarray not 1-dimensional')
        if obj.dtype != self.dtype:
            raise ValueError('expecting dtype "%s" but got "%s"'
                             % (obj.dtype, self.dtype))

        elt = etree.Element(tag)
        self.populate_element(elt, obj)
        return elt

    def extract_from(self, elt, expected_tag):
        self.verify_tag(elt, expected_tag)
        elements_list = self.extract_elements_list(elt)
        return np.array(elements_list, dtype = self.dtype)

class NumpyAtomicVector(NumpyVectorBase):
    def __init__(self, dtype):
        self.dtype = dtype

    def populate_element(self, elt, xs):
        elt.text = ','.join(map(repr, xs))

    def extract_elements_list(self, elt):
        s_elts = elt.text.split(',')
        return map(self.dtype, s_elts)

class NumpyRecordVectorStructured(NumpyVectorBase):
    def __init__(self, dtype, contained_tag):
        self.dtype = dtype
        self.n_fields = len(dtype)
        self.type_ctors = [dtype.fields[n][0].type for n in dtype.names]
        self.contained_tag = contained_tag

    def entry_element(self, x):
        elt = etree.Element(self.contained_tag)
        for n, v in zip(self.dtype.names, x):
            # TODO: Allow different XML tags vs names of dtype fields.
            field_elt = etree.SubElement(elt, n)
            field_elt.text = repr(v)
        return elt

    def populate_element(self, elt, xs):
        for record in xs:
            elt.append(self.entry_element(record))

    def extract_entry_element(self, subelt):
        if len(subelt) != self.n_fields:
            raise ValueError('expected %d sub-elements but got %d'
                             % (self.n_fields, len(subelt)))

        values = [None] * self.n_fields
        for i, field_name in enumerate(self.dtype.names):
            child = subelt[i]
            if child.tag != field_name:
                raise ValueError('expected tag "%s" but got "%s" for child %d'
                                 % (field_name, child.tag, i))
            values[i] = self.type_ctors[i](child.text)
        return tuple(values)

    def extract_elements_list(self, elt):
        return map(self.extract_entry_element, elt)

def NumpyVector(dtype, contained_tag = None):
    return (NumpyAtomicVector(dtype) if contained_tag is None
            else NumpyRecordVectorStructured(dtype, contained_tag))

def Serialize(obj, tag):
    instance_td = Instance(obj.__class__)
    return instance_td.xml_element(obj, tag)

def Deserialize(cls, elt, expected_tag):
    instance_td = Instance(cls)
    return instance_td.extract_from(elt, expected_tag)
