class XMLSerDesError(ValueError):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.message = args[0]
        self.xpath = kwargs.pop('xpath')

    def __str__(self):
        base_str = ValueError.__str__(self)
        xpath_str = '/' + '/'.join(self.xpath)
        return '%s at %s' % (base_str, xpath_str)
