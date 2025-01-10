# -*- coding: utf-8 -*-

"""
Variable-Width Vertex-Wise Buffer

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
    QgsProcessingFeatureBasedAlgorithm,
    QgsWkbTypes
)

from ..metadata import AlgorithmMetadata

class LineStringBufferByM(AlgorithmMetadata, QgsProcessingFeatureBasedAlgorithm):
    """
    Variable-Width Vertex-Wise Buffer.
    Local buffer width at each vertex is determined from M coordinate.
    """

    METADATA = AlgorithmMetadata.read(__file__, 'LineStringBufferByM')

    def inputLayerTypes(self): 
        return [QgsProcessing.TypeVectorLine]

    def outputName(self): 
        return self.tr('Buffer')

    def outputWkbType(self, inputWkbType): 
        return QgsWkbTypes.Polygon

    def supportInPlaceEdit(self, layer): 
        return False

    def prepareAlgorithm(self, parameters, context, feedback): 

        layer = self.parameterAsSource(parameters, 'INPUT', context)

        if not QgsWkbTypes.hasM(layer.wkbType()):
            feedback.reportError(self.tr('Input must have M coordinate.'), True)
            return False

        return True

    def processFeature(self, feature, context, feedback): 

        features = []

        for geometry in feature.geometry().asGeometryCollection():

            new_geometry = geometry.variableWidthBufferByM(5)
            new_feature = QgsFeature()
            new_feature.setAttributes(feature.attributes())
            new_feature.setGeometry(new_geometry)
            features.append(new_feature)

        return features
