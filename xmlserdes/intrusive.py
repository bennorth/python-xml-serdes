import six

import collections

from xmlserdes.element_descriptor import ElementDescriptor
from xmlserdes.type_descriptors import Instance

import xmlserdes
import xmlserdes.utils
from xmlserdes.errors import XMLSerDesError, XMLSerDesWrongChildrenError


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

    @classmethod
    def _find_xml_descriptor(meta, cls_name, bases, cls_dict):
        """
        Find an 'xml_descriptor' attribute, first by looking within the direct
        ``cls_dict``, and then the ``bases``.  Return the pair

            ``descriptor``, ``inherited_p``

        where ``descriptor`` is the value of the ``xml_descriptor`` attribute found, and
        ``inherited_p`` indicates whether the attribute was found somewhere in
        ``bases``.  (And so ``inherited_p`` is false if the ``xml_descriptor`` attribute
        was found directly in ``cls_dict``.)

        If no ``xml_descriptor`` is found anywhere, raise a ``ValueError``.
        """
        if 'xml_descriptor' in cls_dict:
            return cls_dict['xml_descriptor'], False

        for b in bases:
            if hasattr(b, 'xml_descriptor'):
                return getattr(b, 'xml_descriptor'), True

        raise ValueError('no "xml_descriptor" in "%s"' % cls_name)

    def __new__(meta, cls_name, bases, cls_dict):
        raw_xml_descriptor, inherited_p = meta._find_xml_descriptor(cls_name, bases, cls_dict)
        xml_descriptor = raw_xml_descriptor if inherited_p else meta._expand(raw_xml_descriptor)
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
        return instance_td.xml_element(self, tag, [tag])

    def as_xml_str(self, tag=None, **kwargs):
        """
        Return an XML element representing ``self`` rendered as string. Defaults to
        pretty printing unless specified otherwise.
        """
        kwargs['pretty_print'] = kwargs.get('pretty_print', True)
        return xmlserdes.utils.str_from_xml_elt(self.as_xml(tag=tag), **kwargs)

    @classmethod
    def from_xml(cls, xml_elt, expected_tag, _xpath=[]):
        """
        Return a new instance of ``cls`` by deserializing the given XML
        element, which must have the given expected tag.  The real work
        is done by a class method ``from_xml_dict``, which the derived
        class must provide.
        """

        _xpath = _xpath or [expected_tag]
        if xml_elt.tag != expected_tag:
            raise XMLSerDesError('expected tag "%s" but got "%s"'
                                 % (expected_tag, xml_elt.tag),
                                 xpath=_xpath[:-1])

        ordered_dict = cls._ordered_dict_from_xml(xml_elt, _xpath)
        # Might throw exception if class doesn't care about deserialization:
        return cls.from_xml_dict(ordered_dict, _xpath)

    @classmethod
    def _ordered_dict_from_xml(cls, xml_elt, _xpath):
        descr = cls.xml_descriptor

        # Individual wrong tags will be caught later.
        if len(xml_elt) != len(descr):
            raise XMLSerDesWrongChildrenError(exp_tags=[e.tag for e in descr],
                                              got_tags=[ch.tag for ch in xml_elt],
                                              xpath=_xpath)

        return collections.OrderedDict(
            (child_elt.tag, descr_elt.extract_from(child_elt, _xpath + [child_elt.tag]))
            for child_elt, descr_elt in zip(xml_elt, descr))


class XMLSerializableNamedTupleMeta(XMLSerializableMeta):
    @staticmethod
    def _partition_dict(src_dict, keys):
        """
        Partition the items in ``src_dict`` according to whether the key of the item is
        in ``keys``.  Two new dictionaries are returned:

            ``matching_keys_dict``, ``non_matching_keys_dict``

        where ``matching_keys_dict`` consists of those items of ``src_dict`` whose keys
        are in ``keys``, and ``non_matching_keys_dict`` consists of those items of
        ``src_dict`` whose keys are NOT in ``keys``.  The passed-in ``src_dict`` is not
        mutated.
        """
        matching_keys_dict = {}
        non_matching_keys_dict = {}
        for k, v in src_dict.items():
            dest_dict = matching_keys_dict if k in keys else non_matching_keys_dict
            dest_dict[k] = v
        return matching_keys_dict, non_matching_keys_dict

    def __new__(meta, cls_name, bases, cls_dict):
        if 'xml_descriptor' not in cls_dict:
            raise ValueError('no "xml_descriptor" in "%s"' % cls_name)

        cls_dict.setdefault('xml_default_tag', cls_name)
        if cls_dict['xml_default_tag'] is None:
            cls_dict.pop('xml_default_tag')

        super_new = super(XMLSerializableNamedTupleMeta, meta).__new__
        xml_name = '_XML_' + cls_name
        xml_cls_dict = {'xml_descriptor': cls_dict['xml_descriptor']}
        xml_cls = super_new(meta, xml_name, bases, xml_cls_dict)

        descr = xml_cls.xml_descriptor

        if len(xml_cls.slot_name_from_tag_name) != len(descr):
            raise ValueError('invalid xml_descriptor: all "value_from"s must be simple attributes')

        namedtuple_cls = collections.namedtuple(cls_name,
                                                list(xml_cls.slot_name_from_tag_name.values()))

        cls_dict.pop('xml_descriptor')
        return type.__new__(meta, cls_name, (namedtuple_cls, xml_cls), cls_dict)


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

    If class has no ``xml_default_tag`` attribute, it is created with
    value equal to the class name:

    >>> class Circle(xmlserdes.XMLSerializableNamedTuple):
    ...     xml_descriptor = [('radius', int)]
    >>> c = Circle(42)
    >>> print(c)
    Circle(radius=42)
    >>> c.radius
    42
    >>> print(xmlserdes.utils.str_from_xml_elt(c.as_xml()))
    <Circle><radius>42</radius></Circle>

    To suppress this behaviour, define an ``xml_default_tag`` attribute
    with value ``None``.  This is useful if you wish to force callers of
    ``as_xml()`` to supply the tag:

    >>> class Sphere(xmlserdes.XMLSerializableNamedTuple):
    ...     xml_default_tag = None
    ...     xml_descriptor = [('radius', int)]
    >>> s = Sphere(100)
    >>> print(xmlserdes.utils.str_from_xml_elt(s.as_xml('round-object')))
    <round-object><radius>100</radius></round-object>
    >>> x = s.as_xml()
    ... #doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    AttributeError: 'Sphere' object has no attribute 'xml_default_tag'
    """

    xml_default_tag = None
    xml_descriptor = []

    @classmethod
    def _verify_children(cls, ordered_dict, _xpath):
        tags_got = list(ordered_dict.keys())
        tags_exp = list(cls.slot_name_from_tag_name.keys())
        if tags_got != tags_exp:
            raise XMLSerDesWrongChildrenError(exp_tags=tags_exp,
                                              got_tags=tags_got,
                                              xpath=_xpath)

    @classmethod
    def from_xml_dict(cls, ordered_dict, _xpath=[]):
        cls._verify_children(ordered_dict, _xpath)
        return cls._make(ordered_dict.values())
