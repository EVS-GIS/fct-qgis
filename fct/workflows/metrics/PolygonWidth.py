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
    QgsProcessingParameterField,
    QgsWkbTypes,
    QgsFeature,
    QgsField,
    QgsFeatureSink
)

from qgis.PyQt.QtCore import QVariant

from ..metadata import AlgorithmMetadata
from ...utils.assertions import assertLayersCompatibility

class PolygonWidth(AlgorithmMetadata, QgsProcessingAlgorithm):

    METADATA = AlgorithmMetadata.read(__file__, 'PolygonWidth')

    INPUT_POLYGONS = 'INPUT_POLYGONS'
    INPUT_MEDIAL_AXIS = 'INPUT_MEDIAL_AXIS'
    INPUT_POLYGONS_FID = 'INPUT_POLYGONS_FID'
    INPUT_MEDIAL_AXIS_FID = 'INPUT_MEDIAL_AXIS_FID'
    SAMPLING_INTERVAL = 'SAMPLING_INTERVAL'
    MAX_WIDTH = 'MAX_WIDTH'
    OUTPUT_TRANSECTS = 'OUTPUT_TRANSECTS'
    OUTPUT_TABLE = 'OUTPUT_TABLE'
    

    def initAlgorithm(self, configuration): 

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT_POLYGONS,
            self.tr('Disaggregated objects to measure'),
            [QgsProcessing.TypeVectorPolygon]))
        
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT_MEDIAL_AXIS,
            self.tr('Disaggregated axis along which the measurements will be made perpendicularly'),
            [QgsProcessing.TypeVectorLine]))
        
        self.addParameter(QgsProcessingParameterField(
            self.INPUT_POLYGONS_FID,
            self.tr('DGO FID field on objects'),
            type=QgsProcessingParameterField.Numeric,
            parentLayerParameterName=self.INPUT_POLYGONS,
            allowMultiple=False,
            defaultValue='DGO_FID'))

        self.addParameter(QgsProcessingParameterField(
            self.INPUT_MEDIAL_AXIS_FID,
            self.tr('DGO FID field on axis'),
            type=QgsProcessingParameterField.Numeric,
            parentLayerParameterName=self.INPUT_MEDIAL_AXIS,
            allowMultiple=False,
            defaultValue='DGO_FID'))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.SAMPLING_INTERVAL,
            self.tr('Length between sampling transects'),
            type=QgsProcessingParameterNumber.Integer,
            defaultValue=5))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.MAX_WIDTH,
            self.tr('Maximum transects width'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=1000.0))

        self.addParameter(QgsProcessingParameterVectorDestination(
            self.OUTPUT_TABLE,
            self.tr('Output measurement summary table'),
            QgsProcessing.TypeVectorPolygon))
        
        self.addParameter(QgsProcessingParameterVectorDestination(
            self.OUTPUT_TRANSECTS,
            self.tr('Output measurement transects'),
            QgsProcessing.TypeVectorLine,
            optional=True))
        
        
    def processAlgorithm(self, parameters, context, feedback): 

        polygons = self.parameterAsVectorLayer(parameters, self.INPUT_POLYGONS, context)
        medial_axis = self.parameterAsVectorLayer(parameters, self.INPUT_MEDIAL_AXIS, context)
        sampling_interval = self.parameterAsDouble(parameters, self.SAMPLING_INTERVAL, context)
        max_width = self.parameterAsDouble(parameters, self.MAX_WIDTH, context)

        polygon_fid = self.parameterAsString(parameters, self.INPUT_POLYGONS_FID, context)
        medial_axis_fid = self.parameterAsString(parameters, self.INPUT_MEDIAL_AXIS_FID, context)

        assertLayersCompatibility([polygons, medial_axis], feedback)

        transects_fields = medial_axis.fields()
        transects_fields.append(QgsField('LENGTH', QVariant.Double))

        (transects_sink, transects_dest_id) = self.parameterAsSink(parameters, 
                                                                   self.OUTPUT_TRANSECTS, 
                                                                   context, 
                                                                   transects_fields, 
                                                                   QgsWkbTypes.LineString, 
                                                                   medial_axis.sourceCrs())

        transects_proc = processing.run("fct:variablelengthtransects", {
            'INPUT':medial_axis,
            'LENGTH':max_width,
            'INTERVAL':sampling_interval,
            'OUTPUT':QgsProcessing.TEMPORARY_OUTPUT
        }, context=context, feedback=feedback, is_child_algorithm=True)

        transects = context.takeResultLayer(transects_proc['OUTPUT'])

        # Iterate over the polygons
        for polygon in polygons.getFeatures():
            # Get the polygon geometry
            geom = polygon.geometry()

            # Get the FID of the polygon
            fid = polygon.attribute(polygon_fid)

            # Get the transects by FID
            transects.selectByExpression(f'{medial_axis_fid} = {fid}')

            # Iterate over the transects
            for transect in transects.selectedFeatures():
                # Get the transect geometry
                transect_geom = transect.geometry()

                # Get the intersection between the polygon and the transect
                intersection = transect_geom.intersection(geom)

                # If the intersection is not empty, add the feature to the output
                if intersection.isGeosValid():

                    # Create a new feature for the output
                    sampling_transect = QgsFeature(transects_fields)
                    sampling_transect.setGeometry(intersection)

                    attrs = transect.attributes()
                    attrs.append(round(intersection.length(), 3))

                    sampling_transect.setAttributes(attrs)

                    transects_sink.addFeature(sampling_transect, QgsFeatureSink.FastInsert)

        # Close the sink
        del transects_sink

        # Calculate transect length stats by DGO
        stats = processing.run("qgis:statisticsbycategories", {
            'INPUT':transects_dest_id,
            'VALUES_FIELD_NAME':'LENGTH',
            'CATEGORIES_FIELD_NAME':['DGO_FID'],
            'OUTPUT': parameters['OUTPUT_TABLE']
        }, context=context, feedback=feedback, is_child_algorithm=True)

        return {
            self.OUTPUT_TABLE: stats['OUTPUT'],
            self.OUTPUT_TRANSECTS: transects_dest_id
        }
