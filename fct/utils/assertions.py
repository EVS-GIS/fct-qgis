# -*- coding: utf-8 -*-

"""
Generic assertions used by FCT

***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from qgis.core import QgsWkbTypes, QgsProcessingFeedback, QgsProcessingException, QgsVectorLayer, QgsRasterLayer


def assertLayersCompatibility(layers: list[QgsVectorLayer|QgsRasterLayer], feedback: QgsProcessingFeedback, same_crs: bool = True, mutli_geom_allowed: bool = True):
    """ Assert that a list of layers are compatible

    Parameters
    ----------
    layers : list
        List of QgsVectorLayer or QgsRasterLayer


    Feedback reportError with details of failed assertions
    Raises QgsProcessingException if layers are not compatible
    """

    valid = True
    for layer in layers:
        if not layer.isValid():
            feedback.reportError(f'Layer {layer.name()} is not valid')
            valid = False

        if not layer.crs():
            feedback.reportError(f'Input layer {layer.name()} has no CRS')
            valid = False

        if same_crs:
            if not layer.crs().authid() == layers[0].crs().authid():
                feedback.reportError(f'Input layer {layer.name()} have different CRS')
                valid = False   

        if not mutli_geom_allowed:
            if layer.wkbType() == QgsWkbTypes.MultiPolygon:
                feedback.reportError(f'MultiPolygon geometries are not allowed')
                valid = False
            elif layer.wkbType() == QgsWkbTypes.MultiLineString:
                feedback.reportError(f'MultiLineString geometries are not allowed')
                valid = False
            elif layer.wkbType() == QgsWkbTypes.MultiPoint:
                feedback.reportError(f'MultiPoint geometries are not allowed')
                valid = False

    if not valid:
        raise QgsProcessingException("Assertions failed (see above for details)")
