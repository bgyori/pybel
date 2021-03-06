# -*- coding: utf-8 -*-

"""

CX JSON
~~~~~~~
CX is an aspect-oriented network interchange format encoded in JSON with a format inspired by the JSON-LD encoding of
Resource Description Framework (RDF). It is primarily used by the Network Data Exchange (NDEx) and more recent versions
of Cytoscape.

.. seealso::

    - The NDEx Data Model `Specification <http://www.home.ndexbio.org/data-model/>`_
    - `Cytoscape.js <http://js.cytoscape.org/>`_
    - CX Support for Cytoscape.js on the Cytoscape `App Store <http://apps.cytoscape.org/apps/cxsupport>`_

"""

import json
import logging
import time
from collections import defaultdict

from ..canonicalize import node_to_bel
from ..constants import *
from ..struct import BELGraph
from ..utils import expand_dict, flatten_dict, hash_node

CX_NODE_NAME = 'label'

__all__ = [
    'to_cx',
    'to_cx_jsons',
    'to_cx_file',
    'from_cx',
    'from_cx_jsons',
    'from_cx_file',
    'NDEX_SOURCE_FORMAT',
]

log = logging.getLogger(__name__)

NDEX_SOURCE_FORMAT = "ndex:sourceFormat"


def _dict_to_cx(d, key_tag='k', value_tag='v'):
    """
    :param dict d:
    :param str key_tag:
    :param str value_tag:
    :rtype: list[dict]
    """
    return [
        {
            key_tag: k,
            value_tag: v
        }
        for k, v in d.items()
    ]


def _cx_to_dict(list_of_dicts, key_tag='k', value_tag='v'):
    """
    :param list[dict] list_of_dicts:
    :param str key_tag:
    :param str value_tag:
    :rtype: dict
    """
    return {
        d[key_tag]: d[value_tag]
        for d in list_of_dicts
    }


def calculate_canonical_cx_identifier(graph, node):
    """Calculates the canonical name for a given node. If it is a simple node, uses the namespace:name combination.
    Otherwise, it uses the BEL string.

    :param BELGraph graph: A BEL Graph
    :param tuple node: A node
    :return: Appropriate identifier for the node for CX indexing
    :rtype: str
    """
    data = graph.node[node]

    if data[FUNCTION] == COMPLEX and NAMESPACE in data:
        return '{}:{}'.format(data[NAMESPACE], data[NAME])

    if VARIANTS in data or FUSION in data or data[FUNCTION] in {REACTION, COMPOSITE, COMPLEX}:
        return node_to_bel(data)

    if VARIANTS not in data and FUSION not in data:  # this is should be a simple node
        return '{}:{}'.format(data[NAMESPACE], data[NAME])

    raise ValueError('Unexpected node data: {}'.format(data))


def build_node_mapping(graph):
    """Builds a mapping from a graph's nodes to their canonical sort order
    
    :param BELGraph graph: A BEL graph 
    :return: A mapping from a graph's nodes to their canonical sort order
    :rtype: dict[tuple,int]
    """
    return {
        node: node_index
        for node_index, node in enumerate(sorted(graph, key=hash_node))
    }


def to_cx(graph):
    """Converts BEL Graph to CX data format (as in-memory JSON) for use with `NDEx <http://www.ndexbio.org/>`_

    :param BELGraph graph: A BEL Graph
    :return: The CX JSON for this graph
    :rtype: list

    .. seealso::

        - `NDEx Python Client <https://github.com/ndexbio/ndex-python>`_
        - `PyBEL / NDEx Python Client Wrapper <https://github.com/pybel/pybel2ndex>`_

    """
    node_mapping = build_node_mapping(graph)
    node_index_data = {}
    nodes_entry = []
    node_attributes_entry = []

    for node, node_index in node_mapping.items():
        data = graph.node[node]
        node_index_data[node_index] = data

        nodes_entry.append({
            '@id': node_index,
            'n': calculate_canonical_cx_identifier(graph, node)
        })

        for k, v in data.items():
            if k == VARIANTS:
                for i, el in enumerate(v):
                    for a, b in flatten_dict(el).items():
                        node_attributes_entry.append({
                            'po': node_index,
                            'n': '{}_{}_{}'.format(k, i, a),
                            'v': b
                        })
            elif k == FUSION:
                for a, b in flatten_dict(v).items():
                    node_attributes_entry.append({
                        'po': node_index,
                        'n': '{}_{}'.format(k, a),
                        'v': b
                    })

            elif k == NAME:
                node_attributes_entry.append({
                    'po': node_index,
                    'n': CX_NODE_NAME,
                    'v': v
                })

            elif k in {PRODUCTS, REACTANTS, MEMBERS}:
                node_attributes_entry.append({
                    'po': node_index,
                    'n': k,
                    'v': json.dumps(v)
                })

            else:
                node_attributes_entry.append({
                    'po': node_index,
                    'n': k,
                    'v': v
                })

    edges_entry = []
    edge_attributes_entry = []

    for edge_index, (source, target, d) in enumerate(graph.edges_iter(data=True)):
        uid = node_mapping[source]
        vid = node_mapping[target]

        edges_entry.append({
            '@id': edge_index,
            's': uid,
            't': vid,
            'i': d[RELATION],
        })

        if EVIDENCE in d:
            edge_attributes_entry.append({
                'po': edge_index,
                'n': EVIDENCE,
                'v': d[EVIDENCE]
            })

            for k, v in d[CITATION].items():
                edge_attributes_entry.append({
                    'po': edge_index,
                    'n': '{}_{}'.format(CITATION, k),
                    'v': v
                })

        if ANNOTATIONS in d:
            for annotation, values in d[ANNOTATIONS].items():
                edge_attributes_entry.append({
                    'po': edge_index,
                    'n': annotation,
                    'v': sorted(values),
                    'd': 'list_of_string',
                })

        if SUBJECT in d:
            for k, v in flatten_dict(d[SUBJECT]).items():
                edge_attributes_entry.append({
                    'po': edge_index,
                    'n': '{}_{}'.format(SUBJECT, k),
                    'v': v
                })

        if OBJECT in d:
            for k, v in flatten_dict(d[OBJECT]).items():
                edge_attributes_entry.append({
                    'po': edge_index,
                    'n': '{}_{}'.format(OBJECT, k),
                    'v': v
                })

    context_legend = {}

    for key in graph.namespace_url:
        context_legend[key] = GRAPH_NAMESPACE_URL

    for key in graph.namespace_owl:
        context_legend[key] = GRAPH_NAMESPACE_OWL

    for key in graph.namespace_pattern:
        context_legend[key] = GRAPH_NAMESPACE_PATTERN

    for key in graph.annotation_url:
        context_legend[key] = GRAPH_ANNOTATION_URL

    for key in graph.annotation_owl:
        context_legend[key] = GRAPH_ANNOTATION_OWL

    for key in graph.annotation_pattern:
        context_legend[key] = GRAPH_ANNOTATION_PATTERN

    for key in graph.annotation_list:
        context_legend[key] = GRAPH_ANNOTATION_LIST

    context_legend_entry = []
    for keyword, resource_type in context_legend.items():
        context_legend_entry.append({
            'k': keyword,
            'v': resource_type
        })

    annotation_list_keys_lookup = {keyword: i for i, keyword in enumerate(sorted(graph.annotation_list))}
    annotation_lists_entry = []
    for keyword, values in graph.annotation_list.items():
        for values in values:
            annotation_lists_entry.append({
                'k': annotation_list_keys_lookup[keyword],
                'v': values
            })

    context_entry_dict = {}
    context_entry_dict.update(graph.namespace_url)
    context_entry_dict.update(graph.namespace_pattern)
    context_entry_dict.update(graph.namespace_owl)
    context_entry_dict.update(graph.annotation_url)
    context_entry_dict.update(graph.annotation_pattern)
    context_entry_dict.update(graph.annotation_owl)
    context_entry_dict.update(annotation_list_keys_lookup)

    context_entry_dict.update(graph.namespace_url)
    context_entry = [context_entry_dict]

    network_attributes_entry = [{
        "n": NDEX_SOURCE_FORMAT,
        "v": "PyBEL"
    }]
    for k, v in graph.document.items():
        network_attributes_entry.append({
            'n': k,
            'v': v
        })

    # Coalesce to cx
    # cx = create_aspect.number_verification()
    cx = [{'numberVerification': [{'longNumber': 281474976710655}]}]

    cx_pairs = [
        ('@context', context_entry),
        ('context_legend', context_legend_entry),
        ('annotation_lists', annotation_lists_entry),
        ('networkAttributes', network_attributes_entry),
        ('nodes', nodes_entry),
        ('nodeAttributes', node_attributes_entry),
        ('edges', edges_entry),
        ('edgeAttributes', edge_attributes_entry),
    ]

    cx_metadata = []

    for key, aspect in cx_pairs:
        aspect_dict = {
            "name": key,
            "elementCount": len(aspect),
            "lastUpdate": time.time(),
            "consistencyGroup": 1,
            "properties": [],
            "version": "1.0"
        }

        if key in {'citations', 'supports', 'nodes', 'edges'}:
            aspect_dict['idCounter'] = len(aspect)

        cx_metadata.append(aspect_dict)

    cx.append({
        'metaData': cx_metadata
    })

    for key, aspect in cx_pairs:
        cx.append({
            key: aspect
        })

    cx.append({"status": [{"error": "", "success": True}]})

    return cx


def to_cx_file(graph, file, indent=2, **kwargs):
    """Writes this graph to a JSON file in CX format

    :param BELGraph graph: A BEL graph
    :param file file: A writable file or file-like
    :param Optional[int] indent: How many spaces to use to pretty print. Change to None for no pretty printing

    Example:

    >>> from pybel import from_url, to_cx_file
    >>> from pybel.constants import SMALL_CORPUS_URL
    >>> graph = from_url(SMALL_CORPUS_URL)
    >>> with open('graph.cx', 'w') as f:
    >>> ... to_cx_file(graph, f)
    """
    graph_cx_json_dict = to_cx(graph)
    json.dump(graph_cx_json_dict, file, ensure_ascii=False, indent=indent, **kwargs)


def to_cx_jsons(graph, **kwargs):
    """Dumps a BEL graph as CX JSON to a string
    
    :param BELGraph graph: A BEL Graph
    :return: CX JSON string
    :rtype: str
    """
    graph_cx_json_str = to_cx(graph)
    return json.dumps(graph_cx_json_str, **kwargs)


def _iterate_list_of_dicts(lod):
    """
    :type lod: list[dict[A,B]]
    :rtype: iter[tuple[A,B]]
    """
    for l in lod:
        for k, v in l.items():
            yield k, v


def from_cx(cx):
    """Rebuilds a BELGraph from CX JSON output from PyBEL

    :param list[dict] cx: The CX JSON for this graph
    :rtype: BELGraph
    """
    graph = BELGraph()

    context_legend_aspect = []
    annotation_lists_aspect = []
    context_entry = {}
    network_attributes_aspect = []
    nodes_aspect = []
    node_attributes_aspect = []
    edge_annotations_aspect = []
    edges_aspect = []
    meta_entries = defaultdict(list)

    for key, value in _iterate_list_of_dicts(cx):
        if key == 'context_legend':
            context_legend_aspect.extend(value)

        elif key == 'annotation_lists':
            annotation_lists_aspect.extend(value)

        elif key == '@context':
            context_entry.update(value[0])

        elif key == 'networkAttributes':
            network_attributes_aspect.extend(value)

        elif key == 'nodes':
            nodes_aspect.extend(value)

        elif key == 'nodeAttributes':
            node_attributes_aspect.extend(value)

        elif key == 'edges':
            log.warning('got edge: %s', value)  # FIXME REMOVE
            edges_aspect.extend(value)

        elif key == 'edgeAttributes':
            edge_annotations_aspect.extend(value)

        else:
            meta_entries[key].extend(value)

    context_legend = _cx_to_dict(context_legend_aspect)

    annotation_lists = defaultdict(set)
    for data in annotation_lists_aspect:
        annotation_lists[data['k']].add(data['v'])

    for keyword, entry in context_entry.items():
        if context_legend[keyword] == GRAPH_NAMESPACE_URL:
            graph.namespace_url[keyword] = entry
        elif context_legend[keyword] == GRAPH_NAMESPACE_OWL:
            graph.namespace_owl[keyword] = entry
        elif context_legend[keyword] == GRAPH_NAMESPACE_PATTERN:
            graph.namespace_pattern[keyword] = entry
        elif context_legend[keyword] == GRAPH_ANNOTATION_URL:
            graph.annotation_url[keyword] = entry
        elif context_legend[keyword] == GRAPH_ANNOTATION_OWL:
            graph.annotation_owl[keyword] = entry
        elif context_legend[keyword] == GRAPH_ANNOTATION_PATTERN:
            graph.annotation_pattern[keyword] = entry
        elif context_legend[keyword] == GRAPH_ANNOTATION_LIST:
            graph.annotation_list[keyword] = annotation_lists[entry]

    for data in network_attributes_aspect:
        if data['n'] == NDEX_SOURCE_FORMAT:
            continue
        graph.graph[GRAPH_METADATA][data['n']] = data['v']

    node_name = {}
    for data in nodes_aspect:
        node_name[data['@id']] = data['n']

    node_data = defaultdict(dict)
    for data in node_attributes_aspect:
        node_data[data['po']][data['n']] = data['v']

    node_data_pp = defaultdict(dict)
    node_data_fusion = defaultdict(dict)
    node_data_variants = defaultdict(lambda: defaultdict(dict))

    for nid, data in node_data.items():
        for key, value in data.items():
            if key.startswith(FUSION):
                node_data_fusion[nid][key] = value
            elif key.startswith(VARIANTS):
                _, i, vls = key.split('_', 2)
                node_data_variants[nid][i][vls] = value
            elif key in {PRODUCTS, REACTANTS, MEMBERS}:
                node_data_pp[nid][key] = json.loads(value)
            else:
                node_data_pp[nid][key] = value

    for nid, data in node_data_fusion.items():
        node_data_pp[nid][FUSION] = expand_dict(data)

    for nid, data in node_data_variants.items():
        node_data_pp[nid][VARIANTS] = [expand_dict(data[i]) for i in sorted(data)]

    for nid, data in node_data_pp.items():
        if CX_NODE_NAME in data:
            data[NAME] = data.pop(CX_NODE_NAME)
        graph.add_node(nid, attr_dict=data)

    edge_relation = {}
    edge_source = {}
    edge_target = {}
    for data in edges_aspect:
        eid = data['@id']
        edge_relation[eid] = data['i']
        edge_source[eid] = data['s']
        edge_target[eid] = data['t']

    edge_data = defaultdict(dict)
    for data in edge_annotations_aspect:
        edge_data[data['po']][data['n']] = data['v']

    edge_citation = defaultdict(dict)
    edge_subject = defaultdict(dict)
    edge_object = defaultdict(dict)
    edge_annotations = defaultdict(lambda: defaultdict(dict))

    edge_data_pp = defaultdict(dict)

    for eid, data in edge_data.items():
        for key, value in data.items():
            if key.startswith(CITATION):
                _, vl = key.split('_', 1)
                edge_citation[eid][vl] = value
            elif key.startswith(SUBJECT):
                _, vl = key.split('_', 1)
                edge_subject[eid][vl] = value
            elif key.startswith(OBJECT):
                _, vl = key.split('_', 1)
                edge_object[eid][vl] = value
            elif key == EVIDENCE:
                edge_data_pp[eid][EVIDENCE] = value
            else:
                edge_annotations[eid][key] = value

    for eid, data in edge_citation.items():
        edge_data_pp[eid][CITATION] = data

    for eid, data in edge_subject.items():
        edge_data_pp[eid][SUBJECT] = expand_dict(data)

    for eid, data in edge_object.items():
        edge_data_pp[eid][OBJECT] = expand_dict(data)

    for eid in edge_relation:
        if eid in edge_annotations: # FIXME stick this in edge_data.items() iteration
            edge_data_pp[eid][ANNOTATIONS] = {
                key: {v: True for v in values}
                for key, values in edge_annotations[eid].items()
            }

        if eid in edge_citation:
            graph.add_qualified_edge(
                edge_source[eid],
                edge_target[eid],
                relation=edge_relation[eid],
                citation=edge_data_pp[eid][CITATION],
                evidence=edge_data_pp[eid][EVIDENCE],
                subject_modifier=edge_data_pp[eid].get(SUBJECT),
                object_modifier=edge_data_pp[eid].get(OBJECT),
                annotations=edge_data_pp[eid].get(ANNOTATIONS)
            )
        elif edge_relation[eid] in unqualified_edges:
            graph.add_unqualified_edge(
                edge_source[eid],
                edge_target[eid],
                edge_relation[eid]
            )
        else:
            raise ValueError('problem adding edge: {}'.format(eid))

    return graph


def from_cx_jsons(graph_cx_json_str):
    """Reconstitutes a BEL graph from a CX JSON string
    
    :param str graph_cx_json_str: CX JSON string 
    :return: A BEL graph representing the CX graph contained in the string
    :rtype: BELGraph
    """
    graph_cx_json_dict = json.loads(graph_cx_json_str)
    return from_cx(graph_cx_json_dict)


def from_cx_file(file):
    """Reads a file containing CX JSON and converts to a BEL graph

    :param file file: A readable file or file-like containing the CX JSON for this graph
    :return: A BEL Graph representing the CX graph contained in the file
    :rtype: BELGraph
    """
    graph_cx_json_dict = json.load(file)
    return from_cx(graph_cx_json_dict)
