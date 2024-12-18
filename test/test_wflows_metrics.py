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
from qgis.core import QgsVectorLayer, QgsRasterLayer
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

