import six

import collections

from xmlserdes.element_descriptor import ElementDescriptor
from xmlserdes.type_descriptors import Instance

import xmlserdes
import xmlserdes.utils
from xmlserdes.errors import XMLSerDesError


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
    """
    Base class for types which become serializable to XML via instance
    method ``as_xml``, and deserializable from XML via class method
    ``from_xml``.  XML behaviour is specified via an ``xml_descriptor``
    class attribute (of the derived class), which is a list of terse
    type-descriptor expressions --- see
    :meth:`xmlserdes.TypeDescriptor.from_terse` for details.
    """

    xml_descriptor = []

    def as_xml(self, tag=None):
        """
        Return an XML element representing ``self``.  The element has
        tag ``tag``, or if that is omitted (or ``None``), the
        ``xml_default_tag`` attribute of ``self``'s class.
        """

        tag = tag or self.xml_default_tag
        instance_td = Instance(self.__class__)  # TODO: Cache this t.d. in class?
        return instance_td.xml_element(self, tag)

    def as_xml_str(self, tag=None, **kwargs):
        """
        Return an XML element representing ``self`` rendered as string. Defaults to
        pretty printing unless specified otherwise.
        """
        kwargs['pretty_print'] = kwargs.get('pretty_print', True)
        return xmlserdes.utils.str_from_xml_elt(self.as_xml(tag=tag), **kwargs)

    @classmethod
    def from_xml(cls, xml_elt, expected_tag):
        """
        Return a new instance of ``cls`` by deserializing the given XML
        element, which must have the given expected tag.  The real work
        is done by a class method ``from_xml_dict``, which the derived
        class must provide.
        """

        if xml_elt.tag != expected_tag:
            raise XMLSerDesError('expected tag "%s" but got "%s"'
                                 % (expected_tag, xml_elt.tag))

        ordered_dict = cls._ordered_dict_from_xml(xml_elt)
        # Might throw exception if class doesn't care about deserialization:
        return cls.from_xml_dict(ordered_dict)

    @classmethod
    def _ordered_dict_from_xml(cls, xml_elt):
        descr = cls.xml_descriptor
        if len(xml_elt) != len(descr):
            raise XMLSerDesError('expected %d children but got %d'
                                 % (len(descr), len(xml_elt)))

        return collections.OrderedDict(
            (child_elt.tag, descr_elt.extract_from(child_elt))
            for child_elt, descr_elt in zip(xml_elt, descr))


class XMLSerializableNamedTupleMeta(XMLSerializableMeta):
    def __new__(meta, cls_name, bases, cls_dict):
        if 'xml_descriptor' not in cls_dict:
            raise ValueError('no "xml_descriptor" in "%s"' % cls_name)

        super_new = super(XMLSerializableNamedTupleMeta, meta).__new__
        xml_name = '_XML_' + cls_name
        xml_cls_dict = {'xml_descriptor': cls_dict['xml_descriptor']}
        xml_cls = super_new(meta, xml_name, (), xml_cls_dict)

        descr = xml_cls.xml_descriptor

        if len(xml_cls.slot_name_from_tag_name) != len(descr):
            raise ValueError('invalid xml_descriptor: all "value_from"s must be simple attributes')

        namedtuple_cls = collections.namedtuple(cls_name,
                                                list(xml_cls.slot_name_from_tag_name.values()))

        cls_dict.pop('xml_descriptor')
        return type.__new__(meta, cls_name, (namedtuple_cls, xml_cls) + bases, cls_dict)


class XMLSerializableNamedTuple(six.with_metaclass(XMLSerializableNamedTupleMeta,
                                                   XMLSerializable)):
    """
    Base class for types which are essentially named tuples with the
    field-names taken from the ``xml_descriptor``.

    >>> class Rectangle(xmlserdes.XMLSerializableNamedTuple):
    ...     xml_default_tag = 'rect'
    ...     xml_descriptor = [('wd', int), ('ht', int)]
    >>> r = Rectangle(10, 20)
    >>> print(r)
    Rectangle(wd=10, ht=20)
    >>> r.wd
    10
    >>> r.ht
    20
    >>> print(xmlserdes.utils.str_from_xml_elt(r.as_xml()))
    <rect><wd>10</wd><ht>20</ht></rect>
    """

    xml_descriptor = []

    @classmethod
    def _verify_children(cls, ordered_dict):
        tags_got = list(ordered_dict.keys())
        tags_exp = list(cls.slot_name_from_tag_name.keys())
        if tags_got != tags_exp:
            if len(tags_got) != len(tags_exp):
                raise XMLSerDesError('expected %d children but got %d'
                                     % (len(tags_exp), len(tags_got)))
            differing_tags = [
                (idx, expected, got)
                for (idx, (expected, got)) in enumerate(zip(tags_exp, tags_got))
                if expected != got]
            first_diff = differing_tags[0]
            raise XMLSerDesError(('unexpected tags: %d differ; first diff:'
                                  + ' expected "%s" but got "%s" at posn %d')
                                 % (len(differing_tags),
                                    first_diff[1], first_diff[2], first_diff[0]))

    @classmethod
    def from_xml_dict(cls, ordered_dict):
        cls._verify_children(ordered_dict)
        return cls._make(ordered_dict.values())
