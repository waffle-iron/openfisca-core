# -*- coding: utf-8 -*-


"""Reform class and functions used to modify the tax and benefit system."""


from . import legislations, legislationsxml, periods
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


class LegislationUpdater(object):
    def __init__(self, legislation_json):
        self.legislation_json = legislation_json

    def add(self, node):
        '''
        Add a given `node` to the legislation tree.

        `node` can be a `string` containing XML.
        '''
        if isinstance(node, basestring):
            code, node_json = legislationsxml.load_code_and_json_from_xml_string(node)
        else:
            raise NotImplementedError(u'Other types not implemented')
        self.legislation_json['children'][code] = node_json

    # Reminder: __getattr__ is called only when attribute is not found.
    def __getattr__(self, key):
        import ipdb; ipdb.set_trace()


class Reform(TaxBenefitSystem):
    name = None

    def __init__(self, reference):
        self.entity_class_by_key_plural = reference.entity_class_by_key_plural
        self._legislation_json = reference.get_legislation_json()
        self.legislation_node_by_instant_cache = {}  # weakref.WeakValueDictionary()
        self.column_by_name = reference.column_by_name.copy()
        self.Scenario = reference.Scenario
        self.DEFAULT_DECOMP_FILE = reference.DEFAULT_DECOMP_FILE
        self.reference = reference
        self.key = unicode(self.__class__.__name__)
        # Legislation updater
        self.legislation = LegislationUpdater(self.get_legislation_json())
        self.apply()

    def apply():
        # TODO Add a link to the documentation in the error message.
        raise NotImplementedError(u'Inherit this method in your Reform sub-class.')

    @property
    def full_key(self):
        key = self.key
        assert key is not None, 'key was not set for reform {} (name: {!r})'.format(self, self.name)
        if self.reference is not None and hasattr(self.reference, 'key'):
            reference_full_key = self.reference.full_key
            key = u'.'.join([reference_full_key, key])
        return key


# Legislation JSON modifiers


def replace_scale_rate(scale_node, period, new_rate, old_rate=None, bracket_index=None):
    '''
    Modify a scale.

    In a given `scale_node`, and for a given `period`:
        - replace an `old_rate` by a `new_rate` or
        - set a `new_rate` given a `bracket_index`
    If no bracket matches, a ValueError is raised.

    You must provide either `old_rate` or `bracket_index`.

    Note: modifies the `scale_node`.
    '''
    assert bool(old_rate is not None) ^ bool(bracket_index is not None), \
        'You must provide either `old_rate` or `bracket_index`'
    if not legislations.is_scale(scale_node):
        raise TypeError(u'The given `scale_node` must be a scale, meaning its scale_node[\'@type\'] == \'Scale\'.')
    period = periods.period(period)
    matched = False
    if bracket_index is not None:
        bracket = scale_node['brackets'][bracket_index]
        for rate in bracket['rate']:
            if rate['start'] >= str(period.start) and ('stop' not in rate or rate['stop'] <= str(period.stop)):
                rate['value'] = new_rate
                matched = True
    elif old_rate is not None:
        for bracket in scale_node['brackets']:
            for rate in bracket['rate']:
                if rate['value'] == old_rate and rate['start'] >= str(period.start) and (
                        'stop' not in rate or rate['stop'] <= str(period.stop)):
                    rate['value'] = new_rate
                    matched = True
    if not matched:
        raise ValueError(u'No bracket matched the given arguments, so no rate was updated.')


def update_legislation_between(items, start_instant, stop_instant, value):
    """
    Iterates items (a dict with start, stop, value key) and returns new items sorted by start date,
    according to these rules:
    * if the period matches no existing item, the new item is yielded as-is
    * if the period strictly overlaps another one, the new item is yielded as-is
    * if the period non-strictly overlaps another one, the existing item is partitioned, the period in common removed,
      the new item is yielded as-is and the parts of the existing item are yielded
    """
    assert isinstance(items, collections.Sequence), items
    new_items = []
    new_item = collections.OrderedDict((
        ('start', start_instant),
        ('stop', stop_instant),
        ('value', value),
        ))
    inserted = False
    for item in items:
        item_start = periods.instant(item['start'])
        item_stop = item.get('stop')
        if item_stop is not None:
            item_stop = periods.instant(item_stop)
        if item_stop is not None and item_stop < start_instant or item_start > stop_instant:
            # non-overlapping items are kept: add and skip
            new_items.append(
                collections.OrderedDict((
                    ('start', item['start']),
                    ('stop', item['stop'] if item_stop is not None else None),
                    ('value', item['value']),
                    ))
                )
            continue

        if item_stop == stop_instant and item_start == start_instant:  # exact matching: replace
            if not inserted:
                new_items.append(
                    collections.OrderedDict((
                        ('start', str(start_instant)),
                        ('stop', str(stop_instant)),
                        ('value', new_item['value']),
                        ))
                    )
                inserted = True
            continue

        if item_start < start_instant and item_stop is not None and item_stop <= stop_instant:
            # left edge overlapping are corrected and new_item inserted
            new_items.append(
                collections.OrderedDict((
                    ('start', item['start']),
                    ('stop', str(start_instant.offset(-1, 'day'))),
                    ('value', item['value']),
                    ))
                )
            if not inserted:
                new_items.append(
                    collections.OrderedDict((
                        ('start', str(start_instant)),
                        ('stop', str(stop_instant)),
                        ('value', new_item['value']),
                        ))
                    )
                inserted = True

        if item_start < start_instant and (item_stop is None or item_stop > stop_instant):
            # new_item contained in item: divide, shrink left, insert, new, shrink right
            new_items.append(
                collections.OrderedDict((
                    ('start', item['start']),
                    ('stop', str(start_instant.offset(-1, 'day'))),
                    ('value', item['value']),
                    ))
                )
            if not inserted:
                new_items.append(
                    collections.OrderedDict((
                        ('start', str(start_instant)),
                        ('stop', str(stop_instant)),
                        ('value', new_item['value']),
                        ))
                    )
                inserted = True

            new_items.append(
                collections.OrderedDict((
                    ('start', str(stop_instant.offset(+1, 'day'))),
                    ('stop', item['stop'] if item_stop is not None else None),
                    ('value', item['value']),
                    ))
                )
        if item_start >= start_instant and item_stop is not None and item_stop < stop_instant:
            # right edge overlapping are corrected
            if not inserted:
                new_items.append(
                    collections.OrderedDict((
                        ('start', str(start_instant)),
                        ('stop', str(stop_instant)),
                        ('value', new_item['value']),
                        ))
                    )
                inserted = True

            new_items.append(
                collections.OrderedDict((
                    ('start', str(stop_instant.offset(+1, 'day'))),
                    ('stop', item['stop']),
                    ('value', item['value']),
                    ))
                )
        if item_start >= start_instant and item_stop is not None and item_stop <= stop_instant:
            # drop those
            continue

    return sorted(new_items, key = lambda item: item['start'])
