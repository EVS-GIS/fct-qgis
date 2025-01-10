# -*- coding: utf-8 -*-

"""
Fluvial Corridor Toolbox for QGIS unit tests
Algorithms - Tools for Vectors

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
from qgis.core import QgsVectorLayer, QgsProperty
from processing.core.Processing import Processing
import processing

from fct.FluvialCorridorToolbox import FluvialCorridorToolboxProvider, FluvialCorridorWorkflowsProvider

qgis_app = start_app(cleanup=False)

Processing.initialize()
fct = FluvialCorridorToolboxProvider()
fcw = FluvialCorridorWorkflowsProvider()
qgis_app.processingRegistry().addProvider(fct)
qgis_app.processingRegistry().addProvider(fcw)


class TestVariableLengthTransects(QgisTestCase):

    @classmethod
    def setUpClass(self):
        self.outdir = tempfile.mkdtemp()
        self.ac = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'ac_centerline.gml'))
        

    def test_network_input(self):

        self.assertTrue(self.ac.isValid(), f'Failed to load {self.ac.source()}')


    def test_identifynetworknodes(self):

        proc_alg = processing.run("fct:variablelengthtransects", {
            'INPUT':self.ac,
            'LENGTH':QgsProperty.fromExpression('"DGO_WIDTH"'),
            'INTERVAL':20,
            'OUTPUT': os.path.join(self.outdir, 'variablelengthtransects.gpkg')
        })

        output = QgsVectorLayer(proc_alg['OUTPUT'])
        self.assertTrue(output.isValid(), 'Output transects is not a valid layer')

        expected_output = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'variablelengthtransects.gpkg'))
        self.assertTrue(expected_output.isValid(), f'Failed to load {expected_output.source()}')
    
        self.assertLayersEqual(expected_output, output)
        
                         
    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.outdir, True)
