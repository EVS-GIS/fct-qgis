# -*- coding: utf-8 -*-

"""
Fluvial Corridor Toolbox for QGIS unit tests
Network - Drainage

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
import numpy as np

from qgis.testing import QgisTestCase, start_app
from qgis.core import QgsRasterLayer
from processing.core.Processing import Processing
import processing

from fct.FluvialCorridorToolbox import FluvialCorridorToolboxProvider, FluvialCorridorWorkflowsProvider, FluvialCorridorNetworkProvider

qgis_app = start_app(cleanup=False)

Processing.initialize()
fct = FluvialCorridorToolboxProvider()
fcw = FluvialCorridorWorkflowsProvider()
fcn = FluvialCorridorNetworkProvider()
qgis_app.processingRegistry().addProvider(fct)
qgis_app.processingRegistry().addProvider(fcw)
qgis_app.processingRegistry().addProvider(fcn)


class TestPrepareDEM(QgisTestCase):

    @classmethod
    def setUpClass(self):
        self.outdir = tempfile.mkdtemp()
        self.dem = QgsRasterLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'dem.tif'))
        
    def test_preparedem_inputs(self):

        self.assertTrue(self.dem.isValid(), f'Failed to load {self.dem.source()}')

    def test_preparedem(self):

        proc_alg = processing.run('fcn:preparedem', {
            'DEM': self.dem,
            'WINDOW': 5,
            'OUTPUT': os.path.join(self.outdir, 'preparedem.tif'),
        })

        output = QgsRasterLayer(proc_alg['OUTPUT'])
        self.assertTrue(output.isValid(), 'Output is not a valid layer')

        expected = QgsRasterLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'preparedem.tif'))
        self.assertTrue(expected.isValid(), f'Failed to load {expected.source()}')
    
        output_block = output.dataProvider().block(1, output.extent(), output.width(), output.height())
        expected_block = expected.dataProvider().block(1, expected.extent(), expected.width(), expected.height())

        output_data = np.frombuffer(output_block.data(), dtype=np.uint8)
        expected_data = np.frombuffer(expected_block.data(), dtype=np.uint8)

        self.assertTrue((output_data == expected_data).all(), 'Output does not match expected')


    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.outdir, True)
