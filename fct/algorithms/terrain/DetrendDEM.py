# -*- coding: utf-8 -*-

"""
DetrendDEM

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

from qgis.core import ( 
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterDistance,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterRasterDestination,
)

import processing

from ..metadata import AlgorithmMetadata


class DetrendDEM(AlgorithmMetadata, QgsProcessingAlgorithm):

    METADATA = AlgorithmMetadata.read(__file__, 'DetrendDEM')

    def initAlgorithm(self, configuration):
        self.addParameter(QgsProcessingParameterRasterLayer('dem', 'Input DEM', defaultValue=None))
        self.addParameter(QgsProcessingParameterDistance('disaggregationdistance', 'Disaggregation Distance', parentParameterName='dem', defaultValue=None, type=QgsProcessingParameterDistance.Double))
        self.addParameter(QgsProcessingParameterFeatureSource('stream', 'Stream network', types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterDestination('Detrended', 'Output detrended DEM', createByDefault=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(7, model_feedback)
        results = {}
        outputs = {}

        # Create tmpdir
        tmpdir = tempfile.mkdtemp(prefix='fct_')

        # Raster Info
        alg_params = {
            'BAND': 1,
            'INPUT': parameters['dem']
        }
        outputs['RasterInfo'] = processing.run('fct:rasterinfo', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Simplifier
        alg_params = {
            'INPUT': parameters['stream'],
            'METHOD': 0,  # Distance (Douglas-Peucker)
            'TOLERANCE': 2.5,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Simplifier'] = processing.run('native:simplifygeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Points le long d'une géométrie
        alg_params = {
            'DISTANCE': parameters['disaggregationdistance'],
            'END_OFFSET': 0,
            'INPUT': outputs['Simplifier']['OUTPUT'],
            'START_OFFSET': 0,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PointsLeLongDuneGomtrie'] = processing.run('qgis:pointsalonglines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        # Update FID field
        alg_params = { 
            'FIELD_LENGTH' : 0, 
            'FIELD_NAME' : 'fid', 
            'FIELD_PRECISION' : 0, 
            'FIELD_TYPE' : 1, 
            'FORMULA' : '@id', 
            'INPUT' : outputs['PointsLeLongDuneGomtrie']['OUTPUT'], 
            'OUTPUT' : QgsProcessing.TEMPORARY_OUTPUT }
        outputs['UpdateFID'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Focal Mean
        alg_params = {
            'FIELD': 'VALUE',
            'HEIGHT': 15,
            'INPUT': parameters['dem'],
            'POINTS': outputs['UpdateFID']['OUTPUT'],
            'WIDTH': 15,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FocalMean'] = processing.run('fct:focalmean', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Voronoi Polygons
        voronoi = os.path.join(tmpdir, 'voronoi.gpkg')
        alg_params = {
            'INPUT': outputs['FocalMean']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['VoronoiPolygons'] = processing.run('fct:scipyvoronoipolygons', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Rastérisation (vecteur vers raster)
        alg_params = {
            'BURN': 0,
            'DATA_TYPE': 5,  # Float32
            'EXTENT': parameters['dem'],
            'EXTRA': '',
            'FIELD': 'VALUE',
            'HEIGHT': outputs['RasterInfo']['YSIZE'],
            'INIT': 0,
            'INPUT': outputs['VoronoiPolygons']['OUTPUT'],
            'INVERT': False,
            'NODATA': 0,
            'OPTIONS': '',
            'UNITS': 0,  # Pixels
            'USE_Z': False,
            'WIDTH': outputs['RasterInfo']['XSIZE'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['RastrisationVecteurVersRaster'] = processing.run('gdal:rasterize', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # RasterDifference
        alg_params = {
            'BAND1': 1,
            'BAND2': 1,
            'RASTER1': parameters['dem'],
            'RASTER2': outputs['RastrisationVecteurVersRaster']['OUTPUT'],
            'USE_GDAL': False,
            'OUTPUT': parameters['Detrended']
        }
        outputs['Rasterdifference'] = processing.run('fct:rasterdifference', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Detrended'] = outputs['Rasterdifference']['OUTPUT']
        return results