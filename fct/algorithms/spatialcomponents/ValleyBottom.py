# -*- coding: utf-8 -*-

"""
ValleyBottom

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
import processing

from qgis.core import ( 
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterDistance,
    QgsProcessingParameterNumber,
    QgsProcessingParameterExtent,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterFeatureSink,
)

from ..metadata import AlgorithmMetadata

class ValleyBottom(AlgorithmMetadata, QgsProcessingAlgorithm):
    
    METADATA = AlgorithmMetadata.read(__file__, 'ValleyBottom')

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer('detrendeddem', 'Input detrended DEM', defaultValue=None))
        self.addParameter(QgsProcessingParameterExtent('bbox', 'Output extent', defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSource('inputstreamnetwork', 'Input stream network', types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        self.addParameter(QgsProcessingParameterDistance('largebufferdistanceparameter', 'Max width (large buffer distance)', parentParameterName='detrendeddem', minValue=0, defaultValue=1500))
        self.addParameter(QgsProcessingParameterDistance('mergedistance', 'Merge objects distance', parentParameterName='detrendeddem', minValue=0, defaultValue=5))
        self.addParameter(QgsProcessingParameterDistance('min_height', 'Min height', parentParameterName='detrendeddem', defaultValue=-10))
        self.addParameter(QgsProcessingParameterDistance('max_height', 'Max height', parentParameterName='detrendeddem', defaultValue=10))
        self.addParameter(QgsProcessingParameterNumber('simplify', 'Simplify tolerance', minValue=1, defaultValue=10))
        self.addParameter(QgsProcessingParameterNumber('smoothing', 'Smoothing iterations', minValue=1, defaultValue=5))
        self.addParameter(QgsProcessingParameterRasterDestination('Valleybottom_raster', 'Output valley bottom raster', createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Valleybottom_polygon', 'Output valley bottom polygons', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, supportsAppend=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(10, model_feedback)
        results = {}
        outputs = {}

        # Bottom extraction
        alg_params = { 
            'BAND_A' : 1, 
            'EXTRA' : '', 
            'FORMULA' : f'logical_and(A<{parameters["max_height"]}, A>{parameters["min_height"]})', 
            'INPUT_A' : parameters['detrendeddem'], 
            'NO_DATA' : None, 
            'OPTIONS' : '', 
            'OUTPUT' : QgsProcessing.TEMPORARY_OUTPUT, 
            'PROJWIN' : parameters['bbox'], 
            'RTYPE' : 0 }
        outputs['BottomExtraction'] = processing.run('gdal:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Simplify network
        alg_params = {
            'INPUT': parameters['inputstreamnetwork'],
            'METHOD': 0,  # Distance (Douglas-Peucker)
            'TOLERANCE': 10,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['SimplifyNetwork'] = processing.run('native:simplifygeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Compute large buffer
        alg_params = {
            'DISSOLVE': True,
            'DISTANCE': parameters['largebufferdistanceparameter'],
            'END_CAP_STYLE': 0,  # Rond
            'INPUT': outputs['SimplifyNetwork']['OUTPUT'],
            'JOIN_STYLE': 0,  # Rond
            'MITER_LIMIT': 2,
            'SEGMENTS': 5,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ComputeLargeBuffer'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Clip bottom by large buffer
        alg_params = {
            'ALPHA_BAND': False,
            'CROP_TO_CUTLINE': True,
            'DATA_TYPE': 0,  # Utiliser le type de donnée de la couche en entrée
            'EXTRA': '',
            'INPUT': outputs['BottomExtraction']['OUTPUT'],
            'KEEP_RESOLUTION': True,
            'MASK': outputs['ComputeLargeBuffer']['OUTPUT'],
            'MULTITHREADING': False,
            'NODATA': None,
            'OPTIONS': '',
            'SET_RESOLUTION': False,
            'SOURCE_CRS': None,
            'TARGET_CRS': None,
            'TARGET_EXTENT': None,
            'X_RESOLUTION': None,
            'Y_RESOLUTION': None,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ClipBottomByLargeBuffer'] = processing.run('gdal:cliprasterbymasklayer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Merge close objects
        alg_params = {
            'BAND': 1,
            'DISTANCE': parameters['mergedistance'],
            'INPUT': outputs['ClipBottomByLargeBuffer']['OUTPUT'],
            'ITERATIONS': 5,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['MergeCloseObjects'] = processing.run('fct:binaryclosing', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Sieve result
        alg_params = {
            'EIGHT_CONNECTEDNESS': False,
            'INPUT': outputs['MergeCloseObjects']['OUTPUT'],
            'MASK_LAYER': None,
            'NO_MASK': False,
            'THRESHOLD': 40,
            'OUTPUT': parameters['Valleybottom_raster']
        }
        outputs['SieveResult'] = processing.run('gdal:sieve', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Valleybottom_raster'] = outputs['SieveResult']['OUTPUT']

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Polygonize
        alg_params = {
            'BAND': 1,
            'EIGHT_CONNECTEDNESS': False,
            'FIELD': 'VALUE',
            'INPUT': outputs['SieveResult']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Polygonize'] = processing.run('gdal:polygonize', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # Extract valley bottom polygon
        alg_params = {
            'FIELD': 'VALUE',
            'INPUT': outputs['Polygonize']['OUTPUT'],
            'OPERATOR': 0,  # =
            'VALUE': '1',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractValleyBottomPolygon'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # Simplify polygon
        alg_params = {
            'INPUT': outputs['ExtractValleyBottomPolygon']['OUTPUT'],
            'METHOD': 0,  # Distance (Douglas-Peucker)
            'TOLERANCE': parameters['simplify'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['SimplifyPolygon'] = processing.run('native:simplifygeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # Smooth polygon
        alg_params = {
            'INPUT': outputs['SimplifyPolygon']['OUTPUT'],
            'ITERATIONS': parameters['smoothing'],
            'MAX_ANGLE': 180,
            'OFFSET': 0.25,
            'OUTPUT': parameters['Valleybottom_polygon']
        }
        outputs['SmoothPolygon'] = processing.run('native:smoothgeometry', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Valleybottom_polygon'] = outputs['SmoothPolygon']['OUTPUT']
        return results