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


class TestInflectionDisaggregationWorkflow(QgisTestCase):

    @classmethod
    def setUpClass(self):
        self.outdir = tempfile.mkdtemp()
        self.centerline = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'centerline.gml'))
        

    def test_inflection_inputs(self):

        self.assertTrue(self.centerline.isValid(), f'Failed to load {self.centerline.source()}')


    def test_inflection_disaggregation(self):

        proc_alg = processing.run('fcw:inflectiondisaggregation', {
            'INPUT': self.centerline,
            'SIMPLIFY':10,
            'MAX_DISTANCE':2000,
            'MIN_AMPLITUDE':40,
            'MAX_ANGLE':50,
            'OUTPUT_POINTS':os.path.join(self.outdir, 'inflection_points.gml'),
            'OUTPUT_LINES':os.path.join(self.outdir, 'inflection_lines.gml'),
            'OUTPUT_DISAGGREGATED':os.path.join(self.outdir, 'inflection_network.gml')
        })

        output_points = QgsVectorLayer(proc_alg['OUTPUT_POINTS'])
        self.assertTrue(output_points.isValid(), 'Output inflection points is not a valid layer')

        output_lines = QgsVectorLayer(proc_alg['OUTPUT_LINES'])
        self.assertTrue(output_lines.isValid(), 'Output inflection lines is not a valid layer')

        output_disaggregated = QgsVectorLayer(proc_alg['OUTPUT_DISAGGREGATED'])
        self.assertTrue(output_disaggregated.isValid(), 'Output disaggregated network is not a valid layer')

        expected_points = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'inflection_points.gml'))
        self.assertTrue(expected_points.isValid(), f'Failed to load {expected_points.source()}')
        self.assertLayersEqual(expected_points, output_points)

        expected_lines = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'inflection_lines.gml'))
        self.assertTrue(expected_lines.isValid(), f'Failed to load {expected_lines.source()}')
        self.assertLayersEqual(expected_lines, output_lines)

        expected_disaggregated = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'inflection_network.gml'))
        self.assertTrue(expected_disaggregated.isValid(), f'Failed to load {expected_disaggregated.source()}')
        self.assertLayersEqual(expected_disaggregated, output_disaggregated)

                         
    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.outdir, True)


class TestSequencing(QgisTestCase):

    @classmethod
    def setUpClass(self):
        self.outdir = tempfile.mkdtemp()
        self.network = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'messy_network.gml'))
        self.dem = QgsRasterLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'dem.tif'))
        
    def test_sequencing_inputs(self):

        self.assertTrue(self.network.isValid(), f'Failed to load {self.network.source()}')
        self.assertTrue(self.dem.isValid(), f'Failed to load {self.dem.source()}')


    def test_sequencing(self):

        proc_alg = processing.run('fcw:sequencing', {
            'INPUT': self.network,
            'DEM': self.dem,
            'OUTPUT': os.path.join(self.outdir, 'oriented_network.gml'),
        })

        output = QgsVectorLayer(proc_alg['OUTPUT'])
        self.assertTrue(output.isValid(), 'Output is not a valid layer')

        expected = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'oriented_network.gml'))
        self.assertTrue(expected.isValid(), f'Failed to load {expected.source()}')
    
        self.assertLayersEqual(expected, output)


    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.outdir, True)
