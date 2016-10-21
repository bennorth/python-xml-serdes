import pytest

# xmlserdes imported below to be included in extracted content for doc

import numpy as np
from lxml import etree


sample_xml_text = """\
<building-description>
  <name>house</name>
  <rooms>
    <room>
    <dimensions>5.75,4.0,2.25</dimensions>
    <wall-colour>blue</wall-colour>
    <contents>
      <furniture type="chair"><material>wood</material><count>3</count></furniture>
      <furniture type="table"><material>plastic</material><count>1</count></furniture>
    </contents>
    </room>
    <room>
    <dimensions>2.15,3.0,1.875</dimensions>
    <wall-colour>red</wall-colour>
    <contents>
      <furniture type="lamp"><material>steel</material><count>6</count></furniture>
    </contents>
    </room>
  </rooms>
</building-description>
""" # /sample_xml_text

# sample-class-defns
from xmlserdes import XMLSerializableNamedTuple

class Furniture(XMLSerializableNamedTuple):
    xml_default_tag = 'furniture'
    xml_descriptor = [('@type', str), ('material', str), ('count', int)]

class Room(XMLSerializableNamedTuple):
    xml_default_tag = 'room'
    xml_descriptor = [('dimensions', (np.ndarray, np.float64)),
                      ('wall-colour', 'wall_colour', str),
                      ('contents', [Furniture])]

class BuildingDescription(XMLSerializableNamedTuple):
    xml_default_tag = 'building-description'
    xml_descriptor = [('name', str), ('rooms', [Room])]
# /sample-class-defns

def test_sample():
    xml = etree.fromstring(sample_xml_text)
    bd = BuildingDescription.from_xml(xml, 'building-description')
    # Weak test; if it serializes and deserializes that suffices:
    assert bd is not None
    assert bd.as_xml() is not None
