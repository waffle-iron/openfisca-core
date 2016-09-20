# -*- coding: utf-8 -*-


'''
A node is a wrapper over the result of a computation.

The node class overrides every operation used by coutry_level codes, including infix operators (+, *, ...).
Other numpy operators are overloaded in numpy_wrapper.

In this current implementation, a node contains a numpy array.
Another implementation could defer the computation and contain references to parent nodes.
'''


from __future__ import division

import numpy as np


class Shell(object):
    # TODO Rename by ScalarWrapper?
    '''
    This class encapsulates scalar results (non vectorial) to customize operators between `Node` and `Shell` instances.
    '''

    def __init__(self, value):
        self.value = value

    def __add__(self, other):
        if isinstance(other, Shell):
            return Shell(self.value + other.value)

        raise NotImplementedError()


class Node(object):
    """A container for a numpy array"""

    def __init__(self, value, entity, simulation, default=None):
        # Copy value, otherwise write in cache.
        # TODO Remove copy, Node.__setitem__ and see what fails,
        # and try to solve it with an explicit Node.clone method.
        self.value = np.copy(value)
        self.entity = entity
        self.simulation = simulation
        self.default = default

    def __repr__(self):
        return u'Node(entity={}, value={})'.format(
            repr(dict(self.entity)['key_plural']),
            repr(self.value),
            )

    def copy(self):
        return Node(self.value, self.entity, self.simulation, self.default)

    @property
    def array(self):
        return self

    def override(self, other, method):
        if isinstance(other, Node):
            assert self.entity is other.entity
            assert self.simulation is other.simulation
            other_value = other.value

        elif isinstance(other, Shell):
            other_value = other.value

        else:
            other_value = other

        new_array = getattr(self.value, method)(other_value)
        return Node(new_array, self.entity, self.simulation)

    def override_unary(self, method, *args, **kwargs):
        new_array = getattr(self.value, method)(*args, **kwargs)
        return Node(new_array, self.entity, self.simulation, self.default)

    def __and__(self, other):
        return self.override(other, '__and__')

    def __or__(self, other):
        return self.override(other, '__or__')

    def __truediv__(self, other):
        return self.override(other, '__truediv__')

    def __div__(self, other):
        return self.override(other, '__div__')

    def __rdiv__(self, other):
        return self.override(other, '__rdiv__')

    def __rtruediv__(self, other):
        return self.override(other, '__rtruediv__')

    def __floordiv__(self, other):
        return self.override(other, '__floordiv__')

    def __add__(self, other):
        return self.override(other, '__add__')

    def __radd__(self, other):
        return self.override(other, '__radd__')

    def __sub__(self, other):
        return self.override(other, '__sub__')

    def __rsub__(self, other):
        return self.override(other, '__rsub__')

    def __mul__(self, other):
        return self.override(other, '__mul__')

    def __rmul__(self, other):
        return self.override(other, '__rmul__')

    def __eq__(self, other):
        return self.override(other, '__eq__')

    def __ne__(self, other):
        return self.override(other, '__ne__')

    def __lt__(self, other):
        return self.override(other, '__lt__')

    def __gt__(self, other):
        return self.override(other, '__gt__')

    def __le__(self, other):
        return self.override(other, '__le__')

    def __ge__(self, other):
        return self.override(other, '__ge__')

    def astype(self, *args, **kwargs):
        return self.override_unary('astype', *args, **kwargs)

    def __neg__(self):
        '''Implements unary -x'''
        return self.override_unary('__neg__')

    def __invert__(self):
        '''Implements unary ~x'''
        return self.override_unary('__invert__')

    def __getitem__(self, key):
        assert isinstance(key, Node)
        new_array = self.value[key.value]
        return Node(new_array, key.entity, self.simulation, self.default)

    def __setitem__(self, key, value):
        assert isinstance(key, Node)
        if isinstance(value, Node):
            value_2 = value.value
        else:
            value_2 = value

        self.value[key.value] = value_2
        return None

    def any(self):
        return self.value.any()
