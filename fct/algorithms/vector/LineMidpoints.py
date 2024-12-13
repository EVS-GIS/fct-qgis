# -*- coding: utf-8 -*-

"""
LineMidPoints - Generate a point at the middle of each segment

***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from qgis.core import (
    QgsFeature,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsWkbTypes
)

from ..metadata import AlgorithmMetadata

class LineMidpoints(AlgorithmMetadata, QgsProcessingAlgorithm):
    """
    Generate a point at the middle of each segment
    """

    METADATA = AlgorithmMetadata.read(__file__, 'LineMidpoints')

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, configuration): 

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT,
            self.tr('Input linestrings'),
            [QgsProcessing.TypeVectorLine]))

        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT,
            self.tr('Midpoints'),
            QgsProcessing.TypeVectorPoint))

    def processAlgorithm(self, parameters, context, feedback): 

        layer = self.parameterAsSource(parameters, self.INPUT, context)

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            layer.fields(),
            QgsWkbTypes.Point,
            layer.sourceCrs())
            
        total = 100.0 / layer.featureCount() if layer.featureCount() else 0

        for current, feature in enumerate(layer.getFeatures()):
        
            if feedback.isCanceled():
              raise QgsProcessingException(self.tr('Cancelled by user'))
            
            geom = feature.geometry()
            midpoint = geom.interpolate(0.5 * geom.length())
            outfeature = QgsFeature()
            outfeature.setGeometry(midpoint)
            outfeature.setAttributes(feature.attributes())
            sink.addFeature(outfeature)            

            feedback.setProgress(int(current * total))
            
        return {self.OUTPUT: dest_id}          