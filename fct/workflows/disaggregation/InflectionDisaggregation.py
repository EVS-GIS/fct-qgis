# -*- coding: utf-8 -*-

"""
InflectionDisaggregation

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
    QgsProcessingException
)

from ..metadata import AlgorithmMetadata
from ...utils.assertions import assertLayersCompatibility

class InflectionDisaggregation(AlgorithmMetadata, QgsProcessingAlgorithm):

    METADATA = AlgorithmMetadata.read(__file__, 'InflectionDisaggregation')

    INPUT = 'INPUT'
    SIMPLIFY = 'SIMPLIFY'
    MAX_DISTANCE = 'MAX_DISTANCE'
    MIN_AMPLITUDE = 'MIN_AMPLITUDE'
    MAX_ANGLE = 'MAX_ANGLE'
    OUTPUT_POINTS = 'OUTPUT_POINTS'
    OUTPUT_LINES = 'OUTPUT_LINES'
    OUTPUT_DISAGGREGATED = 'OUTPUT_DISAGGREGATED'

    def initAlgorithm(self, configuration): 

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT,
            self.tr('Input sequenced network'),
            [QgsProcessing.TypeVectorLine]))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.SIMPLIFY,
            self.tr('Simplification offset'),
            defaultValue=10.0,
            minValue=0))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.MAX_DISTANCE,
            self.tr('Maximum distance between inflection points'),
            defaultValue=200.0,
            minValue=0))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.MIN_AMPLITUDE,
            self.tr('Minimum amplitude'),
            defaultValue=10.0,
            minValue=0))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.MAX_ANGLE,
            self.tr('Maximum angle to consider a point as inflection'),
            defaultValue=50.0,
            minValue=0))

        self.addParameter(QgsProcessingParameterVectorDestination(
            self.OUTPUT_POINTS,
            self.tr('Ouput inflection points'),
            QgsProcessing.TypeVectorPoint))

        self.addParameter(QgsProcessingParameterVectorDestination(
            self.OUTPUT_LINES,
            self.tr('Ouput inflection lines'),
            QgsProcessing.TypeVectorLine))
        
        self.addParameter(QgsProcessingParameterVectorDestination(
            self.OUTPUT_DISAGGREGATED,
            self.tr('Ouput disaggregated network'),
            QgsProcessing.TypeVectorLine))
        

    def processAlgorithm(self, parameters, context, feedback): 

        network = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        simplify = self.parameterAsDouble(parameters, self.SIMPLIFY, context)
        max_distance = self.parameterAsDouble(parameters, self.MAX_DISTANCE, context)
        min_amplitude = self.parameterAsDouble(parameters, self.MIN_AMPLITUDE, context)
        max_angle = self.parameterAsDouble(parameters, self.MAX_ANGLE, context)

        assertLayersCompatibility([network], feedback)

        singlepart = processing.run('qgis:multiparttosingleparts', {
            'INPUT': network,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, context=context, feedback=feedback, is_child_algorithm=True)

        simplified = processing.run('native:simplifygeometries', {
            'INPUT': singlepart['OUTPUT'],
            'METHOD': 0,
            'TOLERANCE': simplify,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, context=context, feedback=feedback, is_child_algorithm=True)

        smooth = processing.run('native:smoothgeometry', {
            'INPUT': simplified['OUTPUT'],
            'ITERATIONS': 10,
            'OFFSET': 0.25,
            'MAX_ANGLE': 180,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, context=context, feedback=feedback, is_child_algorithm=True)

        planform = processing.run('fct:planformmetrics', {
            'INPUT': smooth['OUTPUT'],
            'FLOW_AXIS': parameters['OUTPUT_LINES'],
            'LMAX': max_distance,
            'RESOLUTION': min_amplitude,
            'MAX_ANGLE': max_angle,
            'INFLECTION_POINTS': parameters['OUTPUT_POINTS'],
            'OUTPUT': parameters['OUTPUT_DISAGGREGATED'],
            'STEMS': QgsProcessing.TEMPORARY_OUTPUT,
        }, context=context, feedback=feedback, is_child_algorithm=True)

        return {
            'OUTPUT_DISAGGREGATED': planform['OUTPUT'],
            'OUTPUT_POINTS': planform['INFLECTION_POINTS'],
            'OUTPUT_LINES': planform['FLOW_AXIS']
        }