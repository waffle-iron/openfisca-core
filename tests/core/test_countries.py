# -*- coding: utf-8 -*-

import datetime

import numpy as np
from nose.tools import raises, assert_raises

from openfisca_core.variables import Variable
from openfisca_core.periods import YEAR
from openfisca_core.taxbenefitsystems import VariableNameConflict, VariableNotFound
from openfisca_core import periods
from openfisca_core.formulas import DIVIDE
from openfisca_dummy_country import DummyTaxBenefitSystem
from openfisca_core.tools import assert_near


tax_benefit_system = DummyTaxBenefitSystem()


def test_input_variable():
    year = 2016

    simulation = tax_benefit_system.new_scenario().init_single_entity(
        period = year,
        parent1 = dict(
            salaire_brut = 2000,
            ),
        ).new_simulation()
    assert_near(simulation.calculate_add('salaire_brut', year), [2000], absolute_error_margin=0.01)


def test_basic_calculation():
    year = 2016

    simulation = tax_benefit_system.new_scenario().init_single_entity(
        period = year,
        parent1 = dict(
            salaire_brut = 2000,
            ),
        ).new_simulation()
    assert_near(simulation.calculate_add('salaire_net', year), [1600], absolute_error_margin=0.01)


def test_params():
    year = 2013

    simulation = tax_benefit_system.new_scenario().init_single_entity(
        period = year,
        parent1 = dict(
            salaire_imposable = 10000,
            ),
        ).new_simulation()
    assert_near(simulation.calculate('revenu_disponible', year), [7000], absolute_error_margin=0.01)


def test_bareme():
    year = 2017

    simulation = tax_benefit_system.new_scenario().init_single_entity(
        period = year,
        parent1 = dict(
            salaire_brut = 20000,
            ),
        ).new_simulation()
    expected_result = 0.02 * 6000 + 0.06 * 6400 + 0.12 * 7600
    assert_near(simulation.calculate('contribution_sociale', year), [expected_result], absolute_error_margin=0.01)


def test_1_axis():
    year = 2013
    simulation = tax_benefit_system.new_scenario().init_single_entity(
        axes = [
            dict(
                count = 3,
                name = 'salaire_brut',
                max = 100000,
                min = 0,
                ),
            ],
        period = year,
        parent1 = {},
        parent2 = {},
        ).new_simulation(debug = True)
    assert_near(simulation.calculate('revenu_disponible_famille', year), [7200, 28800, 54000], absolute_error_margin = 0.005)


def test_2_parallel_axes_1_constant():
    year = 2013
    simulation = tax_benefit_system.new_scenario().init_single_entity(
        axes = [
            [
                dict(
                    count = 3,
                    name = 'salaire_brut',
                    max = 100000,
                    min = 0,
                    ),
                dict(
                    count = 3,
                    index = 1,
                    name = 'salaire_brut',
                    max = 0.0001,
                    min = 0,
                    ),
                ],
            ],
        period = year,
        parent1 = {},
        parent2 = {},
        ).new_simulation(debug = True)
    assert_near(simulation.calculate('revenu_disponible_famille', year), [7200, 28800, 54000], absolute_error_margin = 0.005)


def test_2_parallel_axes_different_periods():
    year = 2013
    simulation = tax_benefit_system.new_scenario().init_single_entity(
        axes = [
            [
                dict(
                    count = 3,
                    name = 'salaire_brut',
                    max = 120000,
                    min = 0,
                    period = year - 1,
                    ),
                dict(
                    count = 3,
                    index = 1,
                    name = 'salaire_brut',
                    max = 120000,
                    min = 0,
                    period = year,
                    ),
                ],
            ],
        period = year,
        parent1 = {},
        parent2 = {},
        ).new_simulation(debug = True)
    assert_near(simulation.calculate_add('salaire_brut', year - 1), [0, 0, 60000, 0, 120000, 0], absolute_error_margin = 0)
    assert_near(simulation.calculate('salaire_brut', '{}-01'.format(year - 1)), [0, 0, 5000, 0, 10000, 0],
        absolute_error_margin = 0)
    assert_near(simulation.calculate_add('salaire_brut', year), [0, 0, 0, 60000, 0, 120000], absolute_error_margin = 0)
    assert_near(simulation.calculate('salaire_brut', '{}-01'.format(year)), [0, 0, 0, 5000, 0, 10000],
        absolute_error_margin = 0)


def test_2_parallel_axes_same_values():
    year = 2013
    simulation = tax_benefit_system.new_scenario().init_single_entity(
        axes = [
            [
                dict(
                    count = 3,
                    index = 0,
                    name = 'salaire_brut',
                    max = 100000,
                    min = 0,
                    ),
                dict(
                    count = 3,
                    index = 1,
                    name = 'salaire_brut',
                    max = 100000,
                    min = 0,
                    ),
                ],
            ],
        period = year,
        parent1 = {},
        parent2 = {},
        ).new_simulation(debug = True)
    assert_near(simulation.calculate('revenu_disponible_famille', year), [7200, 50400, 100800], absolute_error_margin = 0.005)


def test_age():
    year = 2013
    month = '2013-01'
    simulation = tax_benefit_system.new_scenario().init_single_entity(
        period = year,
        parent1 = dict(
            birth = datetime.date(year - 40, 1, 1),
            ),
        ).new_simulation(debug = True)
    assert_near(simulation.calculate('age', month), [40], absolute_error_margin = 0.005)

    simulation = tax_benefit_system.new_scenario().init_single_entity(
        period = month,
        parent1 = dict(
            age_en_mois = 40 * 12 + 11,
            ),
        ).new_simulation(debug = True)
    assert_near(simulation.calculate('age', month), [40], absolute_error_margin = 0.005)


def check_revenu_disponible(year, city_code, expected_revenu_disponible):
    simulation = tax_benefit_system.new_scenario().init_single_entity(
        axes = [
            dict(
                count = 3,
                name = 'salaire_brut',
                max = 100000,
                min = 0,
                ),
            ],
        famille = dict(city_code = city_code),
        period = periods.period(year),
        parent1 = dict(),
        parent2 = dict(),
        ).new_simulation(debug = True)
    revenu_disponible = simulation.calculate('revenu_disponible', year)
    assert_near(revenu_disponible, expected_revenu_disponible, absolute_error_margin = 0.005)
    revenu_disponible_famille = simulation.calculate('revenu_disponible_famille', year)
    expected_revenu_disponible_famille = np.array([
        expected_revenu_disponible[i] + expected_revenu_disponible[i + 1]
        for i in range(0, len(expected_revenu_disponible), 2)
        ])
    assert_near(revenu_disponible_famille, expected_revenu_disponible_famille, absolute_error_margin = 0.005)


def test_revenu_disponible():
    yield check_revenu_disponible, 2009, '75101', np.array([0, 0, 25200, 0, 50400, 0])
    yield check_revenu_disponible, 2010, '75101', np.array([1200, 1200, 25200, 1200, 50400, 1200])
    yield check_revenu_disponible, 2011, '75101', np.array([2400, 2400, 25200, 2400, 50400, 2400])
    yield check_revenu_disponible, 2012, '75101', np.array([2400, 2400, 25200, 2400, 50400, 2400])
    yield check_revenu_disponible, 2013, '75101', np.array([3600, 3600, 25200, 3600, 50400, 3600])

    yield check_revenu_disponible, 2009, '97123', np.array([-70.0, -70.0, 25130.0, -70.0, 50330.0, -70.0])
    yield check_revenu_disponible, 2010, '97123', np.array([1130.0, 1130.0, 25130.0, 1130.0, 50330.0, 1130.0])
    yield check_revenu_disponible, 2011, '98456', np.array([2330.0, 2330.0, 25130.0, 2330.0, 50330.0, 2330.0])
    yield check_revenu_disponible, 2012, '98456', np.array([2330.0, 2330.0, 25130.0, 2330.0, 50330.0, 2330.0])
    yield check_revenu_disponible, 2013, '98456', np.array([3530.0, 3530.0, 25130.0, 3530.0, 50330.0, 3530.0])


def test_variable_with_reference():
    def new_simulation():
        return tax_benefit_system.new_scenario().init_single_entity(
            period = 2013,
            parent1 = dict(
                salaire_brut = 4000,
                ),
            ).new_simulation()

    revenu_disponible_avant_reforme = new_simulation().calculate('revenu_disponible', 2013)
    assert(revenu_disponible_avant_reforme > 0)

    class revenu_disponible(Variable):
        definition_period = YEAR

        def function(self, simulation, period):
            return self.zeros()

    tax_benefit_system.update_variable(revenu_disponible)
    revenu_disponible_apres_reforme = new_simulation().calculate('revenu_disponible', 2013)

    assert(revenu_disponible_apres_reforme == 0)


@raises(VariableNameConflict)
def test_variable_name_conflict():
    class revenu_disponible(Variable):
        reference = 'revenu_disponible'
        definition_period = YEAR

        def function(self, simulation, period):
            return self.zeros()
    tax_benefit_system.add_variable(revenu_disponible)


@raises(VariableNotFound)
def test_non_existing_variable():
    simulation = tax_benefit_system.new_scenario().init_single_entity(
        period = 2013,
        parent1 = dict(),
        ).new_simulation()

    simulation.calculate('non_existent_variable', 2013)


def test_calculate_variable_with_wrong_definition_period():
    simulation = tax_benefit_system.new_scenario().init_single_entity(
        period = 2013,
        parent1 = dict(
            salaire_brut = 4000,
            ),
        ).new_simulation()

    with assert_raises(ValueError) as error:
        simulation.calculate('rsa', 2013)

    error_message = str(error.exception)
    expected_words = ['period', '2013', 'month', 'rsa', 'ADD']

    for word in expected_words:
        assert word in error_message, u'Expected "{}" in error message "{}"'.format(word, error_message).encode('utf-8')


@raises(ValueError)
def test_wrong_use_of_divide_option():
    simulation = tax_benefit_system.new_scenario().init_single_entity(
        period = 2013,
        parent1 = dict(
            revenu_disponible = 12000,
            ),
        ).new_simulation()

    quarter = periods.period('2013-12').last_3_months
    simulation.individu('revenu_disponible', quarter, options = [DIVIDE])


@raises(ValueError)
def test_input_with_wrong_period():
    tax_benefit_system.new_scenario().init_single_entity(
        period = 2013,
        parent1 = dict(
            revenu_disponible = {'2015-02': 1200},
            ),
        ).new_simulation()


# 371 - start_date, stop_date, one function > fixed_tax
def test_dated_variable_with_one_formula():
    year = 1985
    simulation = tax_benefit_system.new_scenario().init_single_entity(
        period = year,
        parent1 = dict(
            birth = datetime.date(year - 20, 1, 1),
            ),
        ).new_simulation()
    assert (simulation.calculate('fixed_tax', year) == 400)

    var_fixed_tax = tax_benefit_system.column_by_name['fixed_tax']
    assert var_fixed_tax is not None

    assert var_fixed_tax.start == datetime.date(1980, 1, 1)
    assert var_fixed_tax.end == datetime.date(1989, 12, 31)

    assert var_fixed_tax.formula_class.dated_formulas_class.__len__() == 1
    fixed_tax_formula = var_fixed_tax.formula_class.dated_formulas_class[0]
    assert fixed_tax_formula is not None

    assert var_fixed_tax.start == fixed_tax_formula['start_instant'].date
    assert var_fixed_tax.end == fixed_tax_formula['stop_instant'].date


def has_dated_attributes(variable):
    return (variable.start is not None) and (variable.end is not None)


# 371 - @dated_function > rmi
def test_variable_with_one_formula():
    month = '2005-02'
    simulation = tax_benefit_system.new_scenario().init_single_entity(
        period = month,
        parent1 = dict(
            salaire_imposable = {'2005': 10000},
            ),
        ).new_simulation()
    assert_near(simulation.calculate('rmi', month), [0], absolute_error_margin=0.01)

    var_rmi = tax_benefit_system.column_by_name['rmi']
    assert var_rmi is not None

    assert not has_dated_attributes(var_rmi)
    assert var_rmi.formula_class.dated_formulas_class.__len__() == 1

    rmi_formula = var_rmi.formula_class.dated_formulas_class[0]
    assert rmi_formula is not None
    assert rmi_formula['start_instant'].date == datetime.date(2000, 1, 1)
    assert rmi_formula['stop_instant'].date == datetime.date(2009, 12, 31)


# 371 - @dated_function without stop/different names > rsa
def test_variable_with_dated_formulas__different_names():
    dated_function_nb = 3
    simulation = tax_benefit_system.new_scenario().init_single_entity(
        period = '2009',
        parent1 = dict(
            salaire_imposable = {'2010': 0,
                                 '2011': 15000,
                                 '2013': 15150,
                                 '2016': 17000},
            ),
        ).new_simulation()
    assert_near(simulation.calculate('rsa', '2010-05'), [100], absolute_error_margin=0.01)

    variable = tax_benefit_system.column_by_name['rsa']
    assert variable is not None
    assert not has_dated_attributes(variable)

    assert variable.formula_class.dated_formulas_class.__len__() == dated_function_nb
    i = 0
    for formula in variable.formula_class.dated_formulas_class:
        assert formula is not None, (dated_function_nb + " formulas expected in " + variable.formula_class.dated_formulas_class)
        # assert formula['formula_class'].holder is not None, ("Undefined holder for '" + variable.name + "', function#" + str(i))
        assert formula['start_instant'] is not None, ("Missing 'start' date on '" + variable.name + "', function#" + str(i))
        if i < (dated_function_nb - 1):
            assert formula['stop_instant'] is not None, ("Deprecated 'end' date but 'stop_instant' deduction expected on '" + variable.name + "', function#" + str(i))
        i += 1

    assert_near(simulation.calculate('rsa', '2011-05'), [0], absolute_error_margin=0.01)


# #371 - start_date, stop_date, @dated_function/different names > api
def test_dated_variable_with_formulas__different_names():
    month = '1999-01'
    dated_function_nb = 2
    simulation = tax_benefit_system.new_scenario().init_single_entity(
        period = month,
        parent1 = dict(
            ),
        enfants = [
            dict(
                ),
            dict(
                ),
            ]
        ).new_simulation()
    assert_near(simulation.calculate('api', month), [0], absolute_error_margin=0.01)

    variable = tax_benefit_system.column_by_name['api']
    assert variable is not None
    assert has_dated_attributes(variable)

    assert variable.formula_class.dated_formulas_class.__len__() == dated_function_nb

    i = 0
    formula = variable.formula_class.dated_formulas_class[0]
    assert formula is not None, (dated_function_nb + " formulas expected in " + variable.formula_class.dated_formulas_class)
    assert formula['start_instant'] is not None, ("'start_instant' deduced from 'start' attribute expected on '" + variable.name + "', function#" + str(i))
    assert formula['start_instant'].date == variable.start

    i += 1
    formula = variable.formula_class.dated_formulas_class[1]
    assert formula is not None, (dated_function_nb + " formulas expected in " + variable.formula_class.dated_formulas_class)
    assert formula['stop_instant'] is not None, ("'stop_instant' deduced from 'stop' attribute expected on '" + variable.name + "', function#" + str(i))
    assert formula['stop_instant'].date == variable.end


# 371 - start_date, stop_date, @dated_function/one name > api_same_function_name
def test_dated_variable_with_formulas__same_name():
    month = '1999-01'
    dated_function_nb = 2
    simulation = tax_benefit_system.new_scenario().init_single_entity(
        period = month,
        parent1 = dict(
            ),
        enfants = [
            dict(
                ),
            dict(
                ),
            ]
        ).new_simulation()
    assert_near(simulation.calculate('api_same_function_name', month), [0], absolute_error_margin=0.01)

    variable = tax_benefit_system.column_by_name['api_same_function_name']
    assert variable is not None
    assert has_dated_attributes(variable)

    # Should take the first function declared only.
    assert variable.formula_class.dated_formulas_class.__len__() == 1

    i = 0
    formula = variable.formula_class.dated_formulas_class[0]
    assert formula is not None, (dated_function_nb + " formulas expected in " + variable.formula_class.dated_formulas_class)
    assert formula['start_instant'] is not None, ("'start_instant' deduced from 'start' attribute expected on '" + variable.name + "', function#" + str(i))
    assert formula['start_instant'].date == variable.start

    # Should apply stop_date attribute to the first function declared.
    assert formula['stop_instant'] is not None, ("'stop_instant' deduced from 'stop' attribute expected on '" + variable.name + "', function#" + str(i))
    assert formula['stop_instant'].date == variable.end


# 371 - start_date, stop_date, @dated_function/stop_date older than function start > api_stop_date_before_function_start
def test_dated_variable_with_formulas__stop_date_older():
    month = '1999-01'
    dated_function_nb = 2
    simulation = tax_benefit_system.new_scenario().init_single_entity(
        period = month,
        parent1 = dict(
            ),
        enfants = [
            dict(
                ),
            dict(
                ),
            ]
        ).new_simulation()
    assert_near(simulation.calculate('api_stop_date_before_function_start', month), [0], absolute_error_margin=0.01)

    variable = tax_benefit_system.column_by_name['api_stop_date_before_function_start']
    assert variable is not None
    assert has_dated_attributes(variable)

    # Should take the first function declared only.
    assert variable.formula_class.dated_formulas_class.__len__() == 1

    i = 0
    formula = variable.formula_class.dated_formulas_class[0]
    assert formula is not None, (dated_function_nb + " formulas expected in " + variable.formula_class.dated_formulas_class)
    assert formula['start_instant'] is not None, ("'start_instant' deduced from 'start' attribute expected on '" + variable.name + "', function#" + str(i))
    assert formula['start_instant'].date == variable.start

    # Should apply stop_date attribute to the first function declared even if it inactivates it.
    assert formula['stop_instant'] is not None, ("'stop_date' older than 'start_instant' shouldn't be applied on '" + variable.name + "', function#" + str(i))
    assert formula['stop_instant'].date == variable.end
