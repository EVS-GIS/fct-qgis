# -*- coding: utf-8 -*-

"""
Fluvial Corridor Toolbox for QGIS unit tests
Workflows - Metrics

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
from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsProperty
from processing.core.Processing import Processing
import processing

from fct.FluvialCorridorToolbox import FluvialCorridorToolboxProvider, FluvialCorridorWorkflowsProvider

qgis_app = start_app(cleanup=False)

Processing.initialize()
fct = FluvialCorridorToolboxProvider()
fcw = FluvialCorridorWorkflowsProvider()
qgis_app.processingRegistry().addProvider(fct)
qgis_app.processingRegistry().addProvider(fcw)


class TestElevationAndSlope(QgisTestCase):

    @classmethod
    def setUpClass(self):
        self.outdir = tempfile.mkdtemp()
        self.stream = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'stream_dgos.gml'))
        self.network = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'oriented_network.gml'))
        self.dem = QgsRasterLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'dem.tif'))
        

    def test_elevationandslope_inputs(self):

        self.assertTrue(self.stream.isValid(), f'Failed to load {self.stream.source()}')
        self.assertTrue(self.network.isValid(), f'Failed to load {self.network.source()}')
        self.assertTrue(self.dem.isValid(), f'Failed to load {self.dem.source()}')


    def test_elevationandslope_stream(self):

        proc_alg = processing.run("fcw:elevationandslope", {
            'NETWORK': self.stream,
            'DEM': self.dem,
            'OUTPUT_LINES': os.path.join(self.outdir, 'elevationandslope_stream.gpkg'),
        })

        output = QgsVectorLayer(proc_alg['OUTPUT_LINES'])
        self.assertTrue(output.isValid(), 'Output is not a valid layer')

        expected = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'elevationandslope_stream.gpkg'))
        self.assertTrue(expected.isValid(), f'Failed to load {expected.source()}')
    
        self.assertLayersEqual(expected, output)


    def test_elevationandslope_network(self):

        proc_alg = processing.run("fcw:elevationandslope", {
            'NETWORK': self.network,
            'DEM': self.dem,
            'OUTPUT_LINES': os.path.join(self.outdir, 'elevationandslope_network.gpkg'),
        })

        output = QgsVectorLayer(proc_alg['OUTPUT_LINES'])
        self.assertTrue(output.isValid(), 'Output is not a valid layer')

        expected = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'elevationandslope_network.gpkg'))
        self.assertTrue(expected.isValid(), f'Failed to load {expected.source()}')
    
        self.assertLayersEqual(expected, output)


    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.outdir, True)


class TestPolygonWidth(QgisTestCase):

    @classmethod
    def setUpClass(self):
        self.outdir = tempfile.mkdtemp()
        self.ac = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'disaggregated_ac.gml'))
        self.centerline = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'ac_centerline.gml'))
        

    def test_polygonwidth_inputs(self):

        self.assertTrue(self.ac.isValid(), f'Failed to load {self.ac.source()}')
        self.assertTrue(self.centerline.isValid(), f'Failed to load {self.centerline.source()}')


    def test_polygonwidth(self):

        proc_alg = processing.run("fcw:polygonwidth", {
            'INPUT_POLYGONS':self.ac,
            'INPUT_MEDIAL_AXIS':self.centerline,
            'INPUT_POLYGONS_FID':'DGO_FID',
            'INPUT_MEDIAL_AXIS_FID':'DGO_FID',
            'SAMPLING_INTERVAL':5,
            'MAX_WIDTH':QgsProperty.fromExpression('"DGO_WIDTH"'),
            'OUTPUT_TABLE':os.path.join(self.outdir, 'transects_stats.csv'),
            'OUTPUT_TRANSECTS':os.path.join(self.outdir, 'transects.gpkg')
        })

        output_transects = QgsVectorLayer(proc_alg['OUTPUT_TRANSECTS'])
        self.assertTrue(output_transects.isValid(), 'Output is not a valid layer')

        expected_transects = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'transects.gpkg'))
        self.assertTrue(expected_transects.isValid(), f'Failed to load {expected_transects.source()}')

        self.assertLayersEqual(expected_transects, output_transects, compare={'unordered': True, 'fields': {'fid': 'skip'}})

        output_table = QgsVectorLayer(proc_alg['OUTPUT_TABLE'])
        self.assertTrue(output_table.isValid(), 'Output is not a valid layer')

        expected_table = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'transects_stats.csv'))
        self.assertTrue(expected_table.isValid(), f'Failed to load {expected_table.source()}')
    
        self.assertLayersEqual(expected_table, output_table, compare={'fields': {'__all__': {'cast': 'float', 'precision': 6}}})


    @classmethod
    def tearDownClass(self):
        #shutil.rmtree(self.outdir, True)
        pass