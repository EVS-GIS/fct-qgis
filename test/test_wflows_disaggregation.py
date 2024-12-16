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


class TestSegmentationWorkflow(QgisTestCase):

    @classmethod
    def setUpClass(self):
        self.outdir = tempfile.mkdtemp()
        self.centerline = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'centerline.gml'))
        self.polygon = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'vb_nearest.gml'))
        

    def test_segmentation_inputs(self):

        self.assertTrue(self.centerline.isValid(), f'Failed to load {self.centerline.source()}')
        self.assertTrue(self.polygon.isValid(), f'Failed to load {self.polygon.source()}')


    def test_segmentation_polyline(self):

        proc_alg = processing.run('fcw:segmentation', {
            'INPUT': self.centerline,
            'OUTPUT': os.path.join(self.outdir, 'segmentized_centerline.gml'),
        })

        output = QgsVectorLayer(proc_alg['OUTPUT'])
        self.assertTrue(output.isValid(), 'Output is not a valid layer')

        expected = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'segmentized_centerline.gml'))
        self.assertTrue(expected.isValid(), f'Failed to load {expected.source()}')
    
        self.assertLayersEqual(expected, output)


    def test_segmentation_polygon(self):

        proc_alg = processing.run('fcw:segmentation', {
            'INPUT': self.polygon,
            'CENTERLINE': self.centerline,
            'STEP': 200,
            'OUTPUT': os.path.join(self.outdir, 'dgos.gml'),
        })

        output = QgsVectorLayer(proc_alg['OUTPUT'])
        self.assertTrue(output.isValid(), 'Output is not a valid layer')

        expected = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'dgos.gml'))
        self.assertTrue(expected.isValid(), f'Failed to load {expected.source()}')
    
        self.assertLayersEqual(expected, output)

                         
    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.outdir, True)