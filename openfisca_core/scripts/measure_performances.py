#! /usr/bin/env python
# -*- coding: utf-8 -*-


"""Measure performances of a basic tax-benefit system to compare to other OpenFisca implementations."""


import argparse
import datetime
import logging
import sys
import time

import numpy as np
from numpy.core.defchararray import startswith

from openfisca_core import periods, simulations
from openfisca_core.columns import BoolCol, DateCol, FixedStrCol, FloatCol, IntCol
from openfisca_core.periods import ETERNITY
from openfisca_core.entities import build_entity
from openfisca_core.formulas import dated_function
from openfisca_core.variables import Variable
from openfisca_core.taxbenefitsystems import TaxBenefitSystem
from openfisca_core.tools import assert_near


args = None


def timeit(method):
    def timed(*args, **kwargs):
        start_time = time.time()
        result = method(*args, **kwargs)
        # print '%r (%r, %r) %2.9f s' % (method.__name__, args, kw, time.time() - start_time)
        print '{:2.6f} s'.format(time.time() - start_time)
        return result

    return timed


# Entities


PARENT1 = 0
PARENT2 = 1

Famille = build_entity(
    key = "famille",
    plural = "familles",
    label = u'Famille',
    roles = [
        {
            'key': 'parent',
            'plural': 'parents',
            'label': u'Parents',
            'subroles': ['demandeur', 'conjoint']
            },
        {
            'key': 'enfant',
            'plural': 'enfants',
            'label': u'Enfants',
            }
        ]
    )


Individu = build_entity(
    key = "individu",
    plural = "individus",
    label = u'Individu',
    is_person = True,
    )

# Input variables


class age_en_mois(Variable):
    column = IntCol
    entity = Individu
    label = u"Âge (en nombre de mois)"


class birth(Variable):
    column = DateCol
    entity = Individu
    label = u"Date de naissance"


class city_code(Variable):
    column = FixedStrCol(max_length = 5)
    entity = Famille
    column.definition_period = ETERNITY
    label = u"""Code INSEE "city_code" de la commune de résidence de la famille"""


class salaire_brut(Variable):
    column = FloatCol
    entity = Individu
    label = "Salaire brut"


# Calculated variables

class age(Variable):
    column = IntCol
    entity = Individu
    label = u"Âge (en nombre d'années)"

    def function(self, simulation, period):
        birth = simulation.get_array('birth', period)
        if birth is None:
            age_en_mois = simulation.get_array('age_en_mois', period)
            if age_en_mois is not None:
                return age_en_mois // 12
            birth = simulation.calculate('birth', period)
        return (np.datetime64(period.date) - birth).astype('timedelta64[Y]')


class dom_tom(Variable):
    column = BoolCol
    entity = Famille
    label = u"La famille habite-t-elle les DOM-TOM ?"

    def function(self, simulation, period):
        period = period.start.period('year').offset('first-of')
        city_code = simulation.calculate('city_code', period)
        return np.logical_or(startswith(city_code, '97'), startswith(city_code, '98'))


class revenu_disponible(Variable):
    column = FloatCol
    entity = Individu
    label = u"Revenu disponible de l'individu"

    def function(self, simulation, period):
        period = period.start.period(u'year').offset('first-of')
        rsa = simulation.calculate('rsa', period)
        salaire_imposable = simulation.calculate('salaire_imposable', period)
        return rsa + salaire_imposable * 0.7


class rsa(Variable):
    column = FloatCol
    entity = Individu
    label = u"RSA"

    @dated_function(datetime.date(2010, 1, 1))
    def function_2010(self, simulation, period):
        period = period.start.period(u'month').offset('first-of')
        salaire_imposable = simulation.calculate('salaire_imposable', period)
        return (salaire_imposable < 500) * 100.0

    @dated_function(datetime.date(2011, 1, 1), datetime.date(2012, 12, 31))
    def function_2011_2012(self, simulation, period):
        period = period.start.period(u'month').offset('first-of')
        salaire_imposable = simulation.calculate('salaire_imposable', period)
        return (salaire_imposable < 500) * 200.0

    @dated_function(datetime.date(2013, 1, 1))
    def function_2013(self, simulation, period):
        period = period.start.period(u'month').offset('first-of')
        salaire_imposable = simulation.calculate('salaire_imposable', period)
        return (salaire_imposable < 500) * 300


class salaire_imposable(Variable):
    column = FloatCol
    entity = Individu
    label = u"Salaire imposable"

    def function(individu, period):
        period = period.start.period(u'year').offset('first-of')
        dom_tom = individu.famille('dom_tom', period)
        salaire_net = individu('salaire_net', period)
        return salaire_net * 0.9 - 100 * dom_tom


class salaire_net(Variable):
    column = FloatCol
    entity = Individu
    label = u"Salaire net"

    def function(self, simulation, period):
        period = period.start.period(u'year').offset('first-of')
        salaire_brut = simulation.calculate('salaire_brut', period)
        return salaire_brut * 0.8


# TaxBenefitSystem instance declared after formulas


tax_benefit_system = TaxBenefitSystem([Famille, Individu])
tax_benefit_system.add_variables(age_en_mois, birth, city_code, salaire_brut, age,
    dom_tom, revenu_disponible, rsa, salaire_imposable, salaire_net)


@timeit
def check_revenu_disponible(year, city_code, expected_revenu_disponible):
    simulation = simulations.Simulation(period = periods.period(year), tax_benefit_system = tax_benefit_system)
    famille = simulation.entities["famille"]
    famille.count = 3
    famille.roles_count = 2
    famille.step_size = 1
    individu = simulation.entities["individu"]
    individu.count = 6
    individu.step_size = 2
    simulation.get_or_new_holder("city_code").array = np.array([city_code, city_code, city_code])
    famille.members_entity_id = np.array([0, 0, 1, 1, 2, 2])
    famille.members_legacy_role = np.array([PARENT1, PARENT2, PARENT1, PARENT2, PARENT1,
        PARENT2])
    simulation.get_or_new_holder("salaire_brut").array = np.array([0.0, 0.0, 50000.0, 0.0, 100000.0, 0.0])
    revenu_disponible = simulation.calculate('revenu_disponible')
    assert_near(revenu_disponible, expected_revenu_disponible, absolute_error_margin = 0.005)


def main():
    parser = argparse.ArgumentParser(description = __doc__)
    parser.add_argument('-v', '--verbose', action = 'store_true', default = False, help = "increase output verbosity")
    global args
    args = parser.parse_args()
    logging.basicConfig(level = logging.DEBUG if args.verbose else logging.WARNING, stream = sys.stdout)

    check_revenu_disponible(2009, '75101', np.array([0, 0, 25200, 0, 50400, 0]))
    check_revenu_disponible(2010, '75101', np.array([1200, 1200, 25200, 1200, 50400, 1200]))
    check_revenu_disponible(2011, '75101', np.array([2400, 2400, 25200, 2400, 50400, 2400]))
    check_revenu_disponible(2012, '75101', np.array([2400, 2400, 25200, 2400, 50400, 2400]))
    check_revenu_disponible(2013, '75101', np.array([3600, 3600, 25200, 3600, 50400, 3600]))

    check_revenu_disponible(2009, '97123', np.array([-70.0, -70.0, 25130.0, -70.0, 50330.0, -70.0]))
    check_revenu_disponible(2010, '97123', np.array([1130.0, 1130.0, 25130.0, 1130.0, 50330.0, 1130.0]))
    check_revenu_disponible(2011, '98456', np.array([2330.0, 2330.0, 25130.0, 2330.0, 50330.0, 2330.0]))
    check_revenu_disponible(2012, '98456', np.array([2330.0, 2330.0, 25130.0, 2330.0, 50330.0, 2330.0]))
    check_revenu_disponible(2013, '98456', np.array([3530.0, 3530.0, 25130.0, 3530.0, 50330.0, 3530.0]))


if __name__ == "__main__":
    sys.exit(main())
