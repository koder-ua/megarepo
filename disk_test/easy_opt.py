import argparse

__author__ = 'koder'

class Opt(object):
    def __init__(self, tp, doc="", default=None):
        self.tp = tp
        self.doc = doc
        self.name = None
        self.default = default

    def add_to_parser(self, parser):
        if self.default is not None:
            parser.add_argument("--" + self.name,
                dest=self.name,
                default=self.default)
        else:
            parser.add_argument("--" + self.name,
                dest=self.name)

class TypedOpt(Opt):
    def_tp = None

    def __init__(self, *dt, **mp):
        super(TypedOpt, self).__init__(self.def_tp, *dt, **mp)

class StrOpt(TypedOpt):
    def_tp = str

class IntOpt(TypedOpt):
    def_tp = int

class PyOptParser(object):
    _parser = None
    @classmethod
    def parse(cls):
        parser = cls.get_parser()

    @classmethod
    def fields(cls):
        for name, obj in cls.__dict__.items():
            if isinstance(obj, Opt):
                yield name, obj

    @classmethod
    def get_parser(cls):
        if cls._parser is None:
            parser = argparse.ArgumentParser()
            for name, obj in cls.fields():
                obj.name = name
                obj.add_to_parser(parser)
            cls._parser = parser
        return cls._parser

    @classmethod
    def parse_opts(cls, opts=None):
        obj = cls()
        parser = cls.get_parser()
        options = parser.parse_args(opts)
        for name, _ in cls.fields():
            setattr(obj, name, getattr(options, name))
        return obj


