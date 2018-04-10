# -*- coding: utf-8 -*-

from pybel.manager.models import Network
from pybel.struct import union


class MockNetwork(object):
    """Mocks a :class:`pybel.manager.models.Network`"""

    def __init__(self, id):
        self.id = id


class MockQueryManager(object):
    def __init__(self, graphs=None):
        """Builds a mock manager appropriate for testing the pipeline and query builders

        :param Optional[list[pybel.BELGraph]] graphs: A list of BEL graphs to index
        """
        self.graphs = []

        #: A lookup for nodes from the node hash (string) to the node tuple
        self.sha512_to_node = {}

        #: A lookup from network identifier to graph
        self.id_graph = {}

        if graphs is not None:
            for graph in graphs:
                self.insert_graph(graph)

    def count_networks(self):
        """Counts the networks in the database

        :rtype: int
        """
        return len(self.graphs)

    def insert_graph(self, graph):
        """Inserts a graph

        :param pybel.BELGraph graph:
        :rtype: Network
        """
        network_id = len(self.graphs)
        self.graphs.append(graph)
        self.id_graph[network_id] = graph

        self.sha512_to_node.update(graph.sha512_to_node)

        return MockNetwork(id=network_id)

    def get_node_by_hash(self, node_hash):
        """Gets a node tuple by its hash

        :param str node_hash: A node hash from :meth:`BELGraph.hash_node`
        :rtype: tuple
        """
        return self.sha512_to_node[node_hash]

    def get_graph_by_ids(self, network_ids):
        """Gets a graph from the union of multiple

        :param iter[int] network_ids: The identifiers of networks in the database
        :rtype: pybel.BELGraph
        """
        network_ids = list(network_ids)

        if len(network_ids) == 1:
            return self.id_graph[network_ids[0]]

        graphs = [
            self.id_graph[graph_id]
            for graph_id in network_ids
        ]

        return union(graphs)
