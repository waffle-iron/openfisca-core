# -*- coding: utf-8 -*-


"""Handle legislative parameters in JSON format."""


from . import at_instant  # noqa


# JSON nodes navigation functions


def get_node(legislation_json, path):
    '''
    Return a node in the `legislation_json` tree at the given `path`.
    `path` can be a string like "x.y.z" or a list of strings like ['x', 'y', 'z'].
    '''
    if isinstance(path, basestring):
        path = path.split('.')
    path_str = '.'.join(path)
    node = legislation_json
    for index, key in enumerate(path):
        if node['@type'] != 'Node':
            message = u'The given path "{}" is too long, it should be "{}", which targets a "{}".'.format(
                path_str,
                '.'.join(path[:index]),
                node['@type'],
                )
            if key in node:
                message += u' Remaining path fragment(s) should be accessed using the standard `node[\'{0}\']` ' \
                    u'Python operator.'.format(key)
            raise ValueError(message)
        assert 'children' in node, 'Expected "children" key, got: {}'.format(node.keys())
        if key not in node['children']:
            raise ValueError(
                u'The given path "{}" mentions the fragment "{}" which is not found. '
                u'The following legislation nodes are available at this level of the legislation tree: {}.'.format(
                    path_str,
                    key,
                    node['children'].keys(),
                    )
                )
        node = node['children'][key]
    return node


def is_scale(node):
    '''
    Returns True if the given `node` is a "Scale" (Barème in French).
    '''
    return node.get('@type') == 'Scale' and isinstance(node.get('brackets'), list)
