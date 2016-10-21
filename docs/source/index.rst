.. XMLserdes documentation master file, created by
   sphinx-quickstart on Thu Sep  4 14:38:33 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

XMLserdes --- XML Serialisation and Deserialisation
===================================================

Mechanisms for serializing Python objects to XML, and deserializing them
from XML.  The top-level object in a serialization is almost always an
instance of some class having multiple properties to be de/serialized.
Support is provided for declarative specification of how this is to be
done.


Motivating example
------------------

This package is designed to help with the situation where you have to
produce or consume XML along these lines:

.. literalinclude:: ../../tests/test_motivating_example.py
   :language: xml
   :start-after: sample_xml_text
   :end-before: /sample_xml_text


With ``xmlserdes``, you can declare Python classes which mirror this
structure very easily:

.. literalinclude:: ../../tests/test_motivating_example.py
   :language: python
   :start-after: sample-class-defns
   :end-before: /sample-class-defns

Some points to note about these definitions:

* Each element of the ``xml_descriptor`` gives the XML tag name, and
  then optionally the Python-level field name, and then a descriptor for
  the type of the data.
* The leading ``@`` denotes that the ``type`` of a ``Furniture`` object
  is stored in an XML attribute.
* The XML element ``wall-colour`` contains a hyphen, so it is stored in
  the field ``wall_colour`` (with an underscore) of the ``Room`` object.

With this in place, reading a piece of XML into a new object is done
using the ``from_xml()`` classmethod::

  bd = BuildingDescription.from_xml(xml, 'building-description')
  assert bd.rooms[1].dimensions[1] == 4.0

where ``xml`` is a parsed XML element from the ``lxml`` package.
Generating XML from an existing ``BuildingDescription`` object is
achieved using the ``as_xml()`` method::

  xml = bd_description.as_xml()

The reference sections below give more details.  In particular, a full
description of how the elements of the ``xml_descriptor`` are
interpreted is given in
:meth:`xmlserdes.ElementDescriptor.new_from_tuple`.


.. toctree::
   :caption: Reference
   :maxdepth: 2

   classes-and-functions
   top-level-functions
