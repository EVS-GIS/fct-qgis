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


class TestDisaggregatePolygon(QgisTestCase):

    @classmethod
    def setUpClass(self):
        self.outdir = tempfile.mkdtemp()
        self.centerline = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'centerline.gml'))
        self.oriented_centerline = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'testdata', 'input', 'oriented_centerline.gml'))
        self.polygon = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'vb_nearest.gml'))
        
    def test_centerline_input(self):

        self.assertTrue(self.centerline.isValid(), f'Failed to load {self.centerline.source()}')
        self.assertTrue(self.oriented_centerline.isValid(), f'Failed to load {self.oriented_centerline.source()}')
        self.assertTrue(self.polygon.isValid(), f'Failed to load {self.polygon.source()}')
    
    def test_disaggregate100_vb_centerline(self):

        proc_alg = processing.run('fct:disaggregatepolygon', {
            'CENTERLINE': self.centerline,
            'POLYGON': self.polygon,
            'STEP': 100.0,
            'DISAGGREGATED': os.path.join(self.outdir, 'disaggregatepolygon.gml')
        })

        output = QgsVectorLayer(proc_alg['DISAGGREGATED'])
        self.assertTrue(output.isValid(), 'Output is not a valid layer')

        expected = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'disaggregatepolygon.gml'))
        self.assertTrue(expected.isValid(), f'Failed to load {expected.source()}')

        self.assertLayersEqual(expected, output)


    def test_disaggregate500_vb_oriented_centerline(self):

        proc_alg = processing.run('fct:disaggregatepolygon', {
            'CENTERLINE': self.oriented_centerline,
            'POLYGON': self.polygon,
            'STEP': 500.0,
            'DISAGGREGATED': os.path.join(self.outdir, 'disaggregatepolygon_500_oriented.gml')
        })

        output = QgsVectorLayer(proc_alg['DISAGGREGATED'])
        self.assertTrue(output.isValid(), 'Output is not a valid layer')

        expected = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'disaggregatepolygon_500_oriented.gml'))
        self.assertTrue(expected.isValid(), f'Failed to load {expected.source()}')

        self.assertLayersEqual(expected, output)


    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.outdir, True)