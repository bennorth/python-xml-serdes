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
        return collections.OrderedDict(
            (elt_descr.tag, elt_descr.value_slot)
            for elt_descr in xml_descriptor
            if elt_descr.value_slot is not None)

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



class XMLSerializableNamedTupleMeta(XMLSerializableMeta):
    def __new__(meta, cls_name, bases, cls_dict):
        super_new = super(XMLSerializableNamedTupleMeta, meta).__new__
        xml_name = '_XML_' + cls_name
        xml_cls_dict = {'xml_descriptor': cls_dict['xml_descriptor']}
        xml_cls = super_new(meta, xml_name, (), xml_cls_dict)

        descr = xml_cls.xml_descriptor

        if len(xml_cls.slot_name_from_tag_name) != len(descr):
            raise ValueError('invalid xml_descriptor: all "value_from"s must be simple attributes')

        namedtuple_name = '_namedtuple_' + cls_name
        namedtuple_cls = collections.namedtuple(namedtuple_name,
                                                list(xml_cls.slot_name_from_tag_name.values()))

        cls_dict.pop('xml_descriptor')
        return type.__new__(meta, cls_name, (namedtuple_cls, xml_cls) + bases, cls_dict)


class XMLSerializableNamedTuple(six.with_metaclass(XMLSerializableNamedTupleMeta,
                                                   XMLSerializable)):
    xml_descriptor = []

    @classmethod
    def from_xml_dict(cls, ordered_dict):
        if list(ordered_dict.keys()) != list(cls.slot_name_from_tag_name.keys()):
            raise ValueError('tags in wrong order or wrong n. tags or sth')
        return cls._make(ordered_dict.values())
