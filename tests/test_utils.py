# -*- coding: utf-8  -*-

import pytest

import xmlserdes.utils as XmlUtils

import lxml.etree

class TestToUnicode(object):
    def test_empty_element(self):
        elt = lxml.etree.Element('foo')
        assert XmlUtils.str_from_xml_elt(elt) == '<foo/>'

    def test_nonempty_element(self):
        elt = lxml.etree.Element('foo')
        elt.text = 'hello'
        assert XmlUtils.str_from_xml_elt(elt) == '<foo>hello</foo>'

    def test_nested_elements(self):
        elt = lxml.etree.Element('foo')

        child_0 = lxml.etree.Element('bar')
        child_0.text = '123'
        elt.append(child_0)

        child_1 = lxml.etree.Element('baz')
        child_1.text = '456'
        elt.append(child_1)

        assert XmlUtils.str_from_xml_elt(elt) == '<foo><bar>123</bar><baz>456</baz></foo>'
