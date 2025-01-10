# -*- coding: utf-8 -*-

"""
SelectByDistance - Select vectors in layer nearest to a reference layer

***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

import math

from qgis.PyQt.QtCore import ( 
    QVariant
)

from qgis.core import ( 
    QgsApplication,
    QgsExpression,
    QgsGeometry,
    QgsFeatureSink,
    QgsFeatureRequest,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsPointXY,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingFeatureBasedAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterDistance,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProcessingParameterField,
    QgsProcessingParameterVectorLayer,
    QgsSpatialIndex,
    QgsVectorLayer,
    QgsWkbTypes
)

from processing.algs.qgis.QgisAlgorithm import QgisAlgorithm 

from ..metadata import AlgorithmMetadata

class SelectNearestFeature(AlgorithmMetadata, QgsProcessingAlgorithm):

    METADATA = AlgorithmMetadata.read(__file__, 'SelectNearestFeature')

    INPUT_LAYER = 'INPUT'
    REFERENCE_LAYER = 'REFERENCE_LAYER'
    SEARCH_DISTANCE = 'SEARCH_DISTANCE'

    def initAlgorithm(self, configuration=None): 

        self.addParameter(QgsProcessingParameterFeatureSource(self.INPUT_LAYER,
                                          self.tr('Select In Layer'), [QgsProcessing.TypeVectorAnyGeometry]))
        self.addParameter(QgsProcessingParameterFeatureSource(self.REFERENCE_LAYER,
                                          self.tr('Reference Layer'), [QgsProcessing.TypeVectorAnyGeometry]))
        self.addParameter(QgsProcessingParameterDistance(self.SEARCH_DISTANCE,
                                          self.tr('Search Distance'),
                                          defaultValue=0.0))


    def processAlgorithm(self, parameters, context, feedback): 

        input_layer = self.parameterAsVectorLayer(parameters, self.INPUT_LAYER, context)
        reference_layer = self.parameterAsVectorLayer(parameters, self.REFERENCE_LAYER, context)
        search_distance = self.parameterAsDouble(parameters,self.SEARCH_DISTANCE,context)

        spatial_index = QgsSpatialIndex(input_layer.getFeatures())

        total = 100.0 / input_layer.featureCount() if input_layer.featureCount() else 0
        selection = set()

        for current, ref_feature in enumerate(reference_layer.getFeatures()):

            if feedback.isCanceled():
                raise QgsProcessingException(self.tr('Cancelled by user'))
            
            ref_geometry = ref_feature.geometry()
            search_box = ref_geometry.boundingBox()
            search_box.grow(search_distance)

            nearest_id = None
            distance = float('inf')

            for candidate_id in spatial_index.intersects(search_box):

                s = context.getMapLayer(reference_layer.sourceName())
                candidate = s.getFeature(candidate_id)

                d = candidate.geometry().distance(ref_geometry)


                if d < distance:
                    nearest_id = candidate_id
                    distance = d

            if nearest_id is not None:
                selection.add(nearest_id)

            feedback.setProgress(int(current * total))

        input_layer.selectByIds(list(selection), QgsVectorLayer.SetSelection)

        return {}