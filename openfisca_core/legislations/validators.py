# -*- coding: utf-8 -*-


"""Validate legislative parameters in JSON format."""


import collections
import datetime
import itertools

from .. import conv


def N_(message):
    return message


units = [
    u'currency',
    u'day',
    u'hour',
    u'month',
    u'year',
    ]


# Level-1 Converters


def make_validate_values_json_dates(require_consecutive_dates = False):
    def validate_values_json_dates(values_json, state = None):
        if not values_json:
            return values_json, None
        if state is None:
            state = conv.default_state

        errors = {}
        for index, value_json in enumerate(values_json):
            stop_date_str = value_json.get('stop')
            if stop_date_str is not None and value_json['start'] > stop_date_str:
                errors[index] = dict(to = state._(u"Last date must be greater than first date"))

        sorted_values_json = sorted(values_json, key = lambda value_json: value_json['start'], reverse = True)
        next_value_json = sorted_values_json[0]
        for index, value_json in enumerate(itertools.islice(sorted_values_json, 1, None)):
            next_date_str = (datetime.date(*(int(fragment) for fragment in value_json['stop'].split('-'))) +
                datetime.timedelta(days = 1)).isoformat()
            if require_consecutive_dates and next_date_str < next_value_json['start']:
                errors.setdefault(index, {})['start'] = state._(u"Dates of values are not consecutive")
            elif next_date_str > next_value_json['start']:
                errors.setdefault(index, {})['start'] = state._(u"Dates of values overlap")
            next_value_json = value_json

        return sorted_values_json, errors or None

    return validate_values_json_dates


def validate_dated_legislation_json(dated_legislation_json, state = None):
    if dated_legislation_json is None:
        return None, None
    if state is None:
        state = conv.default_state

    dated_legislation_json, error = conv.pipe(
        conv.test_isinstance(dict),
        conv.struct(
            dict(
                instant = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.iso8601_input_to_date,
                    conv.date_to_iso8601_str,
                    conv.not_none,
                    ),
                ),
            constructor = collections.OrderedDict,
            default = conv.noop,
            drop_none_values = 'missing',
            keep_value_order = True,
            ),
        )(dated_legislation_json, state = state)
    if error is not None:
        return dated_legislation_json, error

    instant = dated_legislation_json.pop('instant')
    dated_legislation_json, error = validate_dated_node_json(dated_legislation_json, state = state)
    dated_legislation_json['instant'] = instant
    return dated_legislation_json, error


def validate_dated_node_json(node, state = None):
    if node is None:
        return None, None
    state = conv.add_ancestor_to_state(state, node)

    validated_node, error = conv.test_isinstance(dict)(node, state = state)
    if error is not None:
        conv.remove_ancestor_from_state(state, node)
        return validated_node, error

    validated_node, errors = conv.struct(
        {
            '@context': conv.pipe(
                conv.test_isinstance(basestring),
                conv.make_input_to_url(full = True),
                conv.test_equals(u'http://openfisca.fr/contexts/dated-legislation.jsonld'),
                ),
            '@type': conv.pipe(
                conv.test_isinstance(basestring),
                conv.cleanup_line,
                conv.test_in((u'Node', u'Parameter', u'Scale')),
                conv.not_none,
                ),
            'comment': conv.pipe(
                conv.test_isinstance(basestring),
                conv.cleanup_text,
                ),
            'description': conv.pipe(
                conv.test_isinstance(basestring),
                conv.cleanup_line,
                ),
            'end_line_number': conv.test_isinstance(int),
            'start_line_number': conv.test_isinstance(int),
            },
        constructor = collections.OrderedDict,
        default = conv.noop,
        drop_none_values = 'missing',
        keep_value_order = True,
        )(validated_node, state = state)
    if errors is not None:
        conv.remove_ancestor_from_state(state, node)
        return validated_node, errors

    validated_node.pop('@context', None)  # Remove optional @context everywhere. It will be added to root node later.
    node_converters = {
        '@type': conv.noop,
        'comment': conv.noop,
        'description': conv.noop,
        'end_line_number': conv.test_isinstance(int),
        'start_line_number': conv.test_isinstance(int),
        }
    node_type = validated_node['@type']
    if node_type == u'Node':
        node_converters.update(dict(
            children = conv.pipe(
                conv.test_isinstance(dict),
                conv.uniform_mapping(
                    conv.pipe(
                        conv.test_isinstance(basestring),
                        conv.cleanup_line,
                        conv.not_none,
                        ),
                    conv.pipe(
                        validate_dated_node_json,
                        conv.not_none,
                        ),
                    ),
                conv.empty_to_none,
                conv.not_none,
                ),
            ))
    elif node_type == u'Parameter':
        node_converters.update(dict(
            format = conv.pipe(
                conv.test_isinstance(basestring),
                conv.input_to_slug,
                conv.test_in([
                    'boolean',
                    'float',
                    'integer',
                    'rate',
                    ]),
                ),
            unit = conv.pipe(
                conv.test_isinstance(basestring),
                conv.input_to_slug,
                conv.test_in(units),
                ),
            value = conv.pipe(
                conv.item_or_sequence(
                    validate_dated_value_json,
                    ),
                conv.not_none,
                ),
            ))
    else:
        assert node_type == u'Scale'
        node_converters.update(dict(
            option = conv.pipe(
                conv.test_isinstance(basestring),
                conv.input_to_slug,
                conv.test_in((
                    'contrib',
                    'main-d-oeuvre',
                    'noncontrib',
                    )),
                ),
            brackets = conv.pipe(
                conv.test_isinstance(list),
                conv.uniform_sequence(
                    validate_dated_bracket_json,
                    drop_none_items = True,
                    ),
                validate_dated_brackets_json_types,
                conv.empty_to_none,
                conv.not_none,
                ),
            unit = conv.pipe(
                conv.test_isinstance(basestring),
                conv.input_to_slug,
                conv.test_in((
                    'currency',
                    )),
                ),
            ))
    validated_node, errors = conv.struct(
        node_converters,
        constructor = collections.OrderedDict,
        drop_none_values = 'missing',
        keep_value_order = True,
        )(validated_node, state = state)

    conv.remove_ancestor_from_state(state, node)
    return validated_node, errors


def validate_dated_bracket_json(bracket, state = None):
    if bracket is None:
        return None, None
    state = conv.add_ancestor_to_state(state, bracket)
    validated_bracket, errors = conv.pipe(
        conv.test_isinstance(dict),
        conv.struct(
            dict(
                amount = conv.item_or_sequence(
                    validate_dated_value_json,
                    ),
                base = conv.item_or_sequence(
                    conv.pipe(
                        validate_dated_value_json,
                        conv.test_greater_or_equal(0),
                        ),
                    ),
                comment = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_text,
                    ),
                end_line_number = conv.test_isinstance(int),
                rate = conv.item_or_sequence(
                    conv.pipe(
                        validate_dated_value_json,
                        conv.test_between(0, 1),
                        ),
                    ),
                start_line_number = conv.test_isinstance(int),
                threshold = conv.item_or_sequence(
                    conv.pipe(
                        validate_dated_value_json,
                        conv.test_greater_or_equal(0),
                        ),
                    ),
                ),
            constructor = collections.OrderedDict,
            drop_none_values = 'missing',
            keep_value_order = True,
            ),
        )(bracket, state = state)
    conv.remove_ancestor_from_state(state, bracket)
    return validated_bracket, errors


def validate_dated_brackets_json_types(brackets, state = None):
    if not brackets:
        return brackets, None

    has_amount = any(
        'amount' in bracket
        for bracket in brackets
        )
    if has_amount:
        if state is None:
            state = conv.default_state
        errors = {}
        for bracket_index, bracket in enumerate(brackets):
            if 'base' in bracket:
                errors.setdefault(bracket_index, {})['base'] = state._(u"A scale can't contain both amounts and bases")
            if 'rate' in bracket:
                errors.setdefault(bracket_index, {})['rate'] = state._(u"A scale can't contain both amounts and rates")
        if errors:
            return brackets, errors
    return brackets, None


def validate_dated_value_json(value, state = None):
    if value is None:
        return None, None
    container = state.ancestors[-1]
    container_format = container.get('format')
    value_converters = dict(
        boolean = conv.condition(
            conv.test_isinstance(int),
            conv.test_in((0, 1)),
            conv.test_isinstance(bool),
            ),
        float = conv.condition(
            conv.test_isinstance(int),
            conv.anything_to_float,
            conv.test_isinstance(float),
            ),
        integer = conv.condition(
            conv.test_isinstance(float),
            conv.pipe(
                conv.test(lambda number: round(number) == number),
                conv.function(int),
                ),
            conv.test_isinstance(int),
            ),
        rate = conv.condition(
            conv.test_isinstance(int),
            conv.anything_to_float,
            conv.test_isinstance(float),
            ),
        )
    value_converter = value_converters.get(container_format or 'float')  # Only parameters have a "format".
    assert value_converter is not None, 'Wrong format "{}", allowed: {}, container: {}'.format(
        container_format, value_converters.keys(), container)
    return value_converter(value, state = state or conv.default_state)


def validate_node_json(node, state = None):
    if node is None:
        return None, None
    state = conv.add_ancestor_to_state(state, node)

    validated_node, error = conv.test_isinstance(dict)(node, state = state)
    if error is not None:
        conv.remove_ancestor_from_state(state, node)
        return validated_node, error

    validated_node, errors = conv.struct(
        {
            '@context': conv.pipe(
                conv.test_isinstance(basestring),
                conv.make_input_to_url(full = True),
                conv.test_equals(u'http://openfisca.fr/contexts/legislation.jsonld'),
                ),
            '@type': conv.pipe(
                conv.test_isinstance(basestring),
                conv.cleanup_line,
                conv.test_in((u'Node', u'Parameter', u'Scale')),
                conv.not_none,
                ),
            'comment': conv.pipe(
                conv.test_isinstance(basestring),
                conv.cleanup_text,
                ),
            'description': conv.pipe(
                conv.test_isinstance(basestring),
                conv.cleanup_line,
                ),
            'end_line_number': conv.test_isinstance(int),
            'start_line_number': conv.test_isinstance(int),
            },
        constructor = collections.OrderedDict,
        default = conv.noop,
        drop_none_values = 'missing',
        keep_value_order = True,
        )(validated_node, state = state)
    if errors is not None:
        conv.remove_ancestor_from_state(state, node)
        return validated_node, errors

    validated_node.pop('@context', None)  # Remove optional @context everywhere. It will be added to root node later.
    node_converters = {
        '@type': conv.noop,
        'comment': conv.noop,
        'description': conv.noop,
        'end_line_number': conv.noop,
        'start_line_number': conv.noop,
        }
    node_type = validated_node['@type']
    if node_type == u'Node':
        node_converters.update(dict(
            children = conv.pipe(
                conv.test_isinstance(dict),
                conv.uniform_mapping(
                    conv.pipe(
                        conv.test_isinstance(basestring),
                        conv.cleanup_line,
                        conv.not_none,
                        ),
                    conv.pipe(
                        validate_node_json,
                        conv.not_none,
                        ),
                    ),
                conv.empty_to_none,
                conv.not_none,
                ),
            ))
    elif node_type == u'Parameter':
        node_converters.update(dict(
            format = conv.pipe(
                conv.test_isinstance(basestring),
                conv.input_to_slug,
                conv.test_in([
                    'boolean',
                    'float',
                    'integer',
                    'rate',
                    ]),
                ),
            unit = conv.pipe(
                conv.test_isinstance(basestring),
                conv.input_to_slug,
                conv.test_in(units),
                ),
            values = conv.pipe(
                conv.test_isinstance(list),
                conv.uniform_sequence(
                    validate_value_json,
                    drop_none_items = True,
                    ),
                make_validate_values_json_dates(require_consecutive_dates = True),
                conv.empty_to_none,
                conv.not_none,
                ),
            ))
    else:
        assert node_type == u'Scale'
        node_converters.update(dict(
            brackets = conv.pipe(
                conv.test_isinstance(list),
                conv.uniform_sequence(
                    validate_bracket_json,
                    drop_none_items = True,
                    ),
                validate_brackets_json_types,
                validate_brackets_json_dates,
                conv.empty_to_none,
                conv.not_none,
                ),
            option = conv.pipe(
                conv.test_isinstance(basestring),
                conv.input_to_slug,
                conv.test_in((
                    'contrib',
                    'main-d-oeuvre',
                    'noncontrib',
                    )),
                ),
            rates_kind = conv.pipe(
                conv.test_isinstance(basestring),
                conv.test_in((
                    'average',
                    )),
                ),
            unit = conv.pipe(
                conv.test_isinstance(basestring),
                conv.input_to_slug,
                conv.test_in((
                    'currency',
                    )),
                ),
            ))
    validated_node, errors = conv.struct(
        node_converters,
        constructor = collections.OrderedDict,
        drop_none_values = 'missing',
        keep_value_order = True,
        )(validated_node, state = state)

    conv.remove_ancestor_from_state(state, node)
    return validated_node, errors

validate_legislation_json = validate_node_json


def validate_bracket_json(bracket, state = None):
    if bracket is None:
        return None, None
    state = conv.add_ancestor_to_state(state, bracket)
    validated_bracket, errors = conv.pipe(
        conv.test_isinstance(dict),
        conv.struct(
            dict(
                amount = validate_values_holder_json,
                base = validate_values_holder_json,
                comment = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_text,
                    ),
                end_line_number = conv.test_isinstance(int),
                rate = validate_values_holder_json,
                start_line_number = conv.test_isinstance(int),
                threshold = conv.pipe(
                    validate_values_holder_json,
                    conv.not_none,
                    ),
                ),
            constructor = collections.OrderedDict,
            drop_none_values = 'missing',
            keep_value_order = True,
            ),
        conv.test(lambda bracket: bool(bracket.get('amount')) ^ bool(bracket.get('rate')),
            error = N_(u"Either amount or rate must be provided")),
        )(bracket, state = state)
    conv.remove_ancestor_from_state(state, bracket)
    return validated_bracket, errors


def validate_brackets_json_dates(brackets, state = None):
    if not brackets:
        return brackets, None
    if state is None:
        state = conv.default_state
    errors = {}

    previous_bracket = brackets[0]
    for bracket_index, bracket in enumerate(itertools.islice(brackets, 1, None), 1):
        for key in ('amount', 'base', 'rate', 'threshold'):
            valid_segments = []
            for value_json in (previous_bracket.get(key) or []):
                from_date = datetime.date(*(int(fragment) for fragment in value_json['start'].split('-')))
                # Note: to_date may be None for first valid segment.
                to_date_str = value_json.get('stop')
                to_date = None if to_date_str is None \
                    else datetime.date(*(int(fragment) for fragment in to_date_str.split('-')))
                if valid_segments and valid_segments[-1][0] == to_date + datetime.timedelta(days = 1):
                    valid_segments[-1] = (from_date, valid_segments[-1][1])
                else:
                    valid_segments.append((from_date, to_date))
            for value_index, value_json in enumerate(bracket.get(key) or []):
                from_date = datetime.date(*(int(fragment) for fragment in value_json['start'].split('-')))
                # Note: to_date may be None for first value_json.
                to_date_str = value_json.get('stop')
                to_date = None if to_date_str is None \
                    else datetime.date(*(int(fragment) for fragment in to_date_str.split('-')))
                for valid_segment in valid_segments:
                    valid_to_date = valid_segment[1]
                    if valid_segment[0] <= from_date and (
                            valid_to_date is None or to_date is not None and to_date <= valid_to_date):
                        break
                else:
                    errors.setdefault(bracket_index, {}).setdefault(key, {}).setdefault(value_index,
                        {})['start'] = state._(u"Dates don't belong to valid dates of previous bracket")
        previous_bracket = bracket
    if errors:
        return brackets, errors

    for bracket_index, bracket in enumerate(itertools.islice(brackets, 1, None), 1):
        amount_segments = []
        for value_json in (bracket.get('amount') or []):
            from_date = datetime.date(*(int(fragment) for fragment in value_json['start'].split('-')))
            # Note: to_date may be None for first amount segment.
            to_date_str = value_json.get('stop')
            to_date = None if to_date_str is None \
                else datetime.date(*(int(fragment) for fragment in to_date_str.split('-')))
            if amount_segments and amount_segments[-1][0] == to_date + datetime.timedelta(days = 1):
                amount_segments[-1] = (from_date, amount_segments[-1][1])
            else:
                amount_segments.append((from_date, to_date))

        rate_segments = []
        for value_json in (bracket.get('rate') or []):
            from_date = datetime.date(*(int(fragment) for fragment in value_json['start'].split('-')))
            # Note: to_date may be None for first rate segment.
            to_date_str = value_json.get('stop')
            to_date = None if to_date_str is None \
                else datetime.date(*(int(fragment) for fragment in to_date_str.split('-')))
            if rate_segments and rate_segments[-1][0] == to_date + datetime.timedelta(days = 1):
                rate_segments[-1] = (from_date, rate_segments[-1][1])
            else:
                rate_segments.append((from_date, to_date))

        threshold_segments = []
        for value_json in (bracket.get('threshold') or []):
            from_date = datetime.date(*(int(fragment) for fragment in value_json['start'].split('-')))
            # Note: to_date may be None for first threshold segment.
            to_date_str = value_json.get('stop')
            to_date = None if to_date_str is None \
                else datetime.date(*(int(fragment) for fragment in to_date_str.split('-')))
            if threshold_segments and threshold_segments[-1][0] == to_date + datetime.timedelta(days = 1):
                threshold_segments[-1] = (from_date, threshold_segments[-1][1])
            else:
                threshold_segments.append((from_date, to_date))

        for value_index, value_json in enumerate(bracket.get('base') or []):
            from_date = datetime.date(*(int(fragment) for fragment in value_json['start'].split('-')))
            # Note: to_date may be None for first value_json.
            to_date_str = value_json.get('stop')
            to_date = None if to_date_str is None \
                else datetime.date(*(int(fragment) for fragment in to_date_str.split('-')))
            for rate_segment in rate_segments:
                rate_to_date = rate_segment[1]
                if rate_segment[0] <= from_date and (
                        rate_to_date is None or to_date is not None and to_date <= rate_to_date):
                    break
            else:
                errors.setdefault(bracket_index, {}).setdefault('base', {}).setdefault(value_index,
                    {})['start'] = state._(u"Dates don't belong to rate dates")

        for value_index, value_json in enumerate(bracket.get('amount') or []):
            from_date = datetime.date(*(int(fragment) for fragment in value_json['start'].split('-')))
            # Note: to_date may be None for first value_json.
            to_date_str = value_json.get('stop')
            to_date = None if to_date_str is None \
                else datetime.date(*(int(fragment) for fragment in to_date_str.split('-')))
            for threshold_segment in threshold_segments:
                threshold_to_date = threshold_segment[1]
                if threshold_segment[0] <= from_date and (
                        threshold_to_date is None or to_date is not None and to_date <= threshold_to_date):
                    break
            else:
                errors.setdefault(bracket_index, {}).setdefault('amount', {}).setdefault(value_index,
                    {})['start'] = state._(u"Dates don't belong to threshold dates")

        for value_index, value_json in enumerate(bracket.get('rate') or []):
            from_date = datetime.date(*(int(fragment) for fragment in value_json['start'].split('-')))
            # Note: to_date may be None for first value_json.
            to_date_str = value_json.get('stop')
            to_date = None if to_date_str is None \
                else datetime.date(*(int(fragment) for fragment in to_date_str.split('-')))
            for threshold_segment in threshold_segments:
                threshold_to_date = threshold_segment[1]
                if threshold_segment[0] <= from_date and (
                        threshold_to_date is None or to_date is not None and to_date <= threshold_to_date):
                    break
            else:
                errors.setdefault(bracket_index, {}).setdefault('rate', {}).setdefault(value_index,
                    {})['start'] = state._(u"Dates don't belong to threshold dates")

        for value_index, value_json in enumerate(bracket.get('threshold') or []):
            from_date = datetime.date(*(int(fragment) for fragment in value_json['start'].split('-')))
            # Note: to_date may be None for first value_json.
            to_date_str = value_json.get('stop')
            to_date = None if to_date_str is None \
                else datetime.date(*(int(fragment) for fragment in to_date_str.split('-')))
            for amount_segment in amount_segments:
                amount_to_date = amount_segment[1]
                if amount_segment[0] <= from_date and (
                        amount_to_date is None or to_date is not None and to_date <= amount_to_date):
                    break
            else:
                for rate_segment in rate_segments:
                    rate_to_date = rate_segment[1]
                    if rate_segment[0] <= from_date and (
                            rate_to_date is None or to_date is not None and to_date <= rate_to_date):
                        break
                else:
                    errors.setdefault(bracket_index, {}).setdefault('threshold', {}).setdefault(value_index,
                        {})['start'] = state._(u"Dates don't belong to amount or rate dates")

    return brackets, errors or None


def validate_brackets_json_types(brackets, state = None):
    if not brackets:
        return brackets, None

    has_amount = any(
        'amount' in bracket
        for bracket in brackets
        )
    if has_amount:
        if state is None:
            state = conv.default_state
        errors = {}
        for bracket_index, bracket in enumerate(brackets):
            if 'base' in bracket:
                errors.setdefault(bracket_index, {})['base'] = state._(u"A scale can't contain both amounts and bases")
            if 'rate' in bracket:
                errors.setdefault(bracket_index, {})['rate'] = state._(u"A scale can't contain both amounts and rates")
        if errors:
            return brackets, errors
    return brackets, None


def validate_value_json(value, state = None):
    if value is None:
        return None, None
    container = state.ancestors[-1]
    container_format = container.get('format')
    value_converters = dict(
        boolean = conv.condition(
            conv.test_isinstance(int),
            conv.test_in((0, 1)),
            conv.test_isinstance(bool),
            ),
        float = conv.condition(
            conv.test_isinstance(int),
            conv.anything_to_float,
            conv.test_isinstance(float),
            ),
        integer = conv.condition(
            conv.test_isinstance(float),
            conv.pipe(
                conv.test(lambda number: round(number) == number),
                conv.function(int),
                ),
            conv.test_isinstance(int),
            ),
        rate = conv.condition(
            conv.test_isinstance(int),
            conv.anything_to_float,
            conv.test_isinstance(float),
            ),
        )
    value_converter = value_converters.get(container_format or 'float')  # Only parameters have a "format".
    assert value_converter is not None, 'Wrong format "{}", allowed: {}, container: {}'.format(
        container_format, value_converters.keys(), container)
    state = conv.add_ancestor_to_state(state, value)
    validated_value, errors = conv.pipe(
        conv.test_isinstance(dict),
        conv.struct(
            {
                u'comment': conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_text,
                    ),
                u'end_line_number': conv.test_isinstance(int),
                u'start': conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.iso8601_input_to_date,
                    conv.date_to_iso8601_str,
                    conv.not_none,
                    ),
                u'start_line_number': conv.test_isinstance(int),
                u'stop': conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.iso8601_input_to_date,
                    conv.date_to_iso8601_str,
                    ),
                u'value': conv.pipe(
                    value_converter,
                    conv.not_none,
                    ),
                },
            constructor = collections.OrderedDict,
            drop_none_values = 'missing',
            keep_value_order = True,
            ),
        )(value, state = state)
    conv.remove_ancestor_from_state(state, value)
    return validated_value, errors


validate_values_holder_json = conv.pipe(
    conv.test_isinstance(list),
    conv.uniform_sequence(
        validate_value_json,
        drop_none_items = True,
        ),
    make_validate_values_json_dates(require_consecutive_dates = False),
    conv.empty_to_none,
    )


# Level-2 Converters


validate_any_legislation_json = conv.pipe(
    conv.test_isinstance(dict),
    conv.condition(
        conv.test(lambda legislation_json: 'datesim' in legislation_json),
        validate_dated_legislation_json,
        validate_legislation_json,
        ),
    )
