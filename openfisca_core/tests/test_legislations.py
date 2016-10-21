# -*- coding: utf-8 -*-


from nose.tools import assert_equal, assert_in, assert_is_instance, assert_true, raises

from .. import legislations
from ..legislations.at_instant import generate_node_json_at_instant
from .dummy_country import DummyTaxBenefitSystem


tax_benefit_system = DummyTaxBenefitSystem()


def test_get_node():
    taux = legislations.get_node(tax_benefit_system.legislation_at(), 'csg.activite.deductible.taux')
    assert_is_instance(taux, dict)
    assert_in('values', taux)
    assert_is_instance(taux['values'], list)
    assert_equal(taux['values'][0]['value'], 0.051)


@raises(ValueError)
def test_get_node_with_path_too_long():
    legislations.get_node(tax_benefit_system.legislation_at(), 'csg.activite.deductible.abattement.x')


@raises(ValueError)
def test_get_node_with_wrong_path():
    legislations.get_node(tax_benefit_system.legislation_at(), 'xx')


def test_at_instant():
    abattement = legislations.get_node(tax_benefit_system.legislation_at(), 'csg.activite.deductible.abattement')
    abattement_at_instant = generate_node_json_at_instant(abattement, '2005-06-01')
    assert_true(legislations.is_scale(abattement_at_instant))
    assert_equal(len(abattement_at_instant['brackets']), 1)
    assert_equal(abattement_at_instant['brackets'][0]['rate'], 0.03)
    assert_equal(abattement_at_instant['brackets'][0]['threshold'], 0)


def test_is_scale():
    abattement = legislations.get_node(tax_benefit_system.legislation_at(), 'csg.activite.deductible.abattement')
    assert_true(legislations.is_scale(abattement))
