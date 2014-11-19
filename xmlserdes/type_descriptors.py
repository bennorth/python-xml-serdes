import collections
import operator
from abc import ABCMeta, abstractmethod
import numpy as np
from lxml import etree

import xmlserdes

import six


class TypeDescriptor(six.with_metaclass(ABCMeta)):
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
        """
        Method to construct an instance of
        :class:`xmlserdes.TypeDescriptor` from a terse expression.  Many
        types for the ``expression`` argument are supported:

        atomic type object
            A :class:`xmlserdes.Atomic` instance is created for that
            type.  The list of known 'atomic' types is stored in
            ``TypeDescriptor.atomic_types``.

            >>> td = TypeDescriptor.from_terse(int)
            >>> print(xmlserdes.utils.str_from_xml_elt(td.xml_element(42, 'answer')))
            <answer>42</answer>

        bool type object
            An instance of :class:`xmlserdes.AtomicBool` is created.

            >>> td = TypeDescriptor.from_terse(bool)
            >>> print(xmlserdes.utils.str_from_xml_elt(td.xml_element(False, 'is-blue')))
            <is-blue>false</is-blue>

        string instance
            A :class:`xmlserdes.Atomic` instance is created, where the
            contained type is found by interpreting the given string as
            a Numpy dtype code.

            >>> td = TypeDescriptor.from_terse('i2')
            >>> print(xmlserdes.utils.str_from_xml_elt(td.xml_element(np.int16(42), 'answer')))
            <answer>42</answer>

        non-atomic type object
            A :class:`xmlserdes.Instance` instance is created, where the
            contained type is the given type.  The type must have an
            ``xml_descriptor`` attribute.

            >>> class Blob(xmlserdes.XMLSerializableNamedTuple):
            ...     xml_descriptor = [('size', int)]
            >>> td = TypeDescriptor.from_terse(Blob)
            >>> print(xmlserdes.utils.str_from_xml_elt(td.xml_element(Blob(42), 'blob')))
            <blob><size>42</size></blob>

            (This example uses the terse type-descriptor format to
            specify the XML behaviour of the one field of ``Blob``.)

        list instance
            A :class:`xmlserdes.List` instance is created.

            The given list must have either one or two elements.

            If two elements, they are taken as the contained type and
            contained tag:

            >>> td = TypeDescriptor.from_terse([int, 'ans'])
            >>> print(xmlserdes.utils.str_from_xml_elt(td.xml_element([42, 99], 'answers')))
            <answers><ans>42</ans><ans>99</ans></answers>

            If one element, it must be a type having an
            ``xml_default_tag`` attribute, which is used as the
            contained tag:

            >>> class Blob(xmlserdes.XMLSerializableNamedTuple):
            ...     xml_default_tag = 'blob'
            ...     xml_descriptor = [('size', int)]
            >>> td = TypeDescriptor.from_terse([Blob])
            >>> blobs = [Blob(42), Blob(99)]
            >>> print(xmlserdes.utils.str_from_xml_elt(td.xml_element(blobs, 'blobs')))
            <blobs><blob><size>42</size></blob><blob><size>99</size></blob></blobs>

        tuple instance
            Depending on the tuple length, either a
            :class:`xmlserdes.NumpyAtomicVector` or a
            :class:`xmlserdes.NumpyRecordVectorStructured` is created.
            In all cases, the first element of the tuple must be the
            Numpy.ndarray type object

            two-element tuple
                The second tuple element must be an atomic Numpy dtype,
                and a :class:`xmlserdes.NumpyAtomicVector` for that
                dtype is returned.

                >>> td = xmlserdes.TypeDescriptor.from_terse((np.ndarray, np.int32))
                >>> xs = np.array([1, 2, 3], dtype = np.int32)
                >>> print(xmlserdes.utils.str_from_xml_elt(td.xml_element(xs, 'answers')))
                <answers>1,2,3</answers>

            three-element tuple
                The second element must be a record dtype, and the third
                element must be a string naming the contained elements.  A
                :class:`xmlserdes.NumpyRecordVectorStructured` is created.

                This example uses very short tag names to keep the output
                of a reasonable length:

                >>> Rect = np.dtype([('w', np.uint16), ('h', np.uint16)])
                >>> td = xmlserdes.TypeDescriptor.from_terse((np.ndarray, Rect, 'r'))
                >>> rects = np.array([(10, 20), (3, 4)], dtype = Rect)
                >>> print(xmlserdes.utils.str_from_xml_elt(td.xml_element(rects, 'rs')))
                <rs><r><w>10</w><h>20</h></r><r><w>3</w><h>4</h></r></rs>

        """

        if descr in cls.atomic_types:
            return Atomic(descr)

        if descr is bool:
            return AtomicBool()

        if isinstance(descr, str):
            return Atomic(np.dtype(descr).type)

        if isinstance(descr, list):
            if len(descr) == 1:
                contained_descr = descr[0]
                if not hasattr(contained_descr, 'xml_default_tag'):
                    raise ValueError('1-elt list: type "%s" has no "xml_default_tag"'
                                     % contained_descr.__name__)
                tag = contained_descr.xml_default_tag
            elif len(descr) == 2:
                contained_descr, tag = descr
            else:
                raise ValueError(
                    'list descriptor: expected 1 or 2 elements but got %d' % len(descr))
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
                        '2-tuple descriptor: expected atomic numpy type as second element'
                        + ' but got "%s"' % contained_atomic_type.__name__)
                return NumpyAtomicVector(contained_atomic_type)

            if len(descr) == 3:
                contained_dtype, tag = descr[1:]
                if not isinstance(contained_dtype, np.dtype):
                    raise ValueError('3-tuple descriptor must have numpy dtype as second element')
                return NumpyRecordVectorStructured(contained_dtype, tag)

            raise ValueError('tuple descriptor: expected 2 or 3 elements but got %d'
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

    @abstractmethod  # pragma: no cover
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

    @abstractmethod  # pragma: no cover
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


class AtomicBool(TypeDescriptor):
    """
    A special-case :class:`xmlserdes.TypeDescriptor` for handling atomic
    Boolean values.  The Python value ``True`` is serialized as the
    string ``true`` (note the case difference), and similarly for the
    value ``False``.

    When serializing, only the actual bool values True or False are
    valid.

    >>> bool_type_descriptor = xmlserdes.AtomicBool()
    >>> print(xmlserdes.utils.str_from_xml_elt(bool_type_descriptor.xml_element(True, 'answer')))
    <answer>true</answer>
    >>> xml_elt = etree.fromstring('<is-heavy>true</is-heavy>')
    >>> bool_type_descriptor.extract_from(xml_elt, 'is-heavy')
    True
    >>> bad_xml_elt = etree.fromstring('<is-heavy>dark-orange</is-heavy>')
    >>> bool_type_descriptor.extract_from(bad_xml_elt, 'is-heavy')
    Traceback (most recent call last):
        ...
    ValueError: expected text "true" or "false" but got "dark-orange" for bool
    >>> bool_type_descriptor.xml_element(42, 'meaning')
    Traceback (most recent call last):
        ...
    ValueError: expected True or False but got "42" for bool
    """

    def xml_element(self, obj, tag):
        elt = etree.Element(tag)
        if obj is True:
            elt.text = 'true'
        elif obj is False:
            elt.text = 'false'
        else:
            raise ValueError('expected True or False but got "%s" for bool' % obj)
        return elt

    def extract_from(self, elt, expected_tag):
        self.verify_tag(elt, expected_tag)
        text = elt.text
        if text == 'true':
            return True
        if text == 'false':
            return False
        raise ValueError('expected text "true" or "false" but got "%s" for bool' % text)


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

    >>> print(xmlserdes.utils.str_from_xml_elt(
    ...     list_of_ints_td.xml_element([42, 123, 99], 'list-of-answers')))
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
        attribute named ``xml_descriptor`` which is a list of instances
        of :class:`xmlserdes.ElementDescriptor`

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

        self.xml_descriptor = cls.xml_descriptor
        self.constructor = cls

    def xml_element(self, obj, tag):
        elt = etree.Element(tag)
        for child in self.xml_descriptor:
            child_elt = child.xml_element(obj)
            elt.append(child_elt)
        return elt

    components_label = 'children'

    def extract_from(self, elt, expected_tag):
        self.verify_tag(elt, expected_tag)
        descr = self.xml_descriptor
        if len(elt) != len(descr):
            raise ValueError('expected %d %s but got %d'
                             % (len(descr), self.components_label, len(elt)))

        ctor = self.constructor
        ctor_args = [descr_elt.extract_from(child_elt)
                     for child_elt, descr_elt in zip(elt, descr)]

        return ctor(*ctor_args)


class NumpyValidityAssertionMixin(object):
    def assert_valid(self, obj, exp_type, exp_type_label, exp_ndim):
        if not isinstance(obj, exp_type):
            raise ValueError('object not %s' % exp_type_label)
        if obj.ndim != exp_ndim:
            raise ValueError('ndarray not %d-dimensional' % exp_ndim)
        if obj.dtype != self.dtype:
            raise ValueError('expected dtype "%s" but got "%s"'
                             % (obj.dtype, self.dtype))


class NumpyAtomicVector(TypeDescriptor, NumpyValidityAssertionMixin):
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

    def xml_element(self, obj, tag):
        self.assert_valid(obj, np.ndarray, 'ndarray', 1)
        elt = etree.Element(tag)
        elt.text = ','.join(map(repr, obj))
        return elt

    def extract_from(self, elt, expected_tag):
        self.verify_tag(elt, expected_tag)
        s_elts = elt.text.split(',')
        elements_list = list(map(self.dtype, s_elts))
        return np.array(elements_list, dtype=self.dtype)


class DTypeScalar(Instance, NumpyValidityAssertionMixin):
    """
    A :class:`xmlserdes.TypeDescriptor` for handling Numpy scalars of
    custom dtype.

    The XML representation has one sub-element per field of the dtype.
    Atomic-type fields are represented as their ``repr``;
    structured-dtype fields are represented with children corresponding
    to their fields, and so on.

    .. note:: Currently the XML tags for the fields of each record are
      the same as the field names of the ``dtype``.  Possible to-do is to
      allow a mapping between these two sets of names.

    :param dtype: Numpy record ``dtype`` of the vector

    Define record ``dtype`` whose fields are all atomic types:

    >>> import numpy as np
    >>> ColourDType = np.dtype([('red', np.uint8),
    ...                         ('green', np.uint8),
    ...                         ('blue', np.uint8)])

    Define type-descriptor for a scalar instance of it:

    >>> colour_scalar_td = xmlserdes.DTypeScalar(ColourDType)

    Serialize a scalar (the ``[()]`` construct extracts a scalar element
    from the 0-dimensional array):

    >>> colour = np.array((20, 40, 50), dtype = ColourDType)[()]
    >>> print(xmlserdes.utils.str_from_xml_elt(
    ...           colour_scalar_td.xml_element(colour, 'colour'),
    ...           pretty_print = True).rstrip())
    <colour>
      <red>20</red>
      <green>40</green>
      <blue>50</blue>
    </colour>

    >>> xml_elt = etree.fromstring(
    ... '<green><red>0</red><green>64</green><blue>0</blue></green>')
    >>> extracted_colour = colour_scalar_td.extract_from(xml_elt, 'green')
    >>> print(extracted_colour)
    (0, 64, 0)
    >>> print(extracted_colour.dtype)
    [('red', 'u1'), ('green', 'u1'), ('blue', 'u1')]

    Define a record ``dtype`` with nested custom field:

    >>> PatternDType = np.dtype([('background', ColourDType),
    ...                          ('foreground', ColourDType)])

    Define type-descriptor for a scalar instance of it:

    >>> pattern_scalar_td = xmlserdes.DTypeScalar(PatternDType)

    Serialize a scalar (the ``[()]`` construct extracts a scalar element
    from the 0-dimensional array):

    >>> pattern = np.array(((120, 140, 150), (20, 40, 50)), dtype = PatternDType)[()]
    >>> print(xmlserdes.utils.str_from_xml_elt(
    ...           pattern_scalar_td.xml_element(pattern, 'pattern'),
    ...           pretty_print = True).rstrip())
    <pattern>
      <background>
        <red>120</red>
        <green>140</green>
        <blue>150</blue>
      </background>
      <foreground>
        <red>20</red>
        <green>40</green>
        <blue>50</blue>
      </foreground>
    </pattern>
    """

    @staticmethod
    def type_descriptor_from_dtype(dtype):
        if dtype in Instance.atomic_types_numpy:
            return Atomic(dtype.type)
        else:
            return DTypeScalar(dtype)

    def __init__(self, dtype):
        self.dtype = dtype
        self.xml_descriptor = [
            xmlserdes.ElementDescriptor.new_from_tuple(
              (nm,
               operator.itemgetter(nm),
               self.type_descriptor_from_dtype(dtype.fields[nm][0])))
            for nm in dtype.names]

    def xml_element(self, obj, tag):
        self.assert_valid(obj, np.void, 'numpy scalar', 0)
        return Instance.xml_element(self, obj, tag)

    def constructor(self, *args):
        return np.array(args, dtype=self.dtype)

    components_label = 'sub-elements'


class NumpyRecordVectorStructured(List, NumpyValidityAssertionMixin):
    """
    A :class:`xmlserdes.TypeDescriptor` for handling Numpy vectors (i.e.,
    one-dimensional ``ndarray`` instances) where the ``dtype`` is a
    Numpy record type.  The record-type's fields can be scalar atomic
    types or custom ``dtype``s in turn.

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

    >>> colour_vector_td = xmlserdes.NumpyRecordVectorStructured(ColourDType, 'colour')

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

    Custom ``dtype`` one of whose fields is non-atomic:

    >>> StripeDType = np.dtype([('colour', ColourDType), ('width', np.uint16)])

    Type-descriptor for vector of such elements:

    >>> stripe_vector_td = xmlserdes.NumpyRecordVectorStructured(StripeDType, 'stripe')

    Serialize a vector:

    >>> stripes = np.array([((20, 30, 40), 100), ((120, 130, 140), 200)],
    ...                    dtype = StripeDType)
    >>> print(xmlserdes.utils.str_from_xml_elt(
    ...           stripe_vector_td.xml_element(stripes, 'stripes'),
    ...           pretty_print = True).rstrip())
    <stripes>
      <stripe>
        <colour>
          <red>20</red>
          <green>30</green>
          <blue>40</blue>
        </colour>
        <width>100</width>
      </stripe>
      <stripe>
        <colour>
          <red>120</red>
          <green>130</green>
          <blue>140</blue>
        </colour>
        <width>200</width>
      </stripe>
    </stripes>
    """
    def __init__(self, dtype, contained_tag):
        self.dtype = dtype
        List.__init__(self, DTypeScalar(dtype), contained_tag)

    def xml_element(self, obj, tag):
        self.assert_valid(obj, np.ndarray, 'ndarray', 1)
        return List.xml_element(self, obj, tag)

    def extract_from(self, elt, expected_tag):
        elts = List.extract_from(self, elt, expected_tag)
        return np.array(elts, dtype=self.dtype)


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
    >>> int_vector_td = xmlserdes.NumpyVector(np.int32)

    >>> ColourDType = np.dtype([('red', np.uint8),
    ...                         ('green', np.uint8),
    ...                         ('blue', np.uint8)])
    >>> colour_vector_td = xmlserdes.NumpyVector(ColourDType, 'colour')

    """

    return (NumpyAtomicVector(dtype) if contained_tag is None
            else NumpyRecordVectorStructured(dtype, contained_tag))
