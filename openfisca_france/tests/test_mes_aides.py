#! /usr/bin/env python
# -*- coding: utf-8 -*-


# OpenFisca -- A versatile microsimulation software
# By: OpenFisca Team <contact@openfisca.fr>
#
# Copyright (C) 2011, 2012, 2013, 2014, 2015 OpenFisca Team
# https://github.com/openfisca
#
# This file is part of OpenFisca.
#
# OpenFisca is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# OpenFisca is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import division

import os

import numpy as np
from openfisca_core import conv, scenarios
from openfisca_france.tests.base import tax_benefit_system
import yaml


def assert_near2(value, target_value, error_margin = 1, message = ''):
    if isinstance(value, (list, tuple)):
        value = np.array(value)
    if isinstance(target_value, (list, tuple)):
        target_value = np.array(target_value)
    if isinstance(message, unicode):
        message = message.encode('utf-8')
    if isinstance(value, np.ndarray):
        if error_margin <= 0:
            assert (target_value == value).all() or (target_value == value * 12).all() \
                or (target_value == value / 12).all(), '{}{} differs from {}'.format(message, value, target_value)
        else:
            assert (target_value - error_margin < value).all() and (value < target_value + error_margin).all() \
                or (target_value - error_margin < value * 12).all() \
                and (value * 12 < target_value + error_margin).all() \
                or (target_value - error_margin < value / 12).all() \
                and (value / 12 < target_value + error_margin).all(), \
                '{}{} differs from {} with a margin {} >= {}'.format(message, value, target_value,
                    abs(value - target_value), error_margin)
    else:
        if error_margin <= 0:
            assert target_value == value or target_value == value * 12 or target_value == value / 12, \
                '{}{} differs from {}'.format(message, value, target_value)
        else:
            assert target_value - error_margin < value < target_value + error_margin \
                or target_value - error_margin < value * 12 < target_value + error_margin \
                or target_value - error_margin < value / 12 < target_value + error_margin, \
                '{}{} differs from {} with a margin {} >= {}'.format(message, value, target_value,
                    abs(value - target_value), error_margin)


def check(name, period_str, test):
    scenario = test['scenario']
    scenario.suggest()
    simulation = scenario.new_simulation(debug = True)
    output_variables = test.get(u'output_variables')
    if output_variables is not None:
        for variable_name, expected_value in output_variables.iteritems():
            if isinstance(expected_value, dict):
                for requested_period, expected_value_at_period in expected_value.iteritems():
                    assert_near2(simulation.calculate(variable_name, requested_period, accept_other_period = True),
                        expected_value_at_period, error_margin = 0.007,
                        message = u'{}@{}: '.format(variable_name, requested_period))
            else:
                assert_near2(simulation.calculate(variable_name, accept_other_period = True), expected_value,
                    error_margin = 0.007, message = u'{}@{}: '.format(variable_name, period_str))


def test():
    dir_path = os.path.join(os.path.dirname(__file__), 'mes-aides.gouv.fr')
    for file_name in sorted(os.listdir(dir_path)):
        if not file_name.endswith('.yaml'):
            continue
        with open(os.path.join(dir_path, file_name)) as yaml_file:
            test = yaml.load(yaml_file)
            test, error = scenarios.make_json_or_python_to_test(tax_benefit_system)(test)
            if error is not None:
                embedding_error = conv.embed_error(test, u'errors', error)
                assert embedding_error is None, embedding_error
                conv.check((test, error))  # Generate an error.

            if test.get(u'ignore', False):
                continue

            yield check, test['name'], unicode(test['scenario'].period), test


if __name__ == "__main__":
    import argparse
    import logging
    import sys

    parser = argparse.ArgumentParser(description = __doc__)
    parser.add_argument('-n', '--name', default = None, help = "partial name of tests to execute")
    parser.add_argument('-v', '--verbose', action = 'store_true', default = False, help = "increase output verbosity")
    args = parser.parse_args()
    logging.basicConfig(level = logging.DEBUG if args.verbose else logging.WARNING, stream = sys.stdout)

    for test_index, (function, name, period_str, test) in enumerate(test(), 1):
        if args.name is not None and args.name not in name:
            continue
        print("=" * 120)
        print("Test {}: {} - {}".format(test_index, name.encode('utf-8'), period_str))
        print("=" * 120)
        function(name, period_str, test)