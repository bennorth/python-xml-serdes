# -*- coding: utf-8  -*-

from __future__ import print_function

import collections

from xmlserdes.element_descriptor import ElementDescriptor
from xmlserdes.intrusive import XMLSerializable, XMLSerializableNamedTuple
from xmlserdes.type_descriptors import (
    TypeDescriptor, Atomic, AtomicBool, List, Instance, DTypeScalar, NumpyAtomicVector,
    NumpyRecordVectorStructured, NumpyVector)


def SerDesDescriptor(children):
    """
    Convenience function for constructing a list of
    :class:`xmlserdes.ElementDescriptor` instances from a list of
    abbreviated tuples.

    :param children: descriptions of property/sub-element mappings; each
        should be a tuple suitable for passing to
        :meth:`xmlserdes.ElementDescriptor.new_from_tuple`.

    :type children: iterable of tuples

    :return: New list of instances of :class:`xmlserdes.ElementDescriptor`.
    """

    return list(map(ElementDescriptor.new_from_tuple, children))


def serialize(obj, tag):
    """
    Entry point function to serialize a Python object to an XML element.

    :param obj: Python object to serialize
    :type obj: instance of class having ``xml_descriptor`` attribute

    :return: XML element, as instance of :class:`etree.Element`.
    """

    instance_td = Instance(obj.__class__)
    return instance_td.xml_element(obj, tag)


def deserialize(cls, elt, expected_tag):
    """
    Entry point function to deserialize a Python object from an XML element.

    :param cls: class of object to deserialize

    :param elt: XML element
    :type elt: :class:`etree.Element`

    :return: instance of class ``cls``.
    """

    instance_td = Instance(cls)
    return instance_td.extract_from(elt, expected_tag)


def namedtuple(name, xml_descriptor):
    """
    Define a class extended from :class:`collections.namedtuple` having
    fields matching those defined in ``xml_descriptor``.  The
    'extension' to the namedtuple class consists in setting its
    ``xml_descriptor`` attribute to the given ``xml_descriptor``.

    :param str name: the ``__name__`` of the defined class

    :type xml_descriptor: list of :class:`xmlserdes.ElementDescriptor` instances
    :param xml_descriptor: list of field definitions

    The field names of the resulting class are taken from the ``tag``
    fields of the individual :class:`xmlserdes.ElementDescriptor`
    instances within ``xml_descriptor``, and so the ``value_from`` field
    of each element-descriptor must be (equivalent to)
    ``attrgetter(tag)``.  This restriction might be lifted in future.
    """

    field_names = [ed.tag for ed in xml_descriptor]
    cls = collections.namedtuple(name, field_names)
    cls.xml_descriptor = xml_descriptor
    return cls
