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

import processing
import os
import tempfile

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
)

from ..metadata import AlgorithmMetadata

class ValleyBottom(AlgorithmMetadata, QgsProcessingAlgorithm):
    """ 
    Extract valley bottom over the studied area
    """

    METADATA = AlgorithmMetadata.read(__file__, 'ValleyBottom')
    
    IN_DEM = 'IN_DEM'
    IN_STREAM = 'IN_STREAM'
    METHOD = 'METHOD'
    STEP = 'STEP'
    AGGREG = 'AGGREG'
    BUFFER = 'BUFFER'
    THRESH_MIN = 'THRESH_MIN'
    THRESH_MAX = 'THRESH_MAX'
    BBOX = 'BBOX'
    SIMPLIFY = 'SIMPLIFY'
    SMOOTH = 'SMOOTH'
    OUT_VB = 'OUT_VB'

    def initAlgorithm(self, configuration):

        self.addParameter(QgsProcessingParameterRasterLayer(
            self.IN_DEM,
            self.tr('Input DEM'),
            [QgsProcessing.TypeRaster]))

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.IN_STREAM,
            self.tr('Input stream network'),
            [QgsProcessing.TypeVectorLine]))

        self.addParameter(QgsProcessingParameterEnum(
            self.METHOD,
            self.tr('Detrending method'),
            allowMultiple=False,
            options=['Topological', 'Flow', 'Nearest'],
            defaultValue='Topological'))

        self.addParameter(QgsProcessingParameterNumber(
            self.STEP,
            self.tr('Disaggregation step (topological detrending only)'),
            defaultValue=50.0,
            minValue=1))

        self.addParameter(QgsProcessingParameterNumber(
            self.AGGREG,
            self.tr('Isolated objects aggregation distance'),
            defaultValue=5.0,
            minValue=1))

        self.addParameter(QgsProcessingParameterNumber(
            self.BUFFER,
            self.tr('Max width (large buffer size)'),
            defaultValue=1500.0,
            minValue=1))

        self.addParameter(QgsProcessingParameterNumber(
            self.THRESH_MIN,
            self.tr('Minimum relative height value'),
            defaultValue=-10.0,
            type=QgsProcessingParameterNumber.Double))

        self.addParameter(QgsProcessingParameterNumber(
            self.THRESH_MAX,
            self.tr('Maximum relative height value'),
            defaultValue=10.0,
            type=QgsProcessingParameterNumber.Double))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.SIMPLIFY,
            self.tr('Simplify VB tolerance'),
            defaultValue=10))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.SMOOTH,
            self.tr('Smooth VB iterations'),
            defaultValue=5))
        
        self.addParameter(QgsProcessingParameterExtent(
            self.BBOX, 
            self.tr('Output extent'), 
            defaultValue=None))

        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUT_VB,
            self.tr('Output valley bottom')))

    def processAlgorithm(self, parameters, context, feedback): 
        
        # Step 1: Detrend DEM

        method = self.parameterAsString(parameters, self.METHOD, context)

        if method == '0':
            feedback.pushInfo(self.tr('Topological detrending...'))

            detrended_dem = processing.run('fct:detrenddem',
                {
                    'dem': self.parameterAsRasterLayer(parameters, self.IN_DEM, context),
                    'disaggregationdistance': self.parameterAsDouble(parameters, self.STEP, context), 
                    'Detrended': QgsProcessing.TEMPORARY_OUTPUT, 
                    'stream': self.parameterAsVectorLayer(parameters, self.IN_STREAM, context)
                }, context=context)
            
            relative_dem = detrended_dem['Detrended']

        if method == '1':
            feedback.pushInfo(self.tr('Flow detrending...'))
            feedback.pushInfo(self.tr('  Flow direction...'))
            flow_dir = processing.run('fct:flowdirection',
                { 
                    'ELEVATIONS': self.parameterAsRasterLayer(parameters, self.IN_DEM, context), 
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT 
                }, context=context)

            feedback.pushInfo(self.tr('  Detrend DEM...'))
            detrended_dem = processing.run('fct:relativedembyflow',
                { 
                    'FLOW': flow_dir['OUTPUT'], 
                    'INPUT': self.parameterAsRasterLayer(parameters, self.IN_DEM, context), 
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT, 
                    'STREAM': self.parameterAsVectorLayer(parameters, self.IN_STREAM, context)
                }, context=context)
            
            relative_dem = detrended_dem['OUTPUT']

        if method == '2':
            feedback.pushInfo(self.tr('Nearest detrending...'))

            detrended_dem = processing.run('fct:relativedem',
                {
                    'INPUT': self.parameterAsRasterLayer(parameters, self.IN_DEM, context),
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT,
                    'STREAM': self.parameterAsVectorLayer(parameters, self.IN_STREAM, context)
                }, context=context)
            
            relative_dem = detrended_dem['OUTPUT']

        if feedback.isCanceled():
            return {}

        # Step 2: Compute and return Valley Bottom

        feedback.pushInfo(self.tr('Compute Valley Bottom...'))
        tmpdir = tempfile.mkdtemp(prefix='fct_')

        valleybottom = processing.run('fct:valleybottom',
            {
                'detrendeddem': relative_dem, 
                'Valleybottom_raster': os.path.join(tmpdir, 'VB_RASTER.tif'),
                'inputstreamnetwork': self.parameterAsVectorLayer(parameters, self.IN_STREAM, context),
                'largebufferdistanceparameter': self.parameterAsDouble(parameters, self.BUFFER, context),
                'mergedistance': self.parameterAsDouble(parameters, self.AGGREG, context),
                'Valleybottom_polygon': parameters['OUT_VB'],
                'min_height': self.parameterAsDouble(parameters, self.THRESH_MIN, context),
                'max_height': self.parameterAsDouble(parameters, self.THRESH_MAX, context),
                'simplify': self.parameterAsDouble(parameters, self.SIMPLIFY, context),
                'smoothing': self.parameterAsDouble(parameters, self.SMOOTH, context),
                'bbox': self.parameterAsExtent(parameters, self.BBOX, context)
            }, context=context)

        return {self.OUT_VB: valleybottom['Valleybottom_polygon']}