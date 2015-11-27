from difflib import Differ
from collections import namedtuple


class XMLSerDesError(ValueError):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.message = args[0]
        self.xpath = kwargs.pop('xpath')

    @property
    def xpath_str(self):
        return '/' + '/'.join(self.xpath)

    def __str__(self):
        base_str = ValueError.__str__(self)
        return '%s at %s' % (base_str, self.xpath_str)


class XMLSerDesWrongChildrenError(XMLSerDesError):
    def __init__(self, *args, **kwargs):
        self.exp_tags = kwargs.pop('exp_tags')
        self.got_tags = kwargs.pop('got_tags')
        self.tag_comparison = TagListComparison(self.exp_tags, self.got_tags)
        msg = 'mismatched children: %s' % self.tag_comparison
        XMLSerDesError.__init__(self, msg, **kwargs)


class TagDiffEntry(namedtuple('TagDiffEntry', 'type tag')):
    type_from_code = {'- ': 'missing',
                      '+ ': 'unexpected',
                      '  ': 'as-expected'}

    @classmethod
    def maybe_from_delta_entry(cls, d):
        code = d[:2]
        if code == '? ':
            return None
        return cls(cls.type_from_code[code], d[2:])

    def __str__(self):
        return '%s: %s' % self


class TagListComparison(object):
    def __init__(self, expected_tags, got_tags):
        self.entries = list(filter(None,
                                   map(TagDiffEntry.maybe_from_delta_entry,
                                       Differ().compare(expected_tags, got_tags))))

    def __str__(self):
        return '[%s]' % ', '.join(map(str, self.entries))

    def __len__(self):
        return len(self.entries)
