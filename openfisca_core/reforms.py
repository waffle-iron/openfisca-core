# -*- coding: utf-8 -*-

import copy

from . import legislations, periods
from .legislations import validators as legislation_validators
from .taxbenefitsystems import TaxBenefitSystem


def compose_reforms(reforms, tax_benefit_system):
    """
    Compose reforms: the first reform is built with the given base tax-benefit system,
    then each one is built with the previous one as the reference.
    """
    def compose_reforms_reducer(memo, reform):
        reformed_tbs = reform(memo)
        return reformed_tbs
    final_tbs = reduce(compose_reforms_reducer, reforms, tax_benefit_system)
    return final_tbs


class Reform(TaxBenefitSystem):
    name = None

    def __init__(self, reference):
        self.entity_class_by_key_plural = reference.entity_class_by_key_plural
        self._legislation_json = reference.get_legislation()
        self.compact_legislation_by_instant_cache = reference.compact_legislation_by_instant_cache
        self.column_by_name = reference.column_by_name.copy()
        self.Scenario = reference.Scenario
        self.DEFAULT_DECOMP_FILE = reference.DEFAULT_DECOMP_FILE
        self.reference = reference
        self.key = unicode(self.__class__.__name__)
        if not hasattr(self, 'apply'):
            raise Exception("Reform {} must define an `apply` function".format(self.key))
        self.apply()

    @property
    def full_key(self):
        key = self.key
        assert key is not None, 'key was not set for reform {} (name: {!r})'.format(self, self.name)
        if self.reference is not None and hasattr(self.reference, 'key'):
            reference_full_key = self.reference.full_key
            key = u'.'.join([reference_full_key, key])
        return key

    def modify_legislation_json(self, modifier_function):
        """
        Copy the reference TaxBenefitSystem legislation_json attribute and return it.
        Used by reforms which need to modify the legislation_json, usually in the build_reform() function.
        Validates the new legislation.
        """
        reference_legislation_json = self.reference.get_legislation()
        reference_legislation_json_copy = copy.deepcopy(reference_legislation_json)
        reform_legislation_json = modifier_function(reference_legislation_json_copy)
        assert reform_legislation_json is not None, \
            'modifier_function {} in module {} must return the modified legislation_json'.format(
                modifier_function.__name__,
                modifier_function.__module__,
                )
        reform_legislation_json, error = legislation_validators.validate_legislation_json(reform_legislation_json)
        assert error is None, \
            'The modified legislation_json of the reform "{}" is invalid, error: {}'.format(
                self.key, error).encode('utf-8')
        self._legislation_json = reform_legislation_json
        self.compact_legislation_by_instant_cache = {}


# Legislation JSON modifiers


def replace_scale_rate(scale_node, period, new_rate, old_rate=None, bracket_index=None):
    '''
    In a given `scale_node`, for a given `period`:
        - replace an `old_rate` by a `new_rate` or
        - set a `new_rate` given a `bracket_index`

    You must provide either `old_rate` or `bracket_index`.

    Note: modifies the `scale_node`.
    '''
    assert bool(old_rate is not None) ^ bool(bracket_index is not None), \
        'You must provide either `old_rate` or `bracket_index`'
    assert legislations.is_scale(scale_node), 'Scale node expected'
    period = periods.period(period)
    if bracket_index is not None:
        bracket = scale_node['brackets'][bracket_index]
        for rate in bracket['rate']:
            if rate['start'] >= str(period.start) and ('stop' not in rate or rate['stop'] <= str(period.stop)):
                rate['value'] = new_rate
    elif old_rate is not None:
        for bracket in scale_node['brackets']:
            for rate in bracket['rate']:
                if rate['value'] == old_rate and rate['start'] >= str(period.start) and (
                        'stop' not in rate or rate['stop'] <= str(period.stop)):
                    rate['value'] = new_rate
