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

import logging
log = logging.getLogger(__name__)
import numpy as np


def exec_function(formula, simulation, period):
    holder = formula.holder
    column = holder.column
    entity = holder.entity
    debug = simulation.debug
    try:
        array = formula.function(simulation, period)
    except:
        log.error(u'An error occurred while calling formula {}@{}<{}> in module {}'.format(
            column.name, entity.key_plural, str(period), formula.function.__module__,
            ))
        raise
    # TODO Remove this backward compatibility check.
    if isinstance(array, tuple):
        log.debug('Tuple detected! {}'.format(array))
        period, array = array
    assert isinstance(array, np.ndarray), u"Function {}@{}<{}>() --> {}, doesn't return a numpy array".format(
        column.name, entity.key_plural, str(period), array).encode('utf-8')
    assert array.size == entity.count, \
        u'Function {}@{}<{}>() --> {} returns an array of size {}, but size {} is expected for {}'.format(
            column.name, entity.key_plural, str(period), stringify_array(array),
            array.size, entity.count, entity.key_singular).encode('utf-8')
    if debug:
        try:
            # cf http://stackoverflow.com/questions/6736590/fast-check-for-nan-in-numpy
            if np.isnan(np.min(array)):
                nan_count = np.count_nonzero(np.isnan(array))
                raise NaNCreationError(u'Function {}@{}<{}>() --> {} returns {} NaN value(s)'.format(
                    column.name, entity.key_plural, str(period), stringify_array(array), nan_count).encode('utf-8'))
        except TypeError:
            pass
    if array.dtype != column.dtype:
        log.debug(u'Cast array dtype: {} to column dtype: {}'.format(array.dtype, column.dtype))
        array = array.astype(column.dtype)
    return array

def exec_function_or_default(formula, simulation, period):
    holder = formula.holder
    column = holder.column
    if formula.function is not None:
        array = exec_function(formula, simulation, period)
    else:
        array = np.empty(holder.entity.count, dtype = column.dtype)
        array.fill(column.default)
    return array

def monthly_arithmetic_function(formula, simulation, period):
    """
    If requested period is greater than a month (a year or many months),
    then calculate all months and sum the results.
    """
    holder = formula.holder
    column = holder.column
    array_by_period = holder._array_by_period
    if array_by_period is None:
        holder._array_by_period = array_by_period = {}
    if period.unit == u'month' and period.size == 1:
        array = exec_function_or_default(formula, simulation, period)
        array_by_period[period] = array
        return array
    else:
        after_instant = period.start.offset(period.size, period.unit)
        array = np.zeros(holder.entity.count, dtype = column.dtype)
        month = period.start.period(u'month')
        while month.start < after_instant:
            month_array = array_by_period.get(month)
            if month_array is None:
                month_array = exec_function_or_default(formula, simulation, month)
                array_by_period[month] = month_array
            array += month_array
            month = month.offset(1)
        array_by_period[period] = array
        return array

def monthly_state_function(formula, simulation, period):
    """
    If requested period is greather than a month,
    then return the first known value of this period
    or exec the function for the first month if it exists
    """
    holder = formula.holder
    column = holder.column
    array_by_period = holder._array_by_period
    if array_by_period is None:
        holder._array_by_period = array_by_period = {}
    if period.unit == u'month' and period.size == 1:
        array = exec_function_or_default(formula, simulation, period)
        array_by_period[period] = array
        return array
    else:
        first_month = period.start.period(u'month')
        cached_array_first_month = array_by_period.get(first_month)
        if cached_array_first_month is not None:
            return cached_array_first_month
        elif formula.function is not None:
            return exec_function(formula, simulation, first_month)
        else:
            month = first_month.offset(1)
            after_instant = period.start.offset(period.size, period.unit)
            while month.start < after_instant:
                month_array = array_by_period.get(month)
                if month_array is not None:
                    array_by_period[period] = month_array
                    return month_array
                month = month.offset(1)
            # Cas où on n'a pas trouvé de valeur dans le cache
            array = np.empty(holder.entity.count, dtype = column.dtype)
            array.fill(column.default)
            return array

def yearly_arithmetic_function(formula, simulation, period):
    holder = formula.holder
    column = holder.column
    array_by_period = holder._array_by_period
    if array_by_period is None:
        holder._array_by_period = array_by_period = {}
    if period.unit == u'year' and period.size == 1:
        array = exec_function_or_default(formula, simulation, period)
        array_by_period[period] = array
        return array
    elif period.unit == u"year":
        after_instant = period.start.offset(period.size, period.unit)
        array = np.zeros(holder.entity.count, dtype = column.dtype)
        year = period.start.period(u'year')
        while year.start < after_instant:
            year_array = array_by_period.get(year)
            if year_array is None:
                year_array = exec_function_or_default(formula, simulation, year)
                array_by_period[year] = year_array
            array += year_array
            year = year.offset(1)
        array_by_period[period] = array
        return array
    elif is_external_output:
        print("TODO")
        #TODO: divice
    else:
        log.error(u'Yearly arithmetic formula {0} cannot be calculated for a monthly period {1}. You can use explicitely calculate_divide if you \
		wish to get a monthly approximation of {0}'.format(
            column.name, str(period)))
        raise Exception

def requested_period_added_value(formula, simulation, period):
    # This formula is used for variables that can be added to match requested period.
    holder = formula.holder
    column = holder.column
    period_size = period.size
    period_unit = period.unit
    if holder._array_by_period is not None and (period_size > 1 or period_unit == u'year'):
        after_instant = period.start.offset(period_size, period_unit)
        if period_size > 1:
            array = np.zeros(holder.entity.count, dtype = column.dtype)
            sub_period = period.start.period(period_unit)
            while sub_period.start < after_instant:
                sub_array = holder._array_by_period.get(sub_period)
                if sub_array is None:
                    array = None
                    break
                array += sub_array
                sub_period = sub_period.offset(1)
            if array is not None:
                return period, array
        if period_unit == u'year':
            array = np.zeros(holder.entity.count, dtype = column.dtype)
            month = period.start.period(u'month')
            while month.start < after_instant:
                month_array = holder._array_by_period.get(month)
                if month_array is None:
                    array = None
                    break
                array += month_array
                month = month.offset(1)
            if array is not None:
                return period, array
    if formula.function is not None:
        return period, exec_function(formula, simulation, period)
    array = np.empty(holder.entity.count, dtype = column.dtype)
    array.fill(column.default)
    return period, array

def requested_period_default_value(formula, simulation, period):
    if formula.function is not None:
        return period, exec_function(formula, simulation, period)
    holder = formula.holder
    column = holder.column
    array = np.empty(holder.entity.count, dtype = column.dtype)
    array.fill(column.default)
    return period, array

def requested_period_default_value_neutralized(formula, simulation, period):
    holder = formula.holder
    column = holder.column
    array = np.empty(holder.entity.count, dtype = column.dtype)
    array.fill(column.default)
    return period, array

def requested_period_last_value(formula, simulation, period):
    # This formula is used for variables that are constants between events and period size independent.
    # It returns the latest known value for the requested period.
    holder = formula.holder
    if holder._array_by_period is not None:
        for last_period, last_array in sorted(holder._array_by_period.iteritems(), reverse = True):
            if last_period.start <= period.start and (formula.function is None or last_period.stop >= period.stop):
                return period, last_array
    if formula.function is not None:
        return period, exec_function(formula, simulation, period)
    column = holder.column
    array = np.empty(holder.entity.count, dtype = column.dtype)
    array.fill(column.default)
    return period, array

def permanent_default_value(formula, simulation, period):
    if formula.function is not None:
        return period, base_functions.exec_function(formula, simulation, period)
    holder = formula.holder
    column = holder.column
    array = np.empty(holder.entity.count, dtype = column.dtype)
    array.fill(column.default)
    return period, array
