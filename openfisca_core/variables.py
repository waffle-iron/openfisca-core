# -*- coding: utf-8 -*-


import inspect
import textwrap

from openfisca_core.formulas import DatedFormula, new_filled_column


class AbstractVariable(object):
    formula_class = None

    def __init__(self, name, attributes, variable_class):
        self.name = name
        self.attributes = attributes
        self.variable_class = variable_class

    def get_introspection_data(self, tax_benefit_system):
        comments = inspect.getcomments(self.variable_class)

        # Handle dynamically generated variable classes or Jupyter Notebooks, which have no source.
        try:
            absolute_file_path = inspect.getsourcefile(self.variable_class)
        except TypeError:
            source_file_path = None
        else:
            source_file_path = absolute_file_path.replace(tax_benefit_system.get_package_metadata()['location'], '')
        try:
            source_lines, start_line_number = inspect.getsourcelines(self.variable_class)
            source_code = textwrap.dedent(''.join(source_lines))
        except (IOError, TypeError):
            source_code, start_line_number = None, None

        return comments, source_file_path, source_code, start_line_number

    def to_column(self, tax_benefit_system):
        formula_class = self.__class__.formula_class
        entity = self.attributes.pop('entity', None)

        # For reform variable that replaces the existing reference one
        reference = self.attributes.pop('reference', None)
        if reference:
            if not entity:
                entity = reference.entity

        comments, source_file_path, source_code, start_line_number = self.get_introspection_data(tax_benefit_system)

        if entity is None:
            raise Exception('Variable {} must have an entity'.format(self.name))

        return new_filled_column(
            name = self.name,
            entity = entity,
            formula_class = formula_class,
            reference_column = reference,
            comments = comments,
            start_line_number = start_line_number,
            source_code = source_code,
            source_file_path = source_file_path,
            **self.attributes
            )


class Variable(AbstractVariable):
    formula_class = DatedFormula

