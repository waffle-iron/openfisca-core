# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import os

from openfisca_core.tools.test_runner import run_tests
from openfisca_core.scripts import add_tax_benefit_system_arguments, build_tax_benefit_sytem


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('path', help = "paths (files or directories) of tests to execute", nargs = '+')
    parser = add_tax_benefit_system_arguments(parser)
    parser.add_argument('-n', '--name_filter', default = None, help = "partial name of tests to execute. Only tests with the given name_filter in their name, file name, or keywords will be run.")
    parser.add_argument('-v', '--verbose', action = 'store_true', default = False, help = "increase output verbosity")
    parser.add_argument('--nose', action = 'store_true', default = False, help = "use nosetests to run the tests")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    logging.basicConfig(level = logging.DEBUG if args.verbose else logging.WARNING, stream = sys.stdout)

    tax_benefit_system = build_tax_benefit_sytem(args.country_package, args.extensions, args.reforms)

    options = {
        'verbose': args.verbose,
        'name_filter': args.name_filter,
        'nose': args.nose,
        }

    tests_found = False

    for path in args.path:
        path = os.path.abspath(path)
        nb_tests = run_tests(tax_benefit_system, path, options)
        tests_found = tests_found or nb_tests > 0

    if not tests_found and not args.nose:
        print("No tests found!")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
