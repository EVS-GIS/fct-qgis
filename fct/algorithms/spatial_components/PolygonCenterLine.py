# -*- coding: utf-8 -*-

"""
ValleyCenterLine

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
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsWkbTypes,
    QgsPointXY,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterNumber,
    QgsGeometry,
    QgsFeature,
)

from ..metadata import AlgorithmMetadata


class PolygonCenterLine(AlgorithmMetadata, QgsProcessingAlgorithm):
    """ 
    Center-line (ie. medial axis) of the input polygons based on an auxiliary stream network.
    """

    METADATA = AlgorithmMetadata.read(__file__, "PolygonCenterLine")

    POLYGON = "POLYGON"
    NETWORK = "NETWORK"
    POLY_AXIS_FID = "POLY_AXIS_FID"
    AXIS_FID = "AXIS_FID"
    STEP = "STEP"
    SMOOTH = "SMOOTH"
    CENTERLINE = "CENTERLINE"

    def initAlgorithm(self, configuration):

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.POLYGON,
                self.tr("Input polygon"),
                [QgsProcessing.TypeVectorPolygon],
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.NETWORK, self.tr("Stream network or up/downstream polyline (see doc)"), 
                [QgsProcessing.TypeVectorLine]
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.STEP, self.tr("Disaggregation distance"), 
                defaultValue=25
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.SMOOTH, self.tr("Smoothing factor"), 
                defaultValue=5
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.CENTERLINE, self.tr("Output centerline")
            )
        )

    def processAlgorithm(
        self, parameters, context, feedback
    ):  
        network = self.parameterAsSource(parameters, self.NETWORK, context)
        polygons = self.parameterAsSource(parameters, self.POLYGON, context)
        step = self.parameterAsInt(parameters, self.STEP, context)
        smooth = self.parameterAsInt(parameters, self.SMOOTH, context)

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.CENTERLINE,
            context,
            polygons.fields(),
            QgsWkbTypes.LineString,
            polygons.sourceCrs(),
        )

        for polygon in polygons.getFeatures():
            if feedback.isCanceled():
                feedback.reportError(self.tr("Aborted"), True)
                break

            polygon_geom = polygon.geometry().simplify(step)
            geom_ring = polygon_geom.removeInteriorRings().convertToType(
                QgsWkbTypes.LineGeometry
            )

            for polyline in network.getFeatures():
                stream_geom = polyline.geometry()
                pts_collection = stream_geom.intersection(
                    geom_ring
                ).asGeometryCollection()

                pts = [point for point in pts_collection]

                # Compute distances matrix if more than 2 intersetion points
                if len(pts) < 2:
                    feedback.reportError(
                        self.tr(
                            f"Not enough intersection points between polygon and network features (2 needed)"
                        )
                    )
                    break

                elif len(pts) > 2:
                    matrix = np.array(np.meshgrid(pts, pts)).T.reshape(-1, 2)
                    dist_func = lambda x: abs(
                        stream_geom.lineLocatePoint(x[0])
                        - stream_geom.lineLocatePoint(x[1])
                    )
                    matrix = np.c_[
                        matrix, np.apply_along_axis(dist_func, 1, matrix)
                    ]

                    # Search the maximum distance and the closest vertices on the ring
                    extreme_pts = matrix[
                        np.where(matrix[:, 2] == max(matrix[:, 2]))
                    ]
                    first_vertex = extreme_pts[0, 0].asPoint()
                    second_vertex = extreme_pts[0, 1].asPoint()

                else:
                    first_vertex = pts[0].asPoint()
                    second_vertex = pts[1].asPoint()

                vertex1 = geom_ring.closestVertex(first_vertex)
                vertex2 = geom_ring.closestVertex(second_vertex)

                # Create two lines for the two sides of the valley bottom
                # Swap vertices if not in the rigth direction
                if vertex1[1] > vertex2[1]:
                    vertex1, vertex2 = vertex2, vertex1
                    first_vertex, second_vertex = second_vertex, first_vertex

                # First side
                pts_list = [
                    QgsPointXY(geom_ring.vertexAt(vertex))
                    for vertex in range(vertex1[1], vertex2[1], 1)
                ]
                pts_list.insert(0, first_vertex)
                pts_list.append(second_vertex)
                line1 = QgsGeometry().fromPolylineXY(pts_list)

                # Second side
                vert_list = list(range(vertex2[1], len(geom_ring.asPolyline()), 1))
                vert_list.extend(list(range(0, vertex1[1], 1)))
                pts_list = [
                    QgsPointXY(geom_ring.vertexAt(vertex)) for vertex in vert_list
                ]
                pts_list.insert(0, second_vertex)
                pts_list.append(first_vertex)
                line2 = QgsGeometry().fromPolylineXY(pts_list)

                # Points along sides and Voronoi diagram
                length = stream_geom.length()
                pos = step
                center_pts = []
                while pos < length:
                    center_pts.append(stream_geom.interpolate(pos))
                    pos += step

                voronoi_centroids = []
                for center in center_pts:
                    voronoi_centroids.append(line1.nearestPoint(center).asPoint())
                    voronoi_centroids.append(line2.nearestPoint(center).asPoint())

                points = QgsGeometry().fromMultiPointXY(voronoi_centroids)
                voronoi = points.voronoiDiagram()

                # Dissolve one side
                voronoi_selection = [
                    geom
                    for geom in voronoi.asGeometryCollection()
                    if geom.intersection(line1)
                ]
                side = QgsGeometry().unaryUnion(voronoi_selection)

                # Intersect with polygon
                side = side.coerceToType(QgsWkbTypes.LineString)
                geom = side[0].intersection(polygon_geom)

                centerline = geom.smooth(smooth)
                feat = QgsFeature()
                feat.setGeometry(centerline)
                feat.setAttributes(polygon.attributes())
                sink.addFeature(feat)

        return {self.CENTERLINE: dest_id}
