# -*- coding: utf-8 -*-

"""
ElevationAndSlope

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
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterRasterLayer,
)

from ..metadata import AlgorithmMetadata
from ...utils.assertions import assertLayersCompatibility

class ElevationAndSlope(AlgorithmMetadata, QgsProcessingAlgorithm):

    METADATA = AlgorithmMetadata.read(__file__, 'ElevationAndSlope')

    NETWORK = 'NETWORK'
    DEM = 'DEM'
    OUTPUT_LINES = 'OUTPUT_LINES'
    

    def initAlgorithm(self, configuration): 

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.NETWORK,
            self.tr('Input polylines'),
            [QgsProcessing.TypeVectorLine]))
        
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DEM,
            self.tr('Raw DEM'),
            optional=True))

        self.addParameter(QgsProcessingParameterVectorDestination(
            self.OUTPUT_LINES,
            self.tr('Attributed polylines'),
            QgsProcessing.TypeVectorLine))
        
        
    def processAlgorithm(self, parameters, context, feedback): 

        network = self.parameterAsVectorLayer(parameters, self.NETWORK, context)
        dem = self.parameterAsRasterLayer(parameters, self.DEM, context)

        assertLayersCompatibility([network, dem], feedback)

        identifier =  processing.run("native:addautoincrementalfield", {
            'INPUT': network,
            'FIELD_NAME':'FCT_FID',
            'START':1,
            'MODULUS':0,
            'GROUP_FIELDS':[],
            'SORT_EXPRESSION':'',
            'SORT_ASCENDING':True,
            'SORT_NULLS_FIRST':False,
            'OUTPUT':QgsProcessing.TEMPORARY_OUTPUT
        }, context=context, feedback=feedback, is_child_algorithm=True)

        drape = processing.run('native:setzfromraster', {
            'INPUT': identifier['OUTPUT'],
            'RASTER': dem,
            'BAND': 1,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, context=context, feedback=feedback, is_child_algorithm=True)

        slope = processing.run('fct:linestringzslope', {
            'INPUT': drape['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, context=context, feedback=feedback, is_child_algorithm=True)

        z_attr = processing.run("native:extractzvalues", {
            'INPUT': drape['OUTPUT'],
            'COLUMN_PREFIX': 'Z_',
            'SUMMARIES': [0,1,4,5,6,7,8],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, context=context, feedback=feedback, is_child_algorithm=True)

        slope_attr = processing.run("native:extractzvalues", {
            'INPUT': slope['OUTPUT'],
            'COLUMN_PREFIX': 'SLOPE_',
            'SUMMARIES': [0,1,4,5,6,7,8],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, context=context, feedback=feedback, is_child_algorithm=True)

        join = processing.run("native:joinattributestable", {
            'INPUT': z_attr['OUTPUT'],
            'FIELD': 'FCT_FID',
            'INPUT_2': slope_attr['OUTPUT'],
            'DISCARD_NONMATCHING': False,
            'FIELD_2':'FCT_FID',
            'FIELDS_TO_COPY':['SLOPE_first','SLOPE_last','SLOPE_mean','SLOPE_median','SLOPE_stdev','SLOPE_min','SLOPE_max'],
            'METHOD':0,
            'DISCARD_NONMATCHING':False,
            'PREFIX':'',
            'OUTPUT': parameters[self.OUTPUT_LINES]
        }, context=context, feedback=feedback, is_child_algorithm=True)

        return {
            self.OUTPUT_LINES: join['OUTPUT']
        }