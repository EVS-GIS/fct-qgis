# -*- coding: utf-8 -*-

"""
MonotonicZ

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
    # QgsMultiLineString,
    QgsProcessing,
    QgsProcessingFeatureBasedAlgorithm,
    QgsProcessingParameterNumber,
    QgsWkbTypes
)

from ..metadata import AlgorithmMetadata

class MonotonicZ(AlgorithmMetadata, QgsProcessingFeatureBasedAlgorithm):
    """
    Adjust Z values for each vertex,
    so that Z always decreases from upstream to downstream.

    Input linestrings must be properly oriented from upstream to downstream,
    and should be aggregated by Hack order.
    """

    METADATA = AlgorithmMetadata.read(__file__, 'MonotonicZ')

    NODATA = 'NODATA'
    MIN_Z_DELTA = 'MIN_Z_DELTA'

    def initParameters(self, configuration=None): 

        self.addParameter(QgsProcessingParameterNumber(
            self.NODATA,
            self.tr('No-Data Value'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=-99999))

        self.addParameter(QgsProcessingParameterNumber(
            self.MIN_Z_DELTA,
            self.tr('Minimum Z Delta'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=.0005))

    def inputLayerTypes(self): 
        return [QgsProcessing.TypeVectorLine]

    def outputName(self): 
        return self.tr('Adjusted Long Profile')

    def outputWkbType(self, inputWkbType): 
        return inputWkbType

    def supportInPlaceEdit(self, layer): 
        return True

    def canExecute(self): 

        try:
            
            import scipy.signal
            return True, ''
        except ImportError:
            return False, self.tr('Missing dependency: scipy.signal')

    def prepareAlgorithm(self, parameters, context, feedback): 

        layer = self.parameterAsSource(parameters, 'INPUT', context)

        if not QgsWkbTypes.hasZ(layer.wkbType()):
            feedback.reportError(self.tr('Input must have Z coordinate.'), True)
            return False

        if QgsWkbTypes.isMultiType(layer.wkbType()):
            feedback.reportError(self.tr('Multipart geometries are not currently supported'), True)
            return False

        self.nodata = self.parameterAsDouble(parameters, self.NODATA, context) or None
        self.z_delta = self.parameterAsDouble(parameters, self.MIN_Z_DELTA, context)

        return True

    def processFeature(self, feature, context, feedback): 

        from scipy import signal

        z_delta = self.z_delta
        nodata = self.nodata

        def transform(geometry):
            """
            Adjust Z so that it decreases downward,
            and slope is always positive.
            """

            z = np.array([v.z() for v in geometry.vertices()])
            skip = (z == nodata)

            if z.shape[0] == 0:
                return geometry

            adjusted = np.full_like(z, nodata)
            zmax = float('inf')

            for i in range(z.shape[0]):

                if skip[i]:
                    continue

                if z[i] > zmax:

                    adjusted[i] = zmax
                    zmax = zmax - z_delta

                else:

                    zmax = adjusted[i] = z[i]

            points = list()

            for i, vertex in enumerate(geometry.vertices()):
                vertex.setZ(float(adjusted[i]))
                points.append(vertex)

            return QgsLineString(points)

        geometry = feature.geometry()

        # if geometry.isMultipart():

        #     parts = QgsMultiLineString()

        #     for part in geometry.asGeometryCollection():
        #         linestring = transform(part)
        #         parts.addGeometry(linestring)

        #     feature.setGeometry(QgsGeometry(parts))

        # else:

        feature.setGeometry(QgsGeometry(transform(geometry)))

        return [feature]
