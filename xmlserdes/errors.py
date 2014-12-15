class XMLSerDesError(ValueError):
    def __init__(self, *args, **kwargs):
        self.xpath = kwargs.pop('xpath')
        ValueError.__init__(self, *args, **kwargs)
