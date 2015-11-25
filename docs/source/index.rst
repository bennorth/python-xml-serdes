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

.. autofunction:: xmlserdes.Serialize
.. autofunction:: xmlserdes.Deserialize


Classes and functions
---------------------

.. autoclass:: xmlserdes.ElementDescriptor
   :members:
   :member-order: bysource

.. autoclass:: xmlserdes.Descriptor

.. autofunction:: xmlserdes.SerDesDescriptor

.. autoclass:: xmlserdes.TypeDescriptor
   :members:

.. autoclass:: xmlserdes.Atomic
.. autoclass:: xmlserdes.List
.. autoclass:: xmlserdes.Instance
.. autoclass:: xmlserdes.NumpyAtomicVector
.. autoclass:: xmlserdes.NumpyRecordVectorStructured

.. autofunction:: xmlserdes.NumpyVector
