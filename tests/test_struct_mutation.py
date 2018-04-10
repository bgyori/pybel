# -*- coding: utf-8 -*-

import unittest

from pybel import BELGraph
from pybel.constants import ANNOTATIONS, INCREASES
from pybel.dsl import gene, protein, rna
from pybel.examples.statin_example import (
    avorastatin, ec_11134, ec_11188, fluvastatin, hmgcr, hmgcr_inhibitor, mevinolinic_acid, statin, statin_graph,
    synthetic_statin,
)
from pybel.struct.mutation import infer_central_dogma, infer_child_relations, prune_central_dogma, strip_annotations
from pybel.struct.mutation.transfer import iter_children

trem2_gene = gene(namespace='HGNC', name='TREM2')
trem2_rna = rna(namespace='HGNC', name='TREM2')
trem2_protein = protein(namespace='HGNC', name='TREM2')


class TestMutations(unittest.TestCase):
    def test_strip_annotations(self):
        u = protein(namespace='HGNC', name='U')
        v = protein(namespace='HGNC', name='V')

        annotations = {
            'A': {'B': True}
        }

        graph = BELGraph()
        key = graph.add_qualified_edge(
            u,
            v,
            relation=INCREASES,
            citation='123456',
            evidence='Fake',
            annotations=annotations,
        )

        self.assertIn(ANNOTATIONS, graph[u][v][key])

        self.assertEqual(annotations, graph.get_edge_annotations(u, v, key))
        strip_annotations(graph)
        self.assertNotIn(ANNOTATIONS, graph[u][v][key])


class TestTransfer(unittest.TestCase):
    def test_get_children(self):
        children = list(iter_children(statin_graph, hmgcr_inhibitor))

        self.assertNotEqual(0, len(children), msg='no children found')
        self.assertIn(mevinolinic_acid, children, msg='direct child not found')

    def test_infer(self):
        graph = statin_graph.copy()
        self.assertEqual(9, graph.number_of_nodes())
        self.assertEqual(8, graph.number_of_edges())

        self.assertNotIn(ec_11134, graph[fluvastatin])
        self.assertNotIn(ec_11188, graph[fluvastatin])
        self.assertNotIn(ec_11134, graph[avorastatin])
        self.assertNotIn(ec_11188, graph[avorastatin])
        self.assertNotIn(ec_11134, graph[synthetic_statin])
        self.assertNotIn(ec_11188, graph[synthetic_statin])
        self.assertNotIn(ec_11134, graph[statin])
        self.assertNotIn(ec_11188, graph[statin])
        self.assertNotIn(ec_11134, graph[mevinolinic_acid])
        self.assertNotIn(ec_11188, graph[mevinolinic_acid])
        self.assertIn(ec_11134, graph[hmgcr_inhibitor])
        self.assertIn(ec_11188, graph[hmgcr_inhibitor])

        infer_child_relations(graph, hmgcr_inhibitor)

        self.assertIn(ec_11134, graph[fluvastatin])
        self.assertIn(ec_11188, graph[fluvastatin])
        self.assertIn(ec_11134, graph[avorastatin])
        self.assertIn(ec_11188, graph[avorastatin])
        self.assertIn(ec_11134, graph[synthetic_statin])
        self.assertIn(ec_11188, graph[synthetic_statin])
        self.assertIn(ec_11134, graph[statin])
        self.assertIn(ec_11188, graph[statin])
        self.assertIn(ec_11134, graph[mevinolinic_acid])
        self.assertIn(ec_11188, graph[mevinolinic_acid])
        self.assertIn(ec_11134, graph[hmgcr_inhibitor])
        self.assertIn(ec_11188, graph[hmgcr_inhibitor])

        self.assertEqual(9, graph.number_of_nodes())
        self.assertEqual(18, graph.number_of_edges())

        infer_child_relations(graph, ec_11134)

        self.assertIn(hmgcr, graph[fluvastatin])
        self.assertIn(hmgcr, graph[avorastatin])
        self.assertIn(hmgcr, graph[synthetic_statin])
        self.assertIn(hmgcr, graph[statin])
        self.assertIn(hmgcr, graph[mevinolinic_acid])
        self.assertIn(hmgcr, graph[hmgcr_inhibitor])

        self.assertEqual(9, graph.number_of_nodes())
        self.assertEqual(24, graph.number_of_edges())

        self.assertEqual(9, statin_graph.number_of_nodes(), msg='original graph nodes should not be modified')
        self.assertEqual(8, statin_graph.number_of_edges(), msg='original graph edges should not be modified')

    def test_does_not_redo(self):
        """Tests that :func:`propagate_node_relations` does not add the same edges twice"""
        graph = statin_graph.copy()
        self.assertEqual(9, graph.number_of_nodes())
        self.assertEqual(8, graph.number_of_edges())

        infer_child_relations(graph, hmgcr_inhibitor)
        self.assertEqual(9, graph.number_of_nodes())
        self.assertEqual(18, graph.number_of_edges())

        infer_child_relations(graph, hmgcr_inhibitor)
        self.assertEqual(9, graph.number_of_nodes())
        self.assertEqual(18, graph.number_of_edges(), msg='edges should not be added again')


class TestProcessing(unittest.TestCase):
    def test_infer_on_sialic_acid_example(self):
        graph = BELGraph()
        graph.add_entity(trem2_protein)

        self.assertIn(trem2_protein, graph)
        self.assertNotIn(trem2_gene, graph)
        self.assertNotIn(trem2_rna, graph)

        infer_central_dogma(graph)

        self.assertIn(trem2_gene, graph)
        self.assertIn(trem2_rna, graph)

        prune_central_dogma(graph)

        self.assertNotIn(trem2_gene, graph)
        self.assertNotIn(trem2_rna, graph)


if __name__ == '__main__':
    unittest.main()
