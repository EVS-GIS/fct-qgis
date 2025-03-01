# -*- coding: utf-8 -*-

"""
Fluvial Corridor Toolbox for QGIS unit tests
Algorithms - Hydrography

***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

import os
import tempfile
import shutil

from qgis.testing import QgisTestCase, start_app
from qgis.core import QgsVectorLayer
from processing.core.Processing import Processing
import processing

from fct.FluvialCorridorToolbox import FluvialCorridorToolboxProvider, FluvialCorridorWorkflowsProvider

qgis_app = start_app(cleanup=False)

Processing.initialize()
fct = FluvialCorridorToolboxProvider()
fcw = FluvialCorridorWorkflowsProvider()
qgis_app.processingRegistry().addProvider(fct)
qgis_app.processingRegistry().addProvider(fcw)


class TestIdentifyNetworkNodes(QgisTestCase):

    @classmethod
    def setUpClass(self):
        self.outdir = tempfile.mkdtemp()
        self.network = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'network.gpkg'))
        

    def test_network_input(self):

        self.assertTrue(self.network.isValid(), f'Failed to load {self.network.source()}')


    def test_identifynetworknodes(self):

        proc_alg = processing.run('fct:identifynetworknodes', {
            'INPUT': self.network,
            'NODES': os.path.join(self.outdir, 'nodes.gml'),
            'OUTPUT': os.path.join(self.outdir, 'identifynetworknodes.gml')
        })

        nodes_output = QgsVectorLayer(proc_alg['NODES'])
        network_output = QgsVectorLayer(proc_alg['OUTPUT'])
        self.assertTrue(nodes_output.isValid(), 'Nodes output is not a valid layer')
        self.assertTrue(network_output.isValid(), 'Network output is not a valid layer')

        expected_network = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'identifynetworknodes.gml'))
        self.assertTrue(expected_network.isValid(), f'Failed to load {expected_network.source()}')

        expected_nodes = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'nodes.gml'))
        self.assertTrue(expected_nodes.isValid(), f'Failed to load {expected_nodes.source()}')
    
        self.assertLayersEqual(expected_network, network_output)
        self.assertLayersEqual(expected_nodes, nodes_output)
                       
    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.outdir, True)


class TestAggregateStreamSegments(QgisTestCase):

    @classmethod
    def setUpClass(self):
        self.outdir = tempfile.mkdtemp()
        self.network = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'network.gpkg'))
        
    def test_network_input(self):

        self.assertTrue(self.network.isValid(), f'Failed to load {self.network.source()}')

    def test_aggregatestreamsegments(self):

        proc_alg = processing.run('fct:aggregatestreamsegments', {
            'INPUT': self.network,
            'FROM_NODE_FIELD': '',
            'TO_NODE_FIELD': '',
            'COPY_FIELDS': ['GID'],
            'OUTPUT': os.path.join(self.outdir, 'aggregatedstreams.gml')
        })

        aggregated_output = QgsVectorLayer(proc_alg['OUTPUT'])
        self.assertTrue(aggregated_output.isValid(), 'Aggregated output is not a valid layer')

        expected_aggregated = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'aggregatedstreams.gml'))
        self.assertTrue(expected_aggregated.isValid(), f'Failed to load {expected_aggregated.source()}')

        self.assertLayersEqual(expected_aggregated, aggregated_output)
        
    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.outdir, True)


class TestAggregateUndirectedLines(QgisTestCase):

    @classmethod
    def setUpClass(self):
        self.outdir = tempfile.mkdtemp()
        self.network = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'identified_messy.gpkg'))
        
    def test_network_input(self):

        self.assertTrue(self.network.isValid(), f'Failed to load {self.network.source()}')

    def test_aggregateundirectedlines(self):

        proc_alg = processing.run("fct:aggregateundirectedlines", {
            'INPUT':self.network.source(),
            'FROM_NODE_FIELD':'NODEA',
            'TO_NODE_FIELD':'NODEB',
            'OUTPUT':os.path.join(self.outdir, 'aggregate_undirected.gpkg')
        })

        aggregated_output = QgsVectorLayer(proc_alg['OUTPUT'])
        self.assertTrue(aggregated_output.isValid(), 'Aggregated output is not a valid layer')

        expected_aggregated = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'aggregate_undirected.gpkg'))
        self.assertTrue(expected_aggregated.isValid(), f'Failed to load {expected_aggregated.source()}')

        self.assertLayersEqual(expected_aggregated, aggregated_output)


    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.outdir, True)


class TestHackOrder(QgisTestCase):

    @classmethod
    def setUpClass(self):
        self.outdir = tempfile.mkdtemp()
        self.network = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'network.gpkg'))
        

    def test_input(self):

        self.assertTrue(self.network.isValid(), f'Failed to load {self.network.source()}')


    def test_hackorder(self):

        proc_alg = processing.run("fct:hackorder", {
            'INPUT':self.network,
            'FROM_NODE_FIELD':'',
            'TO_NODE_FIELD':'',
            'MEASURE_FIELD':'',
            'IS_DOWNSTREAM_MEAS':True,
            'OUTPUT': os.path.join(self.outdir, 'hack_order.gpkg')
        })

        output = QgsVectorLayer(proc_alg['OUTPUT'])
        self.assertTrue(output.isValid(), 'Output transects is not a valid layer')

        expected_output = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'hack_order.gpkg'))
        self.assertTrue(expected_output.isValid(), f'Failed to load {expected_output.source()}')
    
        self.assertLayersEqual(expected_output, output)


    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.outdir, True)


class TestStrahlerOrder(QgisTestCase):

    @classmethod
    def setUpClass(self):
        self.outdir = tempfile.mkdtemp()
        self.network = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'network.gpkg'))
        

    def test_input(self):

        self.assertTrue(self.network.isValid(), f'Failed to load {self.network.source()}')


    def test_strahlerorder(self):

        proc_alg = processing.run("fct:strahlerorder", {
            'INPUT':self.network,
            'FROM_NODE_FIELD':'',
            'TO_NODE_FIELD':'',
            'AXIS_FIELD':'',
            'OUTPUT': os.path.join(self.outdir, 'strahler_order.gpkg')
        })

        output = QgsVectorLayer(proc_alg['OUTPUT'])
        self.assertTrue(output.isValid(), 'Output transects is not a valid layer')

        expected_output = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'strahler_order.gpkg'))
        self.assertTrue(expected_output.isValid(), f'Failed to load {expected_output.source()}')
    
        self.assertLayersEqual(expected_output, output)


    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.outdir, True)


class TestNetworkNodes(QgisTestCase):

    @classmethod
    def setUpClass(self):
        self.outdir = tempfile.mkdtemp()
        self.network = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'network.gpkg'))
        

    def test_input(self):

        self.assertTrue(self.network.isValid(), f'Failed to load {self.network.source()}')


    def test_strahlerorder(self):

        proc_alg = processing.run("fct:networknodes", {
            'INPUT':self.network,
            'FROM_NODE_FIELD':'',
            'TO_NODE_FIELD':'',
            'MEAS_FIELD':'',
            'SUBSET':0,
            'OUTPUT': os.path.join(self.outdir, 'network_nodes.gpkg')
        })

        output = QgsVectorLayer(proc_alg['OUTPUT'])
        self.assertTrue(output.isValid(), 'Output transects is not a valid layer')

        expected_output = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'network_nodes.gpkg'))
        self.assertTrue(expected_output.isValid(), f'Failed to load {expected_output.source()}')
    
        self.assertLayersEqual(expected_output, output)


    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.outdir, True)

