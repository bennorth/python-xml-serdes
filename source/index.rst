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

Top-level functions
-------------------

.. autofunction:: XMLserdes.Serialize
.. autofunction:: XMLserdes.Deserialize


Classes and functions
---------------------

.. autoclass:: XMLserdes.DescriptorElement
   :members:
   :member-order: bysource

.. autoclass:: XMLserdes.Descriptor

.. autofunction:: XMLserdes.SerDesDescriptor

.. autoclass:: XMLserdes.TypeDescriptor
   :members:

.. autoclass:: XMLserdes.Atomic
.. autoclass:: XMLserdes.List
.. autoclass:: XMLserdes.Instance
.. autoclass:: XMLserdes.NumpyAtomicVector
.. autoclass:: XMLserdes.NumpyRecordVectorStructured

.. autofunction:: XMLserdes.NumpyVector
