# -*- coding: utf-8 -*-

"""
Fluvial Corridor Toolbox for QGIS unit tests
Algorithms - Spatial Reference

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


class TestMeasureNetworkFromOutlet(QgisTestCase):

    @classmethod
    def setUpClass(self):
        self.outdir = tempfile.mkdtemp()
        self.network = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'network.gpkg'))
        

    def test_input(self):

        self.assertTrue(self.network.isValid(), f'Failed to load {self.network.source()}')


    def test_measurenetworkfromoutlet(self):

        proc_alg = processing.run("fct:measurenetworkfromoutlet", {
            'INPUT':self.network,
            'FROM_NODE_FIELD':'',
            'TO_NODE_FIELD':'',
            'OUTPUT': os.path.join(self.outdir, 'measured_network.gpkg')
        })

        output = QgsVectorLayer(proc_alg['OUTPUT'])
        self.assertTrue(output.isValid(), 'Output transects is not a valid layer')

        expected_output = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'measured_network.gpkg'))
        self.assertTrue(expected_output.isValid(), f'Failed to load {expected_output.source()}')
    
        self.assertLayersEqual(expected_output, output)
        
                         
    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.outdir, True)
