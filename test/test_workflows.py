import os
import tempfile
import shutil

from qgis.testing import QgisTestCase, start_app
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer)
from processing.core.Processing import Processing
import processing

from fct.FluvialCorridorToolbox import FluvialCorridorToolboxProvider, FluvialCorridorWorkflowsProvider

qgis_app = start_app(cleanup=True)

Processing.initialize()
fct = FluvialCorridorToolboxProvider()
fcw = FluvialCorridorWorkflowsProvider()
qgis_app.processingRegistry().addProvider(fct)
qgis_app.processingRegistry().addProvider(fcw)


class TestValleyBottomWorkflow(QgisTestCase):

    @classmethod
    def setUpClass(self):
        self.outdir = tempfile.mkdtemp()
        self.stream_layer = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'stream.gml'))
        self.dem_layer = QgsRasterLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'dem.tif'))
        

    def test_valleybottom_input(self):

        self.assertTrue(self.stream_layer.isValid(), f'Failed to load {self.stream_layer.source()}')
        self.assertTrue(self.dem_layer.isValid(), f'Failed to load {self.dem_layer.source()}')


    def test_valleybottom_topological(self):

        proc_alg = processing.run('fcw:valleybottom', {
            'IN_DEM': self.dem_layer,
            'IN_STREAM': self.stream_layer,
            'METHOD': 0,
            'STEP': 50.0,
            'AGGREG': 5.0,
            'BUFFER': 1500.0,
            'THRESH_MIN': -10.0,
            'THRESH_MAX': 30.0,
            'SIMPLIFY': 10,
            'SMOOTH': 5,
            'OUT_VB': os.path.join(self.outdir, 'vb_topological.gml'),
        })

        output = QgsVectorLayer(proc_alg['OUT_VB'])
        self.assertTrue(output.isValid(), 'Output is not a valid layer')

        expected = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'vb_topological.gml'))
        self.assertTrue(expected.isValid(), f'Failed to load {expected.source()}')
    
        self.assertLayersEqual(expected, output)
        

    def test_valleybottom_nearest(self):

        proc_alg = processing.run('fcw:valleybottom', {
            'IN_DEM': self.dem_layer,
            'IN_STREAM': self.stream_layer,
            'METHOD': 2,
            'STEP': 50.0,
            'AGGREG': 5.0,
            'BUFFER': 1500.0,
            'THRESH_MIN': -10.0,
            'THRESH_MAX': 30.0,
            'SIMPLIFY': 10,
            'SMOOTH': 5,
            'OUT_VB': os.path.join(self.outdir, 'vb_nearest.gml'),
        })
        
        output = QgsVectorLayer(proc_alg['OUT_VB'])
        self.assertTrue(output.isValid(), 'Output is not a valid layer')

        expected = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'vb_nearest.gml'))
        self.assertTrue(expected.isValid(), f'Failed to load {expected.source()}')
    
        self.assertLayersEqual(expected, output)

                         
    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.outdir, True)


class TestCenterlineWorkflow(QgisTestCase):

    @classmethod
    def setUpClass(self):
        self.outdir = tempfile.mkdtemp()
        self.stream_layer = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'stream_extended.gml'))
        self.cutline = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'cutting_line.gml'))
        self.vb = QgsVectorLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'vb_nearest.gml'))
        self.dem_layer = QgsRasterLayer(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 
            'testdata', 'input', 'dem.tif'))


    def test_Centerline_input(self):
        
        self.assertTrue(self.stream_layer.isValid(), f'Failed to load {self.stream_layer.source()}')
        self.assertTrue(self.cutline.isValid(), f'Failed to load {self.cutline.source()}')
        self.assertTrue(self.vb.isValid(), f'Failed to load {self.vb.source()}')
        self.assertTrue(self.dem_layer.isValid(), f'Failed to load {self.dem_layer.source()}')


    def test_centerline_stream(self):
        # Test the centerline algorithm with the real stream as input

        proc_alg = processing.run('fcw:centerline', {
            'POLYGON': self.vb,
            'DISTANCE': 25.0,
            'STREAM': self.stream_layer,
            'OUT_CENTERLINE': os.path.join(self.outdir, 'centerline_stream.gml')
        })

        output = QgsVectorLayer(proc_alg['OUT_CENTERLINE'])
        self.assertTrue(output.isValid(), 'Output is not a valid layer')

        expected = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'centerline_stream.gml'))
        self.assertTrue(expected.isValid(), f'Failed to load {expected.source()}')


    def test_centerline_cutline(self):
        # Test the centerline workflow with a dummy polyline as input

        proc_alg = processing.run('fcw:centerline', {
            'POLYGON': self.vb,
            'DISTANCE': 25.0,
            'STREAM': self.cutline,
            'OUT_CENTERLINE': os.path.join(self.outdir, 'centerline_cutline.gml')
        })

        output = QgsVectorLayer(proc_alg['OUT_CENTERLINE'])
        self.assertTrue(output.isValid(), 'Output is not a valid layer')

        expected = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'centerline_cutline.gml'))
        self.assertTrue(expected.isValid(), f'Failed to load {expected.source()}')


    def test_centerline_stream(self):
        # Test the centerline algorithm with the real stream as input

        proc_alg = processing.run('fcw:centerline', {
            'POLYGON': self.vb,
            'DISTANCE': 25.0,
            'STREAM': self.stream_layer,
            'OUT_CENTERLINE': os.path.join(self.outdir, 'centerline_stream.gml')
        })

        output = QgsVectorLayer(proc_alg['OUT_CENTERLINE'])
        self.assertTrue(output.isValid(), 'Output is not a valid layer')

        expected = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'centerline_stream.gml'))
        self.assertTrue(expected.isValid(), f'Failed to load {expected.source()}')


    def test_centerline_cutline(self):
        # Test the centerline workflow with a dummy polyline as input

        proc_alg = processing.run('fcw:centerline', {
            'POLYGON': self.vb,
            'DISTANCE': 25.0,
            'STREAM': self.cutline,
            'OUT_CENTERLINE': os.path.join(self.outdir, 'centerline_cutline.gml')
        })

        output = QgsVectorLayer(proc_alg['OUT_CENTERLINE'])
        self.assertTrue(output.isValid(), 'Output is not a valid layer')

        expected = QgsVectorLayer(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata', 'expected', 'centerline_cutline.gml'))
        self.assertTrue(expected.isValid(), f'Failed to load {expected.source()}')


    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.outdir, True)
