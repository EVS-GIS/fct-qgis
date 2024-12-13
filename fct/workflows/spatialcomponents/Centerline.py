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

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterNumber,
)

from ..metadata import AlgorithmMetadata
from ...utils.assertions import assertLayersCompatibility

class Centerline(AlgorithmMetadata, QgsProcessingAlgorithm):
    """ 
    Extract valley bottom over the studied area
    """

    METADATA = AlgorithmMetadata.read(__file__, 'Centerline')

    POLYGON = 'POLYGON'
    DISTANCE = 'DISTANCE'
    STREAM = 'STREAM'
    DEM = 'DEM'
    OUT_CENTERLINE = 'OUT_CENTERLINE'

    def initAlgorithm(self, configuration):

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.POLYGON,
            self.tr('Input polygon'),
            [QgsProcessing.TypeVectorPolygon]))
        
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.STREAM,
            self.tr('Stream network or up/downstream polyline (see doc)'),
            [QgsProcessing.TypeVectorLine]))

        self.addParameter(QgsProcessingParameterNumber(
            self.DISTANCE,
            self.tr('Disaggregation distance'),
            defaultValue=25.0,
            minValue=1))
        
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DEM,
            self.tr('Input DEM'),
            [QgsProcessing.TypeRaster],
            optional=True))

        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUT_CENTERLINE,
            self.tr('Output Centerline')))

    def processAlgorithm(self, parameters, context, feedback): 

        polygon = self.parameterAsVectorLayer(parameters, self.POLYGON, context)
        stream = self.parameterAsVectorLayer(parameters, self.STREAM, context)
        dem = self.parameterAsRasterLayer(parameters, self.DEM, context)

        layers = [polygon, stream]
        if dem is not None:
            layers.append(dem)

        assertLayersCompatibility(layers, feedback)

        feedback.pushInfo(self.tr('Compute centerline...'))

        if dem is None:

            centerline_proc = processing.run('fct:polygoncenterline',
                {
                    'POLYGON': polygon,
                    'NETWORK': stream,
                    'STEP': self.parameterAsDouble(parameters, self.DISTANCE, context), 
                    'CENTERLINE': parameters[self.OUT_CENTERLINE],
                }, context=context, is_child_algorithm=True, feedback=feedback)

            feedback.pushInfo(self.tr('DEM not provided, skip orientation'))
            return {self.OUT_CENTERLINE: centerline_proc['CENTERLINE']}
        
        else:

            centerline_proc = processing.run('fct:polygoncenterline',
                {
                    'POLYGON': polygon,
                    'NETWORK': stream,
                    'STEP': self.parameterAsDouble(parameters, self.DISTANCE, context), 
                    'CENTERLINE': QgsProcessing.TEMPORARY_OUTPUT,
                }, context=context, is_child_algorithm=True, feedback=feedback)
            feedback.pushInfo(self.tr('Check and fix centerline orientation...'))

            networknodes_proc = processing.run('fct:identifynetworknodes',
                {
                    'INPUT': centerline_proc['CENTERLINE'],
                    'NODES': QgsProcessing.TEMPORARY_OUTPUT,
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT,
                }, context=context, is_child_algorithm=True, feedback=feedback)
            
            drape_proc = processing.run('native:setzfromraster',
                {
                    'INPUT': networknodes_proc['NODES'],
                    'RASTER': dem,
                    'BAND': 1,
                    'NODATA': 0,
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT,
                }, context=context, is_child_algorithm=True, feedback=feedback)
            
            fixlink_proc = processing.run('fct:fixlinkorientation',
                {
                    'INPUT': networknodes_proc['OUTPUT'],
                    'NODES': drape_proc['OUTPUT'],
                    'OUTPUT': parameters[self.OUT_CENTERLINE],
                }, context=context, is_child_algorithm=True, feedback=feedback)

            return {self.OUT_CENTERLINE: fixlink_proc['OUTPUT']}