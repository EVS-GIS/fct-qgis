# -*- coding: utf-8 -*-

"""
Fluvial Corridor Toolbox for QGIS unit tests
Workflows - Statistics

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


class TestHubertTest(QgisTestCase):

    @classmethod
    def setUpClass(self):
        self.outdir = tempfile.mkdtemp()
        self.table = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'dgos.gml'))
        

    def test_segmentation_inputs(self):

        self.assertTrue(self.table.isValid(), f'Failed to load {self.table.source()}')


    def test_huberttest_dgowidth(self):

        proc_alg = processing.run('fcw:huberttest', {
            'INPUT': self.table,
            'METRIC_FIELD':'DGO_WIDTH',
            'ORDERING_FIELD':'DISTANCE',
            'DISSOLVE':False,
            'OUTPUT': os.path.join(self.outdir, 'ago.gml'),
        })

        output = QgsVectorLayer(proc_alg['OUTPUT'])
        self.assertTrue(output.isValid(), 'Output is not a valid layer')

        expected = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'ago.gml'))
        self.assertTrue(expected.isValid(), f'Failed to load {expected.source()}')
    
        self.assertLayersEqual(expected, output)


    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.outdir, True)
