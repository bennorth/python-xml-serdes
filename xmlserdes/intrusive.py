import six

import collections

from xmlserdes.element_descriptor import ElementDescriptor
from xmlserdes.type_descriptors import Instance

class XMLSerializableMeta(type):
    @classmethod
    def _expand(meta, xml_descriptor):
        return list(map(ElementDescriptor.new_from_tuple, xml_descriptor))

    @classmethod
    def build_map_as_ordered_dict(meta, xml_descriptor):
        # Work-in-progress
        return None

    def __new__(meta, cls_name, bases, cls_dict):
        xml_descriptor = meta._expand(cls_dict['xml_descriptor'])
        cls_dict['xml_descriptor'] = xml_descriptor

        # Build map tag-name -> slot-name where 'slot-name' makes
        # sense, i.e., from_value is string not callable.  WiP.
        cls_dict['slot_name_from_tag_name'] = meta.build_map_as_ordered_dict(xml_descriptor)

        cls = super(XMLSerializableMeta, meta).__new__(meta, cls_name, bases, cls_dict)

        # Any further checks on cls here?
        return cls


class XMLSerializable(six.with_metaclass(XMLSerializableMeta)):
    xml_descriptor = []

    def as_xml(self, tag=None):
        tag = tag or self.xml_default_tag
        instance_td = Instance(self.__class__) # TODO: Cache this t.d. in class?
        return instance_td.xml_element(self, tag)

    @classmethod
    def from_xml(cls, xml_elt, expected_tag):
        ordered_dict = cls._ordered_dict_from_xml(xml_elt)
        # Might throw exception if class doesn't care about deserialization:
        return cls.from_xml_dict(ordered_dict)

    @classmethod
    def _ordered_dict_from_xml(cls, xml_elt):
        descr = cls.xml_descriptor
        if len(xml_elt) != len(descr):
            raise ValueError('expecting %d children but got %d'
                             % (len(descr), len(elt)))

        return collections.OrderedDict(
            (child_elt.tag, descr_elt.extract_from(child_elt))
            for child_elt, descr_elt in zip(xml_elt, descr))



########################################################################
# Work-in-progress beyond this point.
########################################################################

class XMLSerializableNamedTupleMeta(type):
    def __new__(meta, cls_name, bases, cls_dict):
        namedtuple_base = collections.namedtuple('_' + cls_name,
                                                 [])
                                                 #[field_names from xml_descriptor])

        # Check all slots are value_from strings

        # Might make sense to require no other bases besides XMLSerializableNamedTuple?
        bases.insert(0, namedtuple_base)

        return super(XMLSerializableNamedTupleMeta, meta).__new__(meta, cls_name, bases, cls_dict)


class XMLSerializableNamedTuple(XMLSerializable):
    xml_descriptor = []

    @classmethod
    def from_xml_dict(cls, ordered_dict):
        # Keys of ordered_dict are xml tag names.
        if ordered_dict.keys() != cls.slot_name_from_tag_name.keys():
            raise ValueError('tags in wrong order or wrong n. tags or sth')
        obj = cls(ordered_dict.values())


"""
  [('OpeningClosingRAMSelect', 'i2'), # Strings interpreted as numpy dtype codes? Avoids 'import numpy'
   ('StartAddress', np.uint16), # Or this still works
   ('ThresholdValue', (np.ndarray, np.int32)), # ndim is 1 by default or only support 1-dml?
   ('Rectangles', (np.ndarray, RectDType, 'rect')), # ndim is 1 by default or only support 1-dml?
   ('Rectangle', Rectangle), # Check at class construction time that Rectangle is derived from our magic base class
   ('ThresholdValue', (np.ndarray, np.int32, 2))] # comma- then semicolon-separated?  or dimension tags?
"""
