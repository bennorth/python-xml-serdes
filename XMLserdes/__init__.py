from collections import namedtuple
from operator import attrgetter

import numpy as np
from lxml import etree

AtomicTypes = (int, float, str,
               np.int8, np.int16, np.int32, np.int64,
               np.uint8, np.uint16, np.uint32, np.uint64)

class DescriptorElement(namedtuple('_DescriptorElement', 'tag value_from type_descr')):
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
    :type type_descr: subclass of :class:`XMLserdes.TypeDescriptor`

    A more convenient way of constructing a
    :class:`XMLserdes.DescriptorElement` is to use the
    :meth:`XMLserdes.DescriptorElement.new_from_tuple` method.
    """

    # TODO Better names.  'SimpleDescriptor', 'CompoundDescriptor'? Sth to indicate
    # that Descriptor (below) knows how to construct a class from the tuple?  If it does.
    @classmethod
    def new_from_tuple(cls, tup):
        """
        Construct a new :class:`XMLserdes.DescriptorElement` from a two-
        or three-element tuple, covering the most common cases.

        :param tuple tup: two- or three-element tuple describing required instance

        The tuple must be one of:

        - a pair ``(tag, type_descriptor)``, in which case the
          ``value_from`` field of the resulting ``DescriptorElement`` is
          ``attrgetter(tag)``

        - a triple ``(tag, field_name_or_callable, type_descriptor)``;
          if ``field_name_or_callable`` is a ``str``, it is taken as an
          attribute and the resulting ``value_from`` is
          ``attrgetter(field_name_or_callable)``; otherwise
          ``field_name_or_callable`` must be a callable.
        """

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
        """
        Serialize, into an XML element, the relevant property from the given object.

        >>> descr = DescriptorElement.new_from_tuple(('width', Atomic(int)))
        >>> shape = namedtuple('Shape', 'width')(42)
        >>> etree.tostring(descr.xml_element(shape))
        '<width>42</width>'

        >>> descr_different_tag = DescriptorElement.new_from_tuple(('shape-width',
        ...                                                         'width',
        ...                                                         Atomic(int)))
        >>> etree.tostring(descr_different_tag.xml_element(shape))
        '<shape-width>42</shape-width>'
        """
        return self.type_descr.xml_element(self.value_from(obj), self.tag)

    def extract_from(self, elt):
        """
        Deserialize, from an XML element, a value of the relevant type.

        >>> descr = DescriptorElement.new_from_tuple(('width', Atomic(int)))
        >>> xml_elt = etree.fromstring('<width>99</width>')
        >>> descr.extract_from(xml_elt)
        99
        """
        return self.type_descr.extract_from(elt, self.tag)


class Descriptor(namedtuple('_Descriptor', 'children')):
    """
    Representation of a list of object-property/sub-XML-element
    mappings.  Used to represent how instances of a particular class
    should be de/serialized from/to the contents of an XML element.

    :ivar children: list of children, each as a
        :class:`XMLserdes.DescriptorElement` instance

    Most conveniently constructed via the
    :func:`XMLserdes.SerDesDescriptor` function.
    """

    # TODO: Add 'ctor_name' slot
    @classmethod
    def new_from_abbreviated_args(cls, *args):
        raw_descriptor = cls._make(args)
        return raw_descriptor._replace(children = map(DescriptorElement.new_from_tuple,
                                                      raw_descriptor.children))

def SerDesDescriptor(children):
    """
    Convenience function for constructing an instance of :class:`XMLserdes.Descriptor`.

    :param children: descriptions of property/sub-element mappings; each
        should be a tuple suitable for passing to
        :meth:`XMLserdes.DescriptorElement.new_from_tuple`.

    :type children: iterable of tuples

    :return: New instance of :class:`XMLserdes.Descriptor`.
    """

    return Descriptor.new_from_abbreviated_args(children)

class TypeDescriptor(object):
    """
    Instances of classes derived from :class:`XMLserdes.TypeDescriptor` support
    two operations on objects of a particular type:

    - :func:`xml_element` --- serialize a given object as an XML element.

    - :func:`extract_from` --- extract an object of the correct type
      from a given XML element.

    This base type is not useful.  Concrete derived types are:

    - :class:`XMLserdes.Atomic` --- fundamental type such as integer or string.
    - :class:`XMLserdes.List` --- homogeneous list of elements.
    - :class:`XMLserdes.Instance` --- instance of class, with fixed list of fields.
    - :class:`XMLserdes.NumpyAtomicVector` --- Numpy vector with atomic ``dtype``.
    - :class:`XMLserdes.NumpyRecordVectorStructured` --- Numpy vector of record ``dtype``.

    See those classes' individual docstrings for more details.
    """

    def verify_tag(self, elt, expected_tag):
        if elt.tag != expected_tag:
            raise ValueError('expected tag "%s" but got "%s"'
                             % (expected_tag, elt.tag))

    def xml_element(self, obj, tag):
        """
        Return an XML element, with the given tag, corresponding to the
        given object.

        :param obj: object to be serialized into an XML element
        :param tag: tag for the returned XML element
        :type tag: str
        :rtype: XML element (as :class:`etree.Element` instance)

        See examples under subclasses of :class:`XMLserdes.TypeDescriptor` for details.
        """
        raise NotImplementedError()

    def extract_from(self, elt, expected_tag):
        """
        Extract and return an object from the given XML element.  The
        tag of ``elt`` should be the given expected tag, otherwise a
        ``ValueError`` is raised.

        :param elt: XML element
        :type elt: :class:`etree.Element`
        :param expected_tag: tag which ``elt`` must have
        :type expected_tag: str
        :rtype: depends on concrete subclass of ``TypeDescriptor``
        """
        raise NotImplementedError()

class Atomic(TypeDescriptor):
    """
    A :class:`XMLserdes.TypeDescriptor` for handling 'atomic' types.  The concept
    of an 'atomic' type is not explicitly defined, but anything which
    can be faithfully represented as a string via ``str()``, and can be
    parsed from a string using the type name, will work.

    :param inner_type: The native Python atomic type to be serialized and deserialized.

    For example, an :class:`XMLserdes.Atomic` type-descriptor to handle an integer:

    >>> atomic_type_descriptor = Atomic(int)

    Serializing an integer into an XML element:

    >>> etree.tostring(atomic_type_descriptor.xml_element(42, 'answer'))
    '<answer>42</answer>'

    Deserializing an integer from an XML element:

    >>> xml_elt = etree.fromstring('<weight>99</weight>')
    >>> atomic_type_descriptor.extract_from(xml_elt, 'weight')
    99

    Unexpected tag:

    >>> atomic_type_descriptor.extract_from(xml_elt, 'length')
    Traceback (most recent call last):
        ...
    ValueError: expected tag "length" but got "weight"
    """

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
    """
    A :class:`XMLserdes.TypeDescriptor` for handling homogeneous lists of
    elements.

    :param contained_descriptor: specification of the type of each element in the lists
    :type contained_descriptor: :class:`XMLserdes.TypeDescriptor`
    :param contained_tag: tag for each sub-element of the sequence element
    :type contained_tag: str

    For example, a :class:`XMLserdes.List` type-descriptor to handle lists of
    integers, where each integer in the list will be represented by an
    XML element with tag ``answer``.

    >>> list_of_ints_td = List(Atomic(int), 'answer')

    Serializing a list of integers into an XML element:

    >>> etree.tostring(list_of_ints_td.xml_element([42, 123, 99], 'list-of-answers'))
    '<list-of-answers><answer>42</answer><answer>123</answer><answer>99</answer></list-of-answers>'

    Deserializing a list of integers from an XML element:

    >>> xml_elt = etree.fromstring('''<list-of-answers>
    ...                                 <answer>1</answer>
    ...                                 <answer>10</answer>
    ...                                 <answer>100</answer>
    ...                               </list-of-answers>''')
    >>> list_of_ints_td.extract_from(xml_elt, 'list-of-answers')
    [1, 10, 100]
    """

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
    """
    A :class:`XMLserdes.TypeDescriptor` for handling homogeneous instances of
    a 'complex' class having an 'XML descriptor'.

    :param cls: class whose instances are to be de/serialized; must have
        attribute named ``XML_Descriptor`` of type :class:`XMLserdes.Descriptor`

    .. note:: Possible to-do is allow separate passing-in of descriptor
        rather than requiring it to be an attribute of the to-be-serialized
        class.

    Define class and augment it with ``XML_Descriptor`` attribute:

    >>> from collections import namedtuple
    >>> Rectangle = namedtuple('Rectangle', 'wd ht')
    >>> Rectangle.XML_Descriptor = SerDesDescriptor([('wd', Atomic(int)),
    ...                                              ('ht', Atomic(int))])

    Define type-descriptor to handle de/serialization:

    >>> rectangle_td = Instance(Rectangle)

    Serialize instance of the ``Rectangle`` class:

    >>> r = Rectangle(210, 297)
    >>> etree.tostring(rectangle_td.xml_element(r, 'rect'))
    '<rect><wd>210</wd><ht>297</ht></rect>'

    Deserialize instance:

    >>> xml_elt = etree.fromstring('<rect><wd>4</wd><ht>3</ht></rect>')
    >>> rectangle_td.extract_from(xml_elt, 'rect')
    Rectangle(wd=4, ht=3)
    """

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
            raise ValueError('expecting %d children but got %d'
                             % (len(descr.children), len(elt)))

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
    """
    A :class:`XMLserdes.TypeDescriptor` for handling Numpy vectors (i.e.,
    one-dimensional ``ndarray`` instances) where the ``dtype`` is an
    'atomic' type.  Serialization is done as a CSV string.  Complex
    types are not supported.

    :param dtype: Numpy ``dtype`` of the vector

    Define type-descriptor to handle de/serialization of a Numpy vector
    of ``uint16`` elements:

    >>> import numpy as np
    >>> vector_td = NumpyAtomicVector(np.uint16)

    Serialize a vector:

    >>> v = np.arange(4, dtype = np.uint16)
    >>> etree.tostring(vector_td.xml_element(v, 'values'))
    '<values>0,1,2,3</values>'

    Deserialize a vector:

    >>> xml_elt = etree.fromstring('<values>10,20,30</values>')
    >>> vector_td.extract_from(xml_elt, 'values')
    array([10, 20, 30], dtype=uint16)
    """
    def __init__(self, dtype):
        self.dtype = dtype

    def populate_element(self, elt, xs):
        elt.text = ','.join(map(repr, xs))

    def extract_elements_list(self, elt):
        s_elts = elt.text.split(',')
        return map(self.dtype, s_elts)

class NumpyRecordVectorStructured(NumpyVectorBase):
    """
    A :class:`XMLserdes.TypeDescriptor` for handling Numpy vectors (i.e.,
    one-dimensional ``ndarray`` instances) where the ``dtype`` is a
    Numpy record type.  Currently, the record-type's fields must all be
    scalar atomic types.

    The XML representation has one sub-element per element of the
    vector.  Each of those sub-elements has sub-sub-elements
    corresponding to the fields of the record type.

    .. note:: Currently the XML tags for the fields of each record are
      the same as the field names of the ``dtype``.  Possible to-do is to
      allow a mapping between these two sets of names.

    :param dtype: Numpy record ``dtype`` of the vector
    :param contained_tag: tag to use for the element representing each element of the vector
    :type contained_tag: str

    Define record ``dtype``:

    >>> import numpy as np
    >>> ColourDType = np.dtype([('red', np.uint8),
    ...                         ('green', np.uint8),
    ...                         ('blue', np.uint8)])

    Define type-descriptor for it:

    >>> colour_vector_td = NumpyRecordVectorStructured(ColourDType, 'colour')

    Serialize a vector:

    >>> colours = np.array([(20, 40, 50),
    ...                     (128, 128, 128),
    ...                     (255, 0, 255)],
    ...                    dtype = ColourDType)
    >>> print etree.tostring(colour_vector_td.xml_element(colours, 'colours'),
    ...                      pretty_print = True).rstrip()
    <colours>
      <colour>
        <red>20</red>
        <green>40</green>
        <blue>50</blue>
      </colour>
      <colour>
        <red>128</red>
        <green>128</green>
        <blue>128</blue>
      </colour>
      <colour>
        <red>255</red>
        <green>0</green>
        <blue>255</blue>
      </colour>
    </colours>

    >>> xml_elt = etree.fromstring(
    ...     '''<greens>
    ...          <colour><red>0</red><green>64</green><blue>0</blue></colour>
    ...          <colour><red>0</red><green>192</green><blue>0</blue></colour>
    ...        </greens>''')
    >>> extracted_colours = colour_vector_td.extract_from(xml_elt, 'greens')
    >>> print extracted_colours
    [(0, 64, 0) (0, 192, 0)]
    >>> print extracted_colours.dtype
    [('red', 'u1'), ('green', 'u1'), ('blue', 'u1')]
    """
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
    """
    Convenience function to instantiate an instance of the appropriate
    :class:`XMLserdes.TypeDescriptor` subclass chosen from

    - :class:`XMLserdes.NumpyAtomicVector`
    - :class:`XMLserdes.NumpyRecordVectorStructured`

    If a ``contained_tag`` is given, a
    :class:`XMLserdes.NumpyRecordVectorStructured` is created.  If not, a
    :class:`XMLserdes.NumpyAtomicVector`.

    >>> import numpy as np
    >>> int_vector_td = NumpyVector(np.int32)

    >>> ColourDType = np.dtype([('red', np.uint8),
    ...                         ('green', np.uint8),
    ...                         ('blue', np.uint8)])
    >>> colour_vector_td = NumpyVector(ColourDType, 'colour')

    """

    return (NumpyAtomicVector(dtype) if contained_tag is None
            else NumpyRecordVectorStructured(dtype, contained_tag))

def Serialize(obj, tag):
    """
    Entry point function to serialize a Python object to an XML element.

    :param obj: Python object to serialize
    :type obj: instance of class having ``XML_Descriptor`` attribute

    :return: XML element, as instance of :class:`etree.Element`.
    """

    instance_td = Instance(obj.__class__)
    return instance_td.xml_element(obj, tag)

def Deserialize(cls, elt, expected_tag):
    """
    Entry point function to deserialize a Python object from an XML element.

    :param cls: class of object to deserialize

    :param elt: XML element
    :type elt: :class:`etree.Element`

    :return: instance of class ``cls``.
    """

    instance_td = Instance(cls)
    return instance_td.extract_from(elt, expected_tag)
