# -*- coding: utf-8 -*-

from nose.tools import assert_equal, assert_is_instance, assert_in, assert_is_not_none

from openfisca_core import legislations
from openfisca_core.tests.dummy_country import DummyTaxBenefitSystem


tax_benefit_system = DummyTaxBenefitSystem()


def test_get_legislation():
    legislation = tax_benefit_system.legislation_at()
    assert_is_instance(legislation, dict)


def test_get_legislation_with_path():
    taux = tax_benefit_system.legislation_at(path='csg.activite.deductible.taux')
    assert_is_instance(taux, dict)
    assert_in('values', taux)
    assert_is_instance(taux['values'], list)
    assert_equal(taux['values'][0]['value'], 0.051)


def test_get_legislation_with_instant():
    legislation_json = tax_benefit_system.legislation_at(instant='2010-01-01')
    assert_is_not_none(legislation_json)
    assert_is_instance(legislation_json, dict)
    brackets = legislations.get_node(legislation_json, 'csg.activite.deductible.abattement')['brackets']
    assert_equal(len(brackets), 1)


def test_get_legislation_with_path_and_instant():
    abattement = tax_benefit_system.legislation_at(path='csg.activite.deductible.abattement', instant='2010-01-01')
    assert_is_not_none(abattement)
    assert_is_instance(abattement, dict)
    assert_equal(len(abattement['brackets']), 1)


def test_multiple_xml_based_tax_benefit_system():
    legislation_json = tax_benefit_system.legislation_at()
    assert_is_not_none(legislation_json)
    assert_is_instance(legislation_json, dict)
    dated_legislation_json = legislations.generate_legislation_json_at_instant(legislation_json, '2012-01-01')
    assert_is_instance(dated_legislation_json, dict)
    compact_legislation = legislations.node_json_at_instant_to_objects(dated_legislation_json)
    assert_equal(compact_legislation.csg.activite.deductible.taux, 0.051)
    assert_equal(compact_legislation.csg.activite.crds.activite.taux, 0.005)
