# -*- coding: utf-8 -*-


import collections
import glob
from inspect import isclass
from os import path
from imp import find_module, load_module
import importlib
import logging
from setuptools import find_packages

from . import conv, legislations, legislationsxml
from variables import AbstractVariable
from formulas import neutralize_column

log = logging.getLogger(__name__)


class VariableNotFound(Exception):
    pass


class VariableNameConflict(Exception):
    pass


class TaxBenefitSystem(object):
    _base_tax_benefit_system = None
    entity_class_by_key_plural = None
    person_key_plural = None
    json_to_attributes = staticmethod(conv.pipe(
        conv.test_isinstance(dict),
        conv.struct({}),
        ))
    reference = None  # Reference tax-benefit system. Used only by reforms. Note: Reforms can be chained.
    Scenario = None
    cache_blacklist = None
    DEFAULT_DECOMP_FILE = None

    def __init__(self, entities, legislation_json = None):
        # TODO: Currently: Don't use a weakref, because they are cleared by Paste (at least) at each call.
        self.column_by_name = collections.OrderedDict()
        self.automatically_loaded_variable = set()
        self.legislation_xml_info_list = []
        self._legislation_json = legislation_json
        self.legislation_node_by_instant_cache = {}  # weakref.WeakValueDictionary()

        if entities is None or len(entities) == 0:
            raise ValueError("A tax benefit sytem must have at least an entity.")
        self.entity_class_by_key_plural = {
            entity_class.key_plural: entity_class
            for entity_class in entities
            }

    @property
    def base_tax_benefit_system(self):
        base_tax_benefit_system = self._base_tax_benefit_system
        if base_tax_benefit_system is None:
            reference = self.reference
            if reference is None:
                return self
            self._base_tax_benefit_system = base_tax_benefit_system = reference.base_tax_benefit_system
        return base_tax_benefit_system

    # Legislation methods

    def legislation_at(self, instant, traced_simulation=None):
        legislation_json = self.get_legislation_json()
        assert legislation_json is not None
        if traced_simulation is None:
            legislation_node = self.legislation_node_by_instant_cache.get(instant)
            if legislation_node is None:
                legislation_json_at_instant = legislations.at_instant.generate_legislation_json_at_instant(
                    legislation_json, instant)
                legislation_node = legislations.at_instant.node_json_at_instant_to_objects(legislation_json_at_instant)
                self.legislation_node_by_instant_cache[instant] = legislation_node
        else:
            legislation_json_at_instant = legislations.generate_legislation_json_at_instant(legislation_json, instant)
            legislation_node = legislations.node_json_at_instant_to_objects(
                legislation_json_at_instant,
                traced_simulation = traced_simulation,
                )
        return legislation_node

    def get_legislation_json(self):
        if self._legislation_json is None:
            self._legislation_json = self.load_legislation_from_xml()
        return self._legislation_json

    def add_legislation_params(self, path_to_xml_file, path_in_legislation_tree=None):
        if path_in_legislation_tree is not None:
            if isinstance(path_in_legislation_tree, basestring):
                path_in_legislation_tree = path_in_legislation_tree.split('.')
        self.legislation_xml_info_list.append((path_to_xml_file, path_in_legislation_tree))
        # New parameters have been added, the legislation will have to be recomputed next time we need it.
        # Not very optimized, but today incremental building of the legislation is not implemented.
        self._legislation_json = None

    def load_legislation_from_xml(self, with_source_file_infos = False):
        state = conv.default_state
        xml_legislation_info_list_to_json = legislationsxml.make_xml_legislation_info_list_to_json(
            with_source_file_infos,
            )
        legislation_json = conv.check(xml_legislation_info_list_to_json)(self.legislation_xml_info_list, state = state)
        if self.preprocess_legislation is not None:
            legislation_json = self.preprocess_legislation(legislation_json)
        return legislation_json

    def preprocess_legislation(self, legislation_json):
        '''
        This method can be overloaded by countries inheriting TaxBenefitSystem.
        Its purpose is to allow enhancing the `legislation_json` for example to load parameter from other
        sources than the XML files, like CSV files for example.
        '''
        return legislation_json

    @classmethod
    def json_to_instance(cls, value, state = None):
        attributes, error = conv.pipe(
            cls.json_to_attributes,
            conv.default({}),
            )(value, state = state or conv.default_state)
        if error is not None:
            return attributes, error
        return cls(**attributes), None

    def new_scenario(self):
        scenario = self.Scenario()
        scenario.tax_benefit_system = self
        return scenario

    def prefill_cache(self):
        pass

    def load_variable(self, variable_class, update = False):
        name = unicode(variable_class.__name__)
        variable_type = variable_class.__bases__[0]
        attributes = dict(variable_class.__dict__)

        existing_column = self.get_column(name)
        if existing_column:
            if update:
                attributes['reference'] = existing_column
            else:
                # Variables that are dependencies of others (trough a conversion column)can be loaded automatically
                if name in self.automatically_loaded_variable:
                    self.automatically_loaded_variable.remove(name)
                    return self.get_column(name)
                raise VariableNameConflict(
                    u'Variable "{}" is already defined. Use `update_variable` to replace it.'.format(name))

        # We pass the variable_class just for introspection.
        variable = variable_type(name, attributes, variable_class)
        # We need the tax benefit system to identify columns mentioned by conversion variables.
        column = variable.to_column(self)
        self.column_by_name[column.name] = column

        return column

    def add_variable(self, variable_class):
        return self.load_variable(variable_class, update = False)

    def update_variable(self, variable_class):
        return self.load_variable(variable_class, update = True)

    def add_variables_from_file(self, file_path):
        try:
            module_name = path.splitext(path.basename(file_path))[0]
            module_directory = path.dirname(file_path)
            module = load_module(module_name, *find_module(module_name, [module_directory]))
            potential_variables = [getattr(module, item) for item in dir(module) if not item.startswith('__')]
            for pot_variable in potential_variables:
                # We only want to get the module classes defined in this module (not imported)
                if isclass(pot_variable) and \
                        issubclass(pot_variable, AbstractVariable) and \
                        pot_variable.__module__.endswith(module_name):
                    self.add_variable(pot_variable)
        except:
            log.error(u'Unable to load openfisca variables from file "{}"'.format(file_path))
            raise

    def add_variables_from_directory(self, directory):
        py_files = glob.glob(path.join(directory, "*.py"))
        for py_file in py_files:
            self.add_variables_from_file(py_file)
        subdirectories = glob.glob(path.join(directory, "*/"))
        for subdirectory in subdirectories:
            self.add_variables_from_directory(subdirectory)

    def add_variables(self, *variables):
        for variable in variables:
            self.add_variable(variable)

    def load_extension(self, extension):
        if path.isdir(extension):
            if find_packages(extension):
                # Load extension from a package directory
                extension_directory = path.join(extension, find_packages(extension)[0])
            else:
                # Load extension from a simple directory
                extension_directory = extension
        else:
            # Load extension from installed pip package
            try:
                package = importlib.import_module(extension)
                extension_directory = package.__path__[0]
            except ImportError:
                raise IOError(
                    "Error loading extension: {} is neither a directory, nor an installed package.".format(extension))

        self.add_variables_from_directory(extension_directory)
        param_file = path.join(extension_directory, 'parameters.xml')
        if path.isfile(param_file):
            self.add_legislation_params(param_file)

    def get_column(self, column_name, check_existence = False):
        column = self.column_by_name.get(column_name)
        if not column and check_existence:
            raise VariableNotFound(u'Variable "{}" not found in current tax benefit system'.format(column_name))
        return column

    def update_column(self, column_name, new_column):
        self.column_by_name[column_name] = new_column

    def neutralize_column(self, column_name):
        self.update_column(
            column_name,
            neutralize_column(self.reference.get_column(column_name, check_existence=True)),
            )

    def add_legislation_params(self, path_to_xml_file, path_in_legislation_tree = None):
        if path_in_legislation_tree is not None:
            path_in_legislation_tree = path_in_legislation_tree.split('.')

        self.legislation_xml_info_list.append(
            (path_to_xml_file, path_in_legislation_tree)
            )
        # New parameters have been added, the legislation will have to be recomputed next time we need it.
        # Not very optimized, but today incremental building of the legislation is not implemented.
        self._legislation_json = None

    def compute_legislation(self, with_source_file_infos = False):
        state = conv.default_state
        xml_legislation_info_list_to_json = legislationsxml.make_xml_legislation_info_list_to_json(
            with_source_file_infos,
            )
        legislation_json = conv.check(xml_legislation_info_list_to_json)(self.legislation_xml_info_list, state = state)
        if self.preprocess_legislation is not None:
            legislation_json = self.preprocess_legislation(legislation_json)
        self._legislation_json = legislation_json

    def get_legislation(self, path=None, instant=None, with_source_file_infos = False):
        '''
        Return the legislation parameters of the tax and benefit system.

        If a `path` is given, return the corresponding node of the legislation.
        `path` can be a string like 'x.y.z' or a list of strings like ['x', 'y', 'z'].

        If an `instant` is given, return a version of the legislation node containing only the values
        at the given `instant`.
        `instant` can be a string like "YYYY-MM-DD" or a value of type `Instant`.

        Examples:
            legislation = tax_benefit_system.get_legislation()
            ir_bareme = tax_benefit_system.get_legislation(path='ir.bareme')
            legislation_at_2015 = tax_benefit_system.get_legislation(instant='2015-01-01')
            ir_bareme_at_2015 = tax_benefit_system.get_legislation(path='ir.bareme', instant='2015-01-01')

        '''
        if self._legislation_json is None:
            self.compute_legislation(with_source_file_infos = with_source_file_infos)
        legislation_json = self._legislation_json
        if path is not None:
            legislation_json = legislations.get_node(legislation_json, path)
        if instant is not None:
            legislation_json = legislations.at_instant(legislation_json, instant)
        return legislation_json
