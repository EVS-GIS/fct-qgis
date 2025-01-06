# -*- coding: utf-8 -*-

"""
PolygonWidth

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
    QgsProcessingParameterNumber,
)

from ..metadata import AlgorithmMetadata
from ...utils.assertions import assertLayersCompatibility

class PolygonWidth(AlgorithmMetadata, QgsProcessingAlgorithm):

    METADATA = AlgorithmMetadata.read(__file__, 'PolygonWidth')

    INPUT_POLYGONS = 'INPUT_POLYGONS'
    INPUT_MEDIAL_AXIS = 'INPUT_MEDIAL_AXIS'
    SAMPLING_INTERVAL = 'SAMPLING_INTERVAL'
    MAX_WIDTH = 'MAX_WIDTH'
    OUTPUT_TRANSECTS = 'OUTPUT_TRANSECTS'
    OUTPUT_POLYGONS = 'OUTPUT_POLYGONS'
    

    def initAlgorithm(self, configuration): 

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT_POLYGONS,
            self.tr('Disaggregated objects to measure'),
            [QgsProcessing.TypeVectorPolygon]))
        
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT_MEDIAL_AXIS,
            self.tr('Medial axis along which the measurements will be made perpendicularly'),
            [QgsProcessing.TypeVectorLine]))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.SAMPLING_INTERVAL,
            self.tr('Sampling interval'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=10.0))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.MAX_WIDTH,
            self.tr('Maximum transects width'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=1000.0))

        self.addParameter(QgsProcessingParameterVectorDestination(
            self.OUTPUT_POLYGONS,
            self.tr('Output measures objects'),
            QgsProcessing.TypeVectorPolygon))

        self.addParameter(QgsProcessingParameterVectorDestination(
            self.OUTPUT_TRANSECTS,
            self.tr('Output measurment transects'),
            QgsProcessing.TypeVectorLine,
            optional=True))
        
        
    def processAlgorithm(self, parameters, context, feedback): 

        polygons = self.parameterAsVectorLayer(parameters, self.INPUT_POLYGONS, context)
        medial_axis = self.parameterAsVectorLayer(parameters, self.INPUT_MEDIAL_AXIS, context)
        sampling_interval = self.parameterAsDouble(parameters, self.SAMPLING_INTERVAL, context)
        max_width = self.parameterAsDouble(parameters, self.MAX_WIDTH, context)

        assertLayersCompatibility([polygons, medial_axis], feedback)

        identifier =  processing.run("native:addautoincrementalfield", {
            'INPUT': polygons,
            'FIELD_NAME':'FCT_FID',
            'START':1,
            'MODULUS':0,
            'GROUP_FIELDS':[],
            'SORT_EXPRESSION':'',
            'SORT_ASCENDING':True,
            'SORT_NULLS_FIRST':False,
            'OUTPUT':QgsProcessing.TEMPORARY_OUTPUT
        }, context=context, feedback=feedback, is_child_algorithm=True)

        transects = processing.run("fct:variablelengthtransects", {
            'INPUT':medial_axis,
            'LENGTH':max_width,
            'INTERVAL':sampling_interval,
            'OUTPUT':QgsProcessing.TEMPORARY_OUTPUT
        }, context=context, feedback=feedback, is_child_algorithm=True)