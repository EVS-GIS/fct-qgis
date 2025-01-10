# -*- coding: utf-8 -*-

"""
Sequencing

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
    QgsProcessingParameterEnum,
    QgsProcessingParameterRasterLayer,
)

from ..metadata import AlgorithmMetadata
from ...utils.assertions import assertLayersCompatibility

class Sequencing(AlgorithmMetadata, QgsProcessingAlgorithm):

    METADATA = AlgorithmMetadata.read(__file__, 'Sequencing')

    INPUT = 'INPUT'
    DEM = 'DEM'
    OUTPUT = 'OUTPUT'


    def initAlgorithm(self, configuration): 

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT,
            self.tr('Input network'),
            [QgsProcessing.TypeVectorLine]))
        
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DEM,
            self.tr('Raw DEM'),
            optional=True))
        
        self.addParameter(QgsProcessingParameterVectorDestination(
            self.OUTPUT,
            self.tr('Sequenced network'),
            QgsProcessing.TypeVectorLine))
        

    def processAlgorithm(self, parameters, context, feedback): 

        network = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        dem = self.parameterAsRasterLayer(parameters, self.DEM, context)

        assertLayersCompatibility([network, dem], feedback)

        identify = processing.run('fct:identifynetworknodes', {
            'INPUT': network,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT,
            'NODES': QgsProcessing.TEMPORARY_OUTPUT,
        }, context=context, feedback=feedback, is_child_algorithm=True)

        drape = processing.run('native:setzfromraster', {
            'INPUT': identify['NODES'],
            'RASTER': dem,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT,
        }, context=context, feedback=feedback, is_child_algorithm=True)

        oriented = processing.run('fct:fixlinkorientation', {
            'INPUT': identify['OUTPUT'],
            'NODES': drape['OUTPUT'],
            'OUTPUT': parameters[self.OUTPUT],
        }, context=context, feedback=feedback, is_child_algorithm=True)

        return {
            self.OUTPUT: oriented['OUTPUT'],
        }