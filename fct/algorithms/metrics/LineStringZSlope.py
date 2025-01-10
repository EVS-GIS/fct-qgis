# -*- coding: utf-8 -*-

"""
LineStringZ Slope

***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

import numpy as np

from qgis.core import ( 
    QgsGeometry,
    QgsLineString,
    QgsMultiLineString,
    QgsProcessing,
    QgsProcessingFeatureBasedAlgorithm,
    QgsWkbTypes
)

from ..metadata import AlgorithmMetadata

class LineStringZSlope(AlgorithmMetadata, QgsProcessingFeatureBasedAlgorithm):
    """
    Compute slope from Z coordinate
    and store result in Z of created new features.
    """

    METADATA = AlgorithmMetadata.read(__file__, 'LineStringZSlope')

    def inputLayerTypes(self): 
        return [QgsProcessing.TypeVectorLine]

    def outputName(self): 
        return self.tr('LineStrings with Slope Coordinate')

    def outputWkbType(self, inputWkbType): 
        return inputWkbType

    def supportInPlaceEdit(self, layer): 
        return False

    def prepareAlgorithm(self, parameters, context, feedback): 

        layer = self.parameterAsSource(parameters, 'INPUT', context)

        if not QgsWkbTypes.hasZ(layer.wkbType()):
            feedback.reportError(self.tr('Input must have Z coordinate.'), True)
            return False

        # if QgsWkbTypes.isMultiType(layer.wkbType()):
        #     feedback.reportError(self.tr('Multipart geometries are not currently supported'), True)
        #     return False

        return True

    def processFeature(self, feature, context, feedback): 

        def transform(geometry):
            """
            Transform Z into Slope.
            Opposite to mathematical convention,
            slope is oriented in reverse line direction.
            """

            vertices = np.array([(v.x(), v.y(), v.z()) for v in geometry.vertices()])
            slope = np.zeros(len(vertices), dtype=np.float32)

            if len(vertices) > 2:

                # 2D horizontal distance
                distance = np.linalg.norm(vertices[:-1, 0:2] - vertices[1:, 0:2], axis=1)

                slope[1:-1] = (vertices[:-2, 2] - vertices[2:, 2]) / (distance[:-1] + distance[1:])
                slope[0] = slope[1]
                slope[-1] = slope[-2]

            points = list()

            for i, vertex in enumerate(geometry.vertices()):
                vertex.setZ(float(slope[i]))
                points.append(vertex)

            return QgsLineString(points)

        geometry = feature.geometry()

        if geometry.isMultipart():

            parts = QgsMultiLineString()

            for part in geometry.asGeometryCollection():
                linestring = transform(part)
                parts.addGeometry(linestring)

            feature.setGeometry(QgsGeometry(parts))

        else:

            feature.setGeometry(QgsGeometry(transform(geometry)))

        return [feature]
