# -*- coding: utf-8 -*-

import collections
import operator

from lxml import etree  # noqa
import xmlserdes  # noqa

from xmlserdes.type_descriptors import TypeDescriptor


class ElementDescriptor(collections.namedtuple('_ElementDescriptor',
                                               'tag value_from value_slot type_descr')):
    """
    Object which represents the mapping between an XML element and a
    property of a Python object, together with the native Python type of
    that property.

    :param tag: tag for XML element to de/serialize from/to
    :type tag: str
    :param value_from: function (or other callable) which extracts the value
        from the containing object
    :type value_from: callable
    :param type_descr: type-descriptor which can de/serialize the Python object
        from/to the contents of an XML element
    :type type_descr: subclass of :class:`xmlserdes.TypeDescriptor`

    A more convenient way of constructing a
    :class:`xmlserdes.ElementDescriptor` is to use the
    :meth:`xmlserdes.ElementDescriptor.new_from_tuple` method.
    """

    def __new__(cls, *args, **kwargs):
        elt_descr = super(ElementDescriptor, cls).__new__(cls, *args, **kwargs)
        if not elt_descr.type_descr.tag_is_valid(elt_descr.tag):
            raise ValueError('tag "{0}" not valid for complex type-descriptor'
                             .format(elt_descr.tag))
        return elt_descr

    @classmethod
    def _ensure_TypeDescriptor(cls, obj):
        """
        If ``obj`` is already an instance of (a subclass of)
        TypeDescriptor, return it unchanged, otherwise return a new
        TypeDescriptor constructed via :meth:`from_terse`.
        """
        if isinstance(obj, TypeDescriptor):
            return obj
        return TypeDescriptor.from_terse(obj)

    @classmethod
    def new_from_tuple(cls, tup):
        """
        Construct a new :class:`xmlserdes.ElementDescriptor` from a two-
        or three-element tuple, covering the most common cases.

        :param tuple tup: two- or three-element tuple describing required instance

        The tuple must be one of:

        - a pair ``(tag, type_descriptor)``, in which case the
          ``value_from`` field of the resulting ``ElementDescriptor`` is
          ``attrgetter(tag)``

        - a triple ``(tag, field_name_or_callable, type_descriptor)``;
          if ``field_name_or_callable`` is a ``str``, it is taken as an
          attribute and the resulting ``value_from`` is
          ``attrgetter(field_name_or_callable)``; otherwise
          ``field_name_or_callable`` must be a callable.
        """

        if len(tup) == 2:
            tag, td = tup
            slot = (tag[1:] if tag[0] == '@' else tag)
            return cls(tag, operator.attrgetter(slot), slot, cls._ensure_TypeDescriptor(td))
        elif len(tup) == 3:
            tag, vf, td = tup
            vslot = None
            if isinstance(vf, str):
                vslot = vf
                vf = operator.attrgetter(vf)
            return cls(tag, vf, vslot, cls._ensure_TypeDescriptor(td))
        else:
            raise ValueError('bad tuple length')

    def xml_element(self, obj, _xpath=[]):
        """
        Serialize, into an XML element, the relevant property from the given object.

        >>> descr = ElementDescriptor.new_from_tuple(('width', xmlserdes.Atomic(int)))
        >>> shape = collections.namedtuple('Shape', 'width')(42)
        >>> print(xmlserdes.utils.str_from_xml_elt(descr.xml_element(shape)))
        <width>42</width>

        >>> descr_different_tag = ElementDescriptor.new_from_tuple(('shape-width',
        ...                                                         'width',
        ...                                                         xmlserdes.Atomic(int)))
        >>> print(xmlserdes.utils.str_from_xml_elt(descr_different_tag.xml_element(shape)))
        <shape-width>42</shape-width>
        """
        return self.type_descr.xml_element(self.value_from(obj), self.tag, _xpath)

    def xml_node(self, obj, _xpath=[]):
        return self.type_descr.xml_node(self.value_from(obj), self.tag, _xpath)

    def extract_from(self, elt, _xpath=[]):
        """
        Deserialize, from an XML element, a value of the relevant type.

        >>> descr = ElementDescriptor.new_from_tuple(('width', xmlserdes.Atomic(int)))
        >>> xml_elt = etree.fromstring('<width>99</width>')
        >>> descr.extract_from(xml_elt)
        99
        """
        return self.type_descr.extract_from(elt, self.tag, _xpath)
