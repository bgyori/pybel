# -*- coding: utf-8 -*-

"""
Node Filters
------------

A node predicate is a function that takes two arguments: a :class:`BELGraph` and a node tuple. It returns a boolean
representing whether the node passed the given test.

This module contains a set of default functions for filtering lists of nodes and building node predicates.

A general use for a node predicate is to use the built-in :func:`filter` in code like
:code:`filter(your_node_predicate, graph)`
"""

from collections import Iterable
from .node_predicates import keep_node_permissive

__all__ = [
    'concatenate_node_predicates',
    'filter_nodes',
    'get_nodes',
    'count_passed_node_filter',
]


def concatenate_node_predicates(node_predicates=None):
    """Concatenates multiple node filters to a new filter that requires all filters to be met

    :param node_predicates: A predicate or list of predicates (graph, node) -> bool
    :type node_predicates: types.FunctionType or iter[types.FunctionType]
    :return: A combine predicate (graph, node) -> bool
    :rtype: types.FunctionType

    Example usage:

    >>> from pybel.dsl import protein, gene
    >>> from pybel.struct.filters.node_predicates import not_pathology, node_exclusion_predicate_builder
    >>> app_protein = protein(name='APP', namespace='HGNC')
    >>> app_gene = gene(name='APP', namespace='HGNC')
    >>> app_filter = node_exclusion_predicate_builder([app_protein, app_gene])
    >>> my_filter = concatenate_node_predicates([not_pathology, app_filter])
    """
    # If no predicates are given, then return the trivially permissive predicate
    if not node_predicates:
        return keep_node_permissive

    # If a predicate outside a list is given, just return it
    if not isinstance(node_predicates, Iterable):
        return node_predicates

    node_predicates = list(node_predicates)

    # If only one predicate is given, don't bother wrapping it
    if 1 == len(node_predicates):
        return node_predicates[0]

    def concatenated_node_predicate(graph, node):
        """Passes only for a nodes that pass all enclosed predicates

        :param BELGraph graph: A BEL Graph
        :param tuple node: A BEL node
        :return: If the node passes all enclosed predicates
        :rtype: bool
        """
        return all(
            node_predicate(graph, node)
            for node_predicate in node_predicates
        )

    return concatenated_node_predicate


def filter_nodes(graph, node_predicates=None):
    """Applies a set of predicates to the nodes iterator of a BEL graph

    :param BELGraph graph: A BEL graph
    :param node_predicates: A node predicate or list/tuple of node predicates
    :type node_predicates: types.FunctionType or iter[types.FunctionType]
    :return: An iterable of nodes that pass all predicates
    :rtype: iter
    """

    # If no predicates are given, return the standard node iterator
    if not node_predicates:
        for node in graph:
            yield node
    else:
        concatenated_predicate = concatenate_node_predicates(node_predicates=node_predicates)
        for node in graph:
            if concatenated_predicate(graph, node):
                yield node


def get_nodes(graph, node_predicates=None):
    """Gets the set of all nodes that pass the predicates

    :param BELGraph graph: A BEL graph
    :param node_predicates: A node predicate or list/tuple of node predicates
    :type node_predicates: types.FunctionType or iter[types.FunctionType]
    :return: The set of nodes passing the predicates
    :rtype: set[tuple]
    """
    return set(filter_nodes(graph, node_predicates=node_predicates))


def count_passed_node_filter(graph, node_predicates=None):
    """Counts how many nodes pass a given set of filters

    :param pybel.BELGraph graph: A BEL graph
    :param node_predicates: A node predicate or list/tuple of node predicates
    :type node_predicates: types.FunctionType or iter[types.FunctionType]
    :return: The number of nodes passing the given set of predicates
    :rtype: int
    """
    return sum(1 for _ in filter_nodes(graph, node_predicates=node_predicates))
