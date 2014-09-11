import collections
import numpy as np
from lxml import etree

import xmlserdes

class TypeDescriptor(object):
    """
    Instances of classes derived from :class:`xmlserdes.TypeDescriptor` support
    two operations on objects of a particular type:

    - :func:`xml_element` --- serialize a given object as an XML element.

    - :func:`extract_from` --- extract an object of the correct type
      from a given XML element.

    This base type is not useful.  Concrete derived types are:

    - :class:`xmlserdes.Atomic` --- fundamental type such as integer or string.
    - :class:`xmlserdes.List` --- homogeneous list of elements.
    - :class:`xmlserdes.Instance` --- instance of class, with fixed list of fields.
    - :class:`xmlserdes.NumpyAtomicVector` --- Numpy vector with atomic ``dtype``.
    - :class:`xmlserdes.NumpyRecordVectorStructured` --- Numpy vector of record ``dtype``.

    See those classes' individual docstrings for more details.
    """

    atomic_types_python = [int, float, str]
    atomic_types_numpy = [np.int8, np.int16, np.int32, np.int64,
                          np.uint8, np.uint16, np.uint32, np.uint64,
                          np.float32, np.float64]
    atomic_types = atomic_types_python + atomic_types_numpy

    @classmethod
    def from_terse(cls, descr):
        if descr in cls.atomic_types:
            return Atomic(descr)

        if isinstance(descr, list):
            if len(descr) != 2:
                raise ValueError(
                    'list descriptor: expecting 2 elements but got %d' % len(descr))
            contained_descr, tag = descr
            return List(cls.from_terse(contained_descr), tag)

        if isinstance(descr, tuple):
            if len(descr) == 0:
                raise ValueError('empty tuple descriptor')

            if descr[0] is not np.ndarray:
                raise ValueError('tuple descriptor must have numpy.ndarray as first element')

            if len(descr) == 2:
                # Atomic vector
                contained_atomic_type = descr[1]
                if contained_atomic_type not in cls.atomic_types_numpy:
                    raise ValueError(
                        '2-tuple descriptor: expecting atomic numpy type as second element'
                        + ' but got "%s"' % contained_atomic_type.__name__)
                return NumpyAtomicVector(contained_atomic_type)

            if len(descr) == 3:
                contained_dtype, tag = descr[1:]
                if not isinstance(contained_dtype, np.dtype):
                    raise ValueError('3-tuple descriptor must have numpy dtype as second element')
                return NumpyRecordVectorStructured(contained_dtype, tag)

            raise ValueError('tuple descriptor: expecting 2 or 3 elements but got %d'
                             % len(descr))

        # Otherwise, 'descr' should be a type which has its own descriptor.
        if isinstance(descr, type):
            if not hasattr(descr, 'xml_descriptor'):
                raise ValueError('non-atomic type descriptor: no "xml_descriptor" attribute in "%s"'
                                 % descr.__name__)

            return Instance(descr)

        raise ValueError('unhandled terse descriptor of type %s' % type(descr).__name__)

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

        See examples under subclasses of :class:`xmlserdes.TypeDescriptor` for details.
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
    A :class:`xmlserdes.TypeDescriptor` for handling 'atomic' types.  The concept
    of an 'atomic' type is not explicitly defined, but anything which
    can be faithfully represented as a string via ``str()``, and can be
    parsed from a string using the type name, will work.

    :param inner_type: The native Python atomic type to be serialized and deserialized.

    For example, an :class:`xmlserdes.Atomic` type-descriptor to handle an integer:

    >>> atomic_type_descriptor = xmlserdes.Atomic(int)

    Serializing an integer into an XML element:

    >>> print(xmlserdes.utils.str_from_xml_elt(atomic_type_descriptor.xml_element(42, 'answer')))
    <answer>42</answer>

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
    A :class:`xmlserdes.TypeDescriptor` for handling homogeneous lists of
    elements.

    :param contained_descriptor: specification of the type of each element in the lists
    :type contained_descriptor: :class:`xmlserdes.TypeDescriptor`
    :param contained_tag: tag for each sub-element of the sequence element
    :type contained_tag: str

    For example, a :class:`xmlserdes.List` type-descriptor to handle lists of
    integers, where each integer in the list will be represented by an
    XML element with tag ``answer``.

    >>> list_of_ints_td = List(xmlserdes.Atomic(int), 'answer')

    Serializing a list of integers into an XML element:

    >>> print(xmlserdes.utils.str_from_xml_elt(list_of_ints_td.xml_element([42, 123, 99], 'list-of-answers')))
    <list-of-answers><answer>42</answer><answer>123</answer><answer>99</answer></list-of-answers>

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
    A :class:`xmlserdes.TypeDescriptor` for handling homogeneous instances of
    a 'complex' class having an 'XML descriptor'.

    :param cls: class whose instances are to be de/serialized; must have
        attribute named ``xml_descriptor`` of type :class:`xmlserdes.Descriptor`

    .. note:: Possible to-do is allow separate passing-in of descriptor
        rather than requiring it to be an attribute of the to-be-serialized
        class.

    Define class and augment it with ``xml_descriptor`` attribute:

    >>> Rectangle = collections.namedtuple('Rectangle', 'wd ht')
    >>> Rectangle.xml_descriptor = xmlserdes.SerDesDescriptor([('wd', xmlserdes.Atomic(int)),
    ...                                                        ('ht', xmlserdes.Atomic(int))])

    Define type-descriptor to handle de/serialization:

    >>> rectangle_td = Instance(Rectangle)

    Serialize instance of the ``Rectangle`` class:

    >>> r = Rectangle(210, 297)
    >>> print(xmlserdes.utils.str_from_xml_elt(rectangle_td.xml_element(r, 'rect')))
    <rect><wd>210</wd><ht>297</ht></rect>

    Deserialize instance:

    >>> xml_elt = etree.fromstring('<rect><wd>4</wd><ht>3</ht></rect>')
    >>> rectangle_td.extract_from(xml_elt, 'rect')
    Rectangle(wd=4, ht=3)
    """

    def __init__(self, cls):
        if not hasattr(cls, 'xml_descriptor'):
            raise ValueError('class "%s" has no xml_descriptor' % cls.__name__)

        self.cls = cls

    def xml_element(self, obj, tag):
        elt = etree.Element(tag)
        for child in self.cls.xml_descriptor.children:
            child_elt = child.xml_element(obj)
            elt.append(child_elt)
        return elt

    def extract_from(self, elt, expected_tag):
        self.verify_tag(elt, expected_tag)
        descr = self.cls.xml_descriptor
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
        return np.array(elements_list, dtype=self.dtype)


class NumpyAtomicVector(NumpyVectorBase):
    """
    A :class:`xmlserdes.TypeDescriptor` for handling Numpy vectors (i.e.,
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
    >>> print(xmlserdes.utils.str_from_xml_elt(vector_td.xml_element(v, 'values')))
    <values>0,1,2,3</values>

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
        return list(map(self.dtype, s_elts))


class NumpyRecordVectorStructured(NumpyVectorBase):
    """
    A :class:`xmlserdes.TypeDescriptor` for handling Numpy vectors (i.e.,
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
    >>> print(xmlserdes.utils.str_from_xml_elt(
    ...           colour_vector_td.xml_element(colours, 'colours'),
    ...           pretty_print = True).rstrip())
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
    >>> print(extracted_colours)
    [(0, 64, 0) (0, 192, 0)]
    >>> print(extracted_colours.dtype)
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
        return list(map(self.extract_entry_element, elt))


def NumpyVector(dtype, contained_tag=None):
    """
    Convenience function to instantiate an instance of the appropriate
    :class:`xmlserdes.TypeDescriptor` subclass chosen from

    - :class:`xmlserdes.NumpyAtomicVector`
    - :class:`xmlserdes.NumpyRecordVectorStructured`

    If a ``contained_tag`` is given, a
    :class:`xmlserdes.NumpyRecordVectorStructured` is created.  If not, a
    :class:`xmlserdes.NumpyAtomicVector`.

    >>> import numpy as np
    >>> int_vector_td = NumpyVector(np.int32)

    >>> ColourDType = np.dtype([('red', np.uint8),
    ...                         ('green', np.uint8),
    ...                         ('blue', np.uint8)])
    >>> colour_vector_td = NumpyVector(ColourDType, 'colour')

    """

    return (NumpyAtomicVector(dtype) if contained_tag is None
            else NumpyRecordVectorStructured(dtype, contained_tag))
