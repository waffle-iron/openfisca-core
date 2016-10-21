# -*- coding: utf-8 -*-


"""Generate legislation notes at a given instant."""


import logging

from .. import periods, taxscales
from ..exceptions import ParameterNotFound


log = logging.getLogger(__name__)


class LegislationNodeAtInstant(object):
    # Note: Legislation attributes are set explicitely by node_json_at_instant_to_objects
    # (ie they are not computed by a magic method).

    instant = None
    name = None

    def __delitem__(self, key):
        # TODO Is this a good idea to allow modifying a LegislationNodeAtInstant?
        del self.__dict__[key]

    # Reminder: __getattr__ is called only when attribute is not found.
    def __getattr__(self, key):
        name = u'.'.join([self.name, key]) \
            if self.name is not None \
            else key
        raise ParameterNotFound(
            instant = self.instant,
            name = name,
            )

    def __getitem__(self, key):
        return self.__dict__[key]

    def __init__(self, instant, name = None):
        assert instant is not None
        self.instant = instant
        self.name = name

    def __iter__(self):
        return self.__dict__.iterkeys()

    def __repr__(self):
        '''Return an XML-like representation of this LegislationNodeAtInstant.'''
        return '''
            <NODE code="new_node" description="Node added to the legislation by the reform">
                <CODE code="new_param" description="New parameter">
                    <VALUE deb="2000-01-01" fin="2014-12-31" valeur="999" />
                </CODE>
            </NODE>
            '''

    def __setitem__(self, key, value):
        # TODO Is this a good idea to allow modifying a LegislationNodeAtInstant?
        self.__dict__[key] = value

    def combine_tax_scales(self):
        """Combine all the MarginalRateTaxScales in the node into a single MarginalRateTaxScale."""
        combined_tax_scales = None
        for name, child in self.iteritems():
            if not isinstance(child, taxscales.AbstractTaxScale):
                log.info(u'Skipping {} with value {} because it is not a tax scale'.format(name, child))
                continue
            if combined_tax_scales is None:
                combined_tax_scales = taxscales.MarginalRateTaxScale(name = name)
                combined_tax_scales.add_bracket(0, 0)
            combined_tax_scales.add_tax_scale(child)
        return combined_tax_scales

    def copy(self, deep = False):
        new = self.__class__()
        for name, value in self.iteritems():
            if deep:
                if isinstance(value, LegislationNodeAtInstant):
                    new[name] = value.copy(deep = deep)
                elif isinstance(value, taxscales.AbstractTaxScale):
                    new[name] = value.copy()
                else:
                    new[name] = value
            else:
                new[name] = value
        return new

    def get(self, key, default = None):
        return self.__dict__.get(key, default)

    def items(self):
        return self.__dict__.items()

    def iteritems(self):
        return self.__dict__.iteritems()

    def iterkeys(self):
        return self.__dict__.iterkeys()

    def itervalues(self):
        return self.__dict__.itervalues()

    def keys(self):
        return self.__dict__.keys()

    def pop(self, key, default = None):
        return self.__dict__.pop(key, default)

    def scale_tax_scales(self, factor):
        """Scale all the MarginalRateTaxScales in the node."""
        scaled_node = LegislationNodeAtInstant()
        for key, child in self.iteritems():
            scaled_node[key] = child.scale_tax_scales(factor)
        return scaled_node

    def update(self, value):
        if isinstance(value, LegislationNodeAtInstant):
            value = value.__dict__
        return self.__dict__.update(value)

    def values(self):
        return self.__dict__.values()


class TracedLegislationNodeAtInstant(object):
    """
    A proxy for LegislationNodeAtInstant which stores the a simulation instance.
    Used for simulations with trace mode enabled.

    Overload __delitem__, __getitem__ and __setitem__ even if __getattribute__ is defined because of:
    http://stackoverflow.com/questions/11360020/why-is-getattribute-not-invoked-on-an-implicit-getitem-invocation
    """
    compact_node = None
    simulation = None
    traced_attributes_name = None

    def __init__(self, compact_node, simulation, traced_attributes_name):
        self.compact_node = compact_node
        self.simulation = simulation
        self.traced_attributes_name = traced_attributes_name

    def __delitem__(self, key):
        # TODO Is this a good idea to allow modifying a LegislationNodeAtInstant?
        del self.compact_node.__dict__[key]

    # Reminder: __getattr__ is called only when attribute is not found.
    def __getattr__(self, key):
        value = getattr(self.compact_node, key)
        if key in self.traced_attributes_name:
            calling_frame = self.simulation.stack_trace[-1]
            caller_parameters_infos = calling_frame['parameters_infos']
            assert self.compact_node.name is not None
            parameter_name = u'.'.join([self.compact_node.name, key])
            parameter_infos = {
                "instant": str(self.compact_node.instant),
                "name": parameter_name,
                }
            if isinstance(value, taxscales.AbstractTaxScale):
                # Do not serialize value in JSON for tax scales since they are too big.
                parameter_infos["@type"] = "Scale"
            else:
                parameter_infos.update({"@type": "Parameter", "value": value})
            if parameter_infos not in caller_parameters_infos:
                caller_parameters_infos.append(dict(sorted(parameter_infos.iteritems())))
        return value

    def __getitem__(self, key):
        return self.compact_node.__dict__[key]

    def __setitem__(self, key, value):
        # TODO Is this a good idea to allow modifying a LegislationNodeAtInstant?
        self.compact_node.__dict__[key] = value


# TODO Move as `LegislationNodeAtInstant` constructor, or .from_json?
def node_json_at_instant_to_objects(node_json_at_instant, code = None, instant = None, parent_codes = None,
        traced_simulation = None):
    """
    Compacts a legislation tree into a hierarchy of LegislationNodeAtInstant objects.

    The "traced_simulation" argument can be used for simulations with trace mode enabled, this stores parameter values
    in the traceback.
    """
    node_type = node_json_at_instant['@type']
    if node_type == u'Node':
        if code is None:
            # Root node
            assert instant is None, instant
            instant = periods.instant(node_json_at_instant['instant'])
        assert instant is not None
        name = u'.'.join((parent_codes or []) + [code]) \
            if code is not None \
            else None
        compact_node = LegislationNodeAtInstant(instant = instant, name = name)
        for key, value in node_json_at_instant['children'].iteritems():
            child_parent_codes = None
            if traced_simulation is not None:
                child_parent_codes = [] if parent_codes is None else parent_codes[:]
                if code is not None:
                    child_parent_codes += [code]
                child_parent_codes = child_parent_codes or None
            compact_node.__dict__[key] = node_json_at_instant_to_objects(
                value,
                code = key,
                instant = instant,
                parent_codes = child_parent_codes,
                traced_simulation = traced_simulation,
                )
        if traced_simulation is not None:
            traced_children_code = [
                key
                for key, value in node_json_at_instant['children'].iteritems()
                if value['@type'] != u'Node'
                ]
            # Only trace Nodes which have at least one Parameter child.
            if traced_children_code:
                compact_node = TracedLegislationNodeAtInstant(
                    compact_node = compact_node,
                    simulation = traced_simulation,
                    traced_attributes_name = traced_children_code,
                    )
        return compact_node
    assert instant is not None
    if node_type == u'Parameter':
        return node_json_at_instant.get('value')
    assert node_type == u'Scale'
    if any('amount' in bracket for bracket in node_json_at_instant['brackets']):
        # AmountTaxScale
        tax_scale = taxscales.AmountTaxScale(name = code, option = node_json_at_instant.get('option'))
        for bracket_json_at_instant in node_json_at_instant['brackets']:
            amount = bracket_json_at_instant.get('amount')
            assert not isinstance(amount, list)
            threshold = bracket_json_at_instant.get('threshold')
            assert not isinstance(threshold, list)
            if amount is not None and threshold is not None:
                tax_scale.add_bracket(threshold, amount)
        return tax_scale

    rates_kind = node_json_at_instant.get('rates_kind', None)
    if rates_kind == "average":
        # LinearAverageRateTaxScale
        tax_scale = taxscales.LinearAverageRateTaxScale(
            name = code,
            option = node_json_at_instant.get('option'),
            unit = node_json_at_instant.get('unit'),
            )
    else:
        # MarginalRateTaxScale
        tax_scale = taxscales.MarginalRateTaxScale(name = code, option = node_json_at_instant.get('option'))

    for bracket_json_at_instant in node_json_at_instant['brackets']:
        base = bracket_json_at_instant.get('base', 1)
        assert not isinstance(base, list)
        rate = bracket_json_at_instant.get('rate')
        assert not isinstance(rate, list)
        threshold = bracket_json_at_instant.get('threshold')
        assert not isinstance(threshold, list)
        if rate is not None and threshold is not None:
            tax_scale.add_bracket(threshold, rate * base)
    return tax_scale


# Functions which generate nodes at instant


def generate_legislation_json_at_instant(legislation_json, instant):
    '''
    Generate a whole legislation tree at a given `instant` from a given `legislation_json`.

    This is the main function.
    '''
    instant_str = str(periods.instant(instant))
    legislation_json_at_instant = generate_node_json_at_instant(legislation_json, instant_str)
    legislation_json_at_instant['@context'] = u'http://openfisca.fr/contexts/legislation-at-instant.jsonld'
    legislation_json_at_instant['instant'] = instant_str
    return legislation_json_at_instant


def generate_bracket_json_at_instant(bracket_json, instant_str):
    bracket_json_at_instant = {}
    for key, value in bracket_json.iteritems():
        if key in ('amount', 'base', 'rate', 'threshold'):
            value_at_instant = generate_json_value_at_instant(value, instant_str)
            if value_at_instant is not None:
                bracket_json_at_instant[key] = value_at_instant
        else:
            bracket_json_at_instant[key] = value
    return bracket_json_at_instant or None


def generate_json_value_at_instant(values_json, instant_str):
    for value_json in values_json:
        value_stop_str = value_json.get('stop')
        if value_json['start'] <= instant_str and (value_stop_str is None or instant_str <= value_stop_str):
            return value_json['value']
    return None


def generate_node_json_at_instant(node_json, instant):
    '''
    Return a version of the given `node` containing only the values at the given `instant`.

    `instant` can be a string like "YYYY-MM-DD" or a value of type `Instant`.
    '''
    instant_str = instant
    if not isinstance(instant_str, basestring):
        instant_str = str(periods.instant(instant_str))
    node_json_at_instant = {}
    for key, value in node_json.iteritems():
        if key == 'children':
            # Occurs when @type == 'Node'.
            children_json_at_instant = type(value)(
                (child_code, child_json_at_instant)
                for child_code, child_json_at_instant in (
                    (
                        child_code,
                        generate_node_json_at_instant(child_json, instant_str),
                        )
                    for child_code, child_json in value.iteritems()
                    )
                if child_json_at_instant is not None
                )
            if not children_json_at_instant:
                return None
            node_json_at_instant[key] = children_json_at_instant
        elif key in ('start', 'stop'):
            pass
        elif key == 'brackets':
            # Occurs when @type == 'Scale'.
            brackets_json_at_instant = [
                bracket_json_at_instant
                for bracket_json_at_instant in (
                    generate_bracket_json_at_instant(bracket_json, instant_str)
                    for bracket_json in value
                    )
                if bracket_json_at_instant is not None
                ]
            if not brackets_json_at_instant:
                return None
            node_json_at_instant[key] = brackets_json_at_instant
        elif key == 'values':
            # Occurs when @type == 'Parameter'.
            value_at_instant = generate_json_value_at_instant(value, instant_str)
            if value_at_instant is None:
                return None
            node_json_at_instant['value'] = value_at_instant
        else:
            node_json_at_instant[key] = value
    return node_json_at_instant
