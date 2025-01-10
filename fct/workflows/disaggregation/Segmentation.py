# -*- coding: utf-8 -*-

"""
Segmentation

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
    QgsWkbTypes,
    QgsProcessingException
)

from ..metadata import AlgorithmMetadata
from ...utils.assertions import assertLayersCompatibility

class Segmentation(AlgorithmMetadata, QgsProcessingAlgorithm):
    """
    Segmentation
    """

    METADATA = AlgorithmMetadata.read(__file__, 'Segmentation')

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    STEP = 'STEP'
    CENTERLINE = 'CENTERLINE'

    def initAlgorithm(self, configuration): 

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT,
            self.tr('Input features to segment'),
            [QgsProcessing.TypeVectorLine, QgsProcessing.TypeVectorPolygon]))

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.CENTERLINE,
            self.tr('Centerline of the polygon to segment'),
            [QgsProcessing.TypeVectorLine],
            optional=True))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.STEP,
            self.tr('Segmentation step'),
            defaultValue=25.0,
            minValue=0))

        self.addParameter(QgsProcessingParameterVectorDestination(
            self.OUTPUT,
            self.tr('Segmented features')))


    def prepareAlgorithm(self, parameters, context, feedback): 

        self.segStep = self.parameterAsDouble(parameters, self.STEP, context)
        self.layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        self.cl_layer = self.parameterAsVectorLayer(parameters, self.CENTERLINE, context)

        if self.segStep == 0:
            raise QgsProcessingException(self.tr('Segmentation step is null'))
        
        if self.layer.wkbType() == QgsWkbTypes.Polygon or self.layer.wkbType() == QgsWkbTypes.MultiPolygon:
            if self.cl_layer == None:
                raise QgsProcessingException(self.tr('Polygon segmentation requires a centerline'))

            elif not(self.cl_layer.wkbType() == QgsWkbTypes.LineString or self.cl_layer.wkbType() == QgsWkbTypes.MultiLineString):
                raise QgsProcessingException(self.tr('Unsupported centerline geometry type'))
            
            else:
                assertLayersCompatibility([
                    self.layer,
                    self.cl_layer
                ], feedback)

            feedback.pushInfo(self.tr('Polygon segmentation'))
            self.input_type = 'Polygon'
            return True
 
        elif self.layer.wkbType() == QgsWkbTypes.LineString or self.layer.wkbType() == QgsWkbTypes.MultiLineString:
            feedback.pushInfo(self.tr('LineString segmentation'))
            self.input_type = 'LineString'
            return True

        else:
            raise QgsProcessingException(self.tr('Unsupported geometry type'))
    

    def processAlgorithm(self, parameters, context, feedback): 
        
        if self.input_type == 'Polygon':

            feedback.pushInfo('Compute polygon DGOs...')
            DGOs = processing.run('fct:disaggregatepolygon',
                    {
                        'POLYGON': self.layer,
                        'CENTERLINE': self.cl_layer,
                        'STEP': str(self.segStep),
                        'DISAGGREGATED': parameters['OUTPUT']
                    }, context=context, feedback=feedback, is_child_algorithm=True)

            return {self.OUTPUT: DGOs['DISAGGREGATED']}

        elif self.input_type == 'LineString':

            feedback.pushInfo('Compute line DGOs...')
            segments = processing.run('fct:segmentize',
            {
                'DISTANCE': self.segStep,
                'INPUT': self.layer,
                'OUTPUT': parameters['OUTPUT']
            }, context=context, feedback=feedback, is_child_algorithm=True)
            
            return {self.OUTPUT: segments['OUTPUT']}
