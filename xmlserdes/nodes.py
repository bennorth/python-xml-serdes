from lxml import etree


class XMLElementNode(object):
    def __init__(self, tag, text=None):
        elt = etree.Element(tag)
        elt.text = text
        self.elt = elt

    def append_child(self, ch):
        self.elt.append(ch)

    def append_attrib(self, ch):
        self.elt.attrib[ch.tag] = ch.text

    def append_to(self, parent_elt):
        parent_elt.append_child(self.elt)


class XMLAttributeNode(object):
    def __init__(self, tag, text=None):
        if text is None:
            raise ValueError('expected "text" when constructing XMLAttributeNode')
        self.tag = tag
        self.text = text

    def append_child(self, ch):
        raise ValueError('cannot append child to XMLAttributeNode')

    def append_attrib(self, ch):
        raise ValueError('cannot append attribute to XMLAttributeNode')

    def append_to(self, parent_elt):
        parent_elt.append_attrib(self)


def make_XMLNode(tag, *args):
    if tag[0] == '@':
        return XMLAttributeNode(tag[1:], *args)
    else:
        return XMLElementNode(tag, *args)
