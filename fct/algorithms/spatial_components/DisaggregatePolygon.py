# -*- coding: utf-8 -*-

"""
DisaggregatePolygon

***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""


from PyQt5.QtCore import QVariant
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsWkbTypes,
    QgsField,
    QgsProcessingUtils,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterNumber,
    QgsVectorLayer,
    QgsProcessingException,
    QgsFeature,
    QgsFeatureSink,
)

import processing

from ..metadata import AlgorithmMetadata
from ..util import asQgsFields
from ...utils.assertions import assertLayersCompatibility


class DisaggregatePolygon(AlgorithmMetadata, QgsProcessingAlgorithm):

    METADATA = AlgorithmMetadata.read(__file__, "DisaggregatePolygon")

    CENTERLINE = "CENTERLINE"
    POLYGON = "POLYGON"
    STEP = "STEP"
    DISAGGREGATED = "DISAGGREGATED"

    def initAlgorithm(self, configuration):

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.CENTERLINE,
                self.tr("Centerline of the polygon"),
                [QgsProcessing.TypeVectorLine],
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.POLYGON,
                self.tr("Polygon to disaggregate"),
                [QgsProcessing.TypeVectorPolygon],
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.STEP,
                self.tr("Disaggregation distance"),
                defaultValue=100.0,
                minValue=0,
            )
        )

        self.addParameter(
             QgsProcessingParameterFeatureSink(
                self.DISAGGREGATED,
                self.tr("Disaggregated polygon"),
                QgsProcessing.TypeVectorPolygon,
            )
        )


    def processAlgorithm(self, parameters, context, feedback):

        centerline = self.parameterAsVectorLayer(parameters, self.CENTERLINE, context)
        polygon = self.parameterAsVectorLayer(parameters, self.POLYGON, context)
        
        assertLayersCompatibility([centerline, polygon], feedback, mutli_geom_allowed=False)

        step = self.parameterAsDouble(parameters, self.STEP, context)

        if polygon.featureCount() > 1:
            raise QgsProcessingException(self.tr("Input polygon must have only one feature"))
       
        if centerline.featureCount() > 1:
            feedback.pushWarning(self.tr(f"Input centerline has {centerline.featureCount()} features. Trying to merge..."))

            identify = processing.run('fct:identifynetworknodes', {
                'INPUT': centerline,
                'NODES': QgsProcessing.TEMPORARY_OUTPUT,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }, feedback=feedback, context=context, is_child_algorithm=True)

            connect = processing.run('fct:aggregateundirectedlines', {
                'INPUT': identify['OUTPUT'],
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }, feedback=feedback, context=context, is_child_algorithm=True)

            singlepart = processing.run('native:multiparttosingleparts', {
                'INPUT': connect['OUTPUT'],
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }, feedback=feedback, context=context, is_child_algorithm=True)

            centerline = QgsVectorLayer(singlepart['OUTPUT'])

            if centerline.featureCount() != 1:
                raise QgsProcessingException(self.tr("Failed to merge centerline features. Check the validity of the input centerline (no multipart features allowed)"))
            else:
                feedback.pushInfo(self.tr("Centerline features merged"))

        cl_feature = next(centerline.getFeatures())
        cl_geom = cl_feature.geometry().simplify(step*2).smooth(10)

        # Points along centerline
        fields = asQgsFields(
            QgsField('DGO_FID', type=QVariant.Int),
            QgsField('DISTANCE', QVariant.Double),
        )

        (sink, cl_points_dest) = QgsProcessingUtils.createFeatureSink(
            'memory:',
            context,
            fields,
            QgsWkbTypes.Point,
            centerline.sourceCrs(),
        )

        for fid, measure in enumerate(range(0, int(cl_geom.length()), int(step))):
            feature = QgsFeature()
            feature.setGeometry(cl_geom.interpolate(measure))
            feature.setAttributes([fid, measure])

            sink.addFeature(feature, QgsFeatureSink.FastInsert)

        # Points along polygon
        polygon_feature = next(polygon.getFeatures())
        polygon_geom = polygon_feature.geometry().removeInteriorRings().convertToType(
                QgsWkbTypes.LineGeometry
            )

        fields = asQgsFields(
            QgsField('FID', type=QVariant.Int),
        )
        
        (sink, poly_points_dest) = QgsProcessingUtils.createFeatureSink(
            'memory:',
            context,
            fields,
            QgsWkbTypes.Point,
            polygon.sourceCrs(),
        )

        for fid, measure in enumerate(range(0, int(polygon_geom.length()), int(step/10))):
            feature = QgsFeature()
            feature.setGeometry(polygon_geom.interpolate(measure))
            feature.setAttributes([fid])
            sink.addFeature(feature, QgsFeatureSink.FastInsert)

        # Distance to centerline
        distance = processing.run('qgis:distancetonearesthubpoints', {
            'INPUT': poly_points_dest,
            'HUBS': cl_points_dest,
            'FIELD': 'DGO_FID',
            'UNIT': 0,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, feedback=feedback, context=context, is_child_algorithm=True)

        double = processing.run('qgis:fieldcalculator', {
            'INPUT': distance['OUTPUT'],
            'FIELD_NAME': 'DoubleDist',
            'FIELD_TYPE': 0,
            'NEW_FIELD': True,
            'FORMULA': 'HubDist*2',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, context=context, feedback=feedback, is_child_algorithm=True)

        means = processing.run('qgis:statisticsbycategories', {
            'INPUT': double['OUTPUT'],
            'CATEGORIES_FIELD_NAME': 'HubName',
            'VALUES_FIELD_NAME': 'DoubleDist',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, feedback=feedback, context=context, is_child_algorithm=True)

        # Refactor fields
        refactor = processing.run("native:refactorfields", {
                'INPUT': means['OUTPUT'],
                'FIELDS_MAPPING':[
                    {'expression': '"HubName"', 'name': 'DGO_FID', 'type': 2, 'type_name': 'integer'},
                    {'expression': 'mean', 'name': 'DGO_WIDTH', 'type': 6, 'type_name': 'double precision'}
                ],
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }, context=context, feedback=feedback, is_child_algorithm=True)

        # Voronoi polygons
        voronoi = processing.run('native:voronoipolygons', {
            'INPUT': cl_points_dest,
            'BUFFER': 50,
            'COPY_ATTRIBUTES': True,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, feedback=feedback, context=context, is_child_algorithm=True)

        # Join voronoi polygons with means
        join = processing.run('qgis:joinattributestable', {
            'INPUT': voronoi['OUTPUT'],
            'FIELD': 'DGO_FID',
            'INPUT_2': refactor['OUTPUT'],
            'FIELD_2': 'DGO_FID',
            'FIELDS_TO_COPY': ['DGO_WIDTH'],
            'METHOD': 1,
            'DISCARD_NONMATCHING': False,
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, feedback=feedback, context=context, is_child_algorithm=True)

        intersect = processing.run('native:clip', {
            'INPUT': join['OUTPUT'],
            'OVERLAY': polygon,
            'OUTPUT': parameters[self.DISAGGREGATED]
        }, feedback=feedback, context=context, is_child_algorithm=True)

        return {self.DISAGGREGATED: intersect['OUTPUT']}
