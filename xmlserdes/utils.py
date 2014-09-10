import lxml

try:
    etree_encoding = unicode
except NameError:
    etree_encoding = str

def str_from_xml_elt(xml_elt):
    return lxml.etree.tostring(xml_elt, encoding=etree_encoding)
