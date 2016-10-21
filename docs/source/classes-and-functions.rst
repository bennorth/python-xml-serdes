Classes and functions
=====================

XMLSerializable
---------------
.. autoclass:: xmlserdes.XMLSerializable

XMLSerializableNamedTuple
-------------------------
.. autoclass:: xmlserdes.XMLSerializableNamedTuple

ElementDescriptor
-----------------
Most uses will be via the mechanism described in
:meth:`ElementDescriptor.new_from_tuple<xmlserdes.ElementDescriptor.new_from_tuple>`.

.. autoclass:: xmlserdes.ElementDescriptor
   :members:
   :member-order: bysource

SerDesDescriptor
----------------
.. autofunction:: xmlserdes.SerDesDescriptor


TypeDescriptor and subclasses
-----------------------------
Most uses will be via the mechanism described in
:meth:`TypeDescriptor.from_terse<xmlserdes.TypeDescriptor.from_terse>`.

.. autoclass:: xmlserdes.TypeDescriptor
   :members:

Atomic
^^^^^^
.. autoclass:: xmlserdes.Atomic

AtomicBool
^^^^^^^^^^
.. autoclass:: xmlserdes.AtomicBool

List
^^^^
.. autoclass:: xmlserdes.List

Instance
^^^^^^^^
.. autoclass:: xmlserdes.Instance

DTypeScalar
^^^^^^^^^^^
.. autoclass:: xmlserdes.DTypeScalar

NumpyAtomicVector
^^^^^^^^^^^^^^^^^
.. autoclass:: xmlserdes.NumpyAtomicVector

NumpyRecordVectorStructured
^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. autoclass:: xmlserdes.NumpyRecordVectorStructured

Function NumpyVector
^^^^^^^^^^^^^^^^^^^^
.. autofunction:: xmlserdes.NumpyVector
