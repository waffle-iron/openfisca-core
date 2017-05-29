# -*- coding: utf-8 -*-

import pkg_resources
import os
import sys
import subprocess

from nose.tools import nottest, raises
from openfisca_dummy_country import DummyTaxBenefitSystem

from openfisca_core.tools.test_runner import run_tests, generate_tests

tax_benefit_system = DummyTaxBenefitSystem()

openfisca_dummy_country_dir = pkg_resources.get_distribution('OpenFisca-Dummy-Country').location
yamls_tests_dir = os.path.join(openfisca_dummy_country_dir, 'openfisca_dummy_country', 'tests')

# Declare that these two functions are not tests to run with nose
nottest(run_tests)
nottest(generate_tests)


@nottest
def run_yaml_test(path, options = {}):
    yaml_path = os.path.join(yamls_tests_dir, path)

    # We are testing tests, and don't want the latter to print anything, so we temporarily deactivate stderr.
    old_stderr = sys.stderr
    sys.stderr = open(os.devnull, 'w')
    result = run_tests(tax_benefit_system, yaml_path, options)
    sys.stderr = old_stderr
    return result


def test_success():
    assert run_yaml_test('test_success.yaml')


def test_fail():
    assert run_yaml_test('test_failure.yaml') is False


def test_relative_error_margin_success():
    assert run_yaml_test('test_relative_error_margin.yaml')


def test_relative_error_margin_fail():
    assert run_yaml_test('failing_test_relative_error_margin.yaml') is False


def test_absolute_error_margin_success():
    assert run_yaml_test('test_absolute_error_margin.yaml')


def test_absolute_error_margin_fail():
    assert run_yaml_test('failing_test_absolute_error_margin.yaml') is False


def test_run_tests_from_directory():
    dir_path = os.path.join(yamls_tests_dir, 'directory')
    assert run_yaml_test(dir_path)


def test_with_reform():
    assert run_yaml_test('test_with_reform.yaml')


def test_run_tests_from_directory_fail():
    assert run_yaml_test(yamls_tests_dir) is False


def test_name_filter():
    assert run_yaml_test(
        yamls_tests_dir,
        options = {'name_filter': 'success'}
        )


def test_shell_script():
    yaml_path = os.path.join(yamls_tests_dir, 'test_success.yaml')
    command = ['openfisca-run-test', yaml_path, '-c', 'openfisca_dummy_country']
    with open(os.devnull, 'wb') as devnull:
        subprocess.check_call(command, stdout = devnull, stderr = devnull)


@raises(subprocess.CalledProcessError)
def test_failing_shell_script():
    yaml_path = os.path.join(yamls_tests_dir, 'test_failure.yaml')
    command = ['openfisca-run-test', yaml_path, '-c', 'openfisca_dummy_country']
    with open(os.devnull, 'wb') as devnull:
        subprocess.check_call(command, stdout = devnull, stderr = devnull)


def test_shell_script_with_reform():
    yaml_path = os.path.join(yamls_tests_dir, 'test_with_reform_2.yaml')
    command = ['openfisca-run-test', yaml_path, '-c', 'openfisca_dummy_country', '-r', 'openfisca_dummy_country.dummy_reforms.neutralization_rsa']
    with open(os.devnull, 'wb') as devnull:
        subprocess.check_call(command, stdout = devnull, stderr = devnull)


def test_shell_script_with_extension():
    extension_dir = os.path.join(openfisca_dummy_country_dir, 'openfisca_dummy_country', 'dummy_extension')
    command = ['openfisca-run-test', extension_dir, '-c', 'openfisca_dummy_country', '-e', extension_dir]
    with open(os.devnull, 'wb') as devnull:
        subprocess.check_call(command, stdout = devnull, stderr = devnull)
