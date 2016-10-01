from lxml import etree


class XMLElementNode(object):
    def __init__(self, tag, text=None):
        elt = etree.Element(tag)
        elt.text = text
        self.elt = elt

    def append_child(self, ch):
        self.elt.append(ch)


def make_XMLNode(tag, *args):
    return XMLElementNode(tag, *args)
