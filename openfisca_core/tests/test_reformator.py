# -*- coding: utf-8 -*-


from openfisca_core.reformator import Reformator
from openfisca_core.tests.test_countries import TestTaxBenefitSystem


def test_reformator():
    tax_benefit_system = TestTaxBenefitSystem()
    population_dataframe = generate_population()
    scenario = SurveyScenario(tax_benefit_system, population_dataframe, period)
    simulation = scenario.new_simulation()
    reformator = Reformator(simulation)
    reformator.reform_variable(variable_name='revdisp', criteria=['age', 'children', 'salaire_imposable'])
    revdisp = reformator.calculate('revdisp')
