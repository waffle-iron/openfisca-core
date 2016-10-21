# -*- coding: utf-8 -*-


"""OpenFisca exceptions."""


class ParameterNotFound(Exception):
    def __init__(self, name, instant, variable_name = None):
        assert name is not None
        assert instant is not None
        self.name = name
        self.instant = instant
        self.variable_name = variable_name
        message = u'Legislation parameter "{}" was not found at instant "{}"'.format(name, instant)
        if variable_name is not None:
            message += u' by variable "{}"'.format(variable_name)
        super(ParameterNotFound, self).__init__(message)

    def to_json(self):
        self_json = {
            'instant': unicode(self.instant),
            'message': unicode(self),
            'parameter_name': self.name,
            }
        if self.variable_name is not None:
            self_json['variable_name'] = self.variable_name
        return self_json
