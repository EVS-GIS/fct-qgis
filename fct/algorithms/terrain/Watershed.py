# -*- coding: utf-8 -*-

"""
Watershed Analysis

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
from osgeo import gdal
# import osr

from qgis.core import ( 
    QgsProcessingAlgorithm,
    QgsProcessingParameterEnum,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer
)

from ..metadata import AlgorithmMetadata

class Watershed(AlgorithmMetadata, QgsProcessingAlgorithm):
    """
    Fills no-data cells in Target Raster
    by propagating data values in the inverse (ie. upward) flow direction
    given by D8-encoded Flow Direction.

    In typical usage,
    the `Target Raster` is the Strahler order for stream cells and no data elsewhere,
    and the result is a raster map of watersheds, identified by their Strahler order.
    """

    METADATA = AlgorithmMetadata.read(__file__, 'Watershed')

    FLOW = 'FLOW'
    TARGET = 'TARGET'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, configuration): 

        self.addParameter(QgsProcessingParameterRasterLayer(
            self.TARGET,
            self.tr('Target Raster')))

        self.addParameter(QgsProcessingParameterRasterLayer(
            self.FLOW,
            self.tr('Flow Direction')))

        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT,
            self.tr('Watersheds')))

    def canExecute(self): 

        try:
            
            from ...lib import terrain_analysis as ta
            return True, ''
        except ImportError:
            return False, self.tr('Missing dependency: FCT terrain_analysis')

    def processAlgorithm(self, parameters, context, feedback): 

        
        from ...lib import terrain_analysis as ta

        flow_lyr = self.parameterAsRasterLayer(parameters, self.FLOW, context)
        target_lyr = self.parameterAsRasterLayer(parameters, self.TARGET, context)
        output = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        flow_ds = gdal.Open(flow_lyr.dataProvider().dataSourceUri())
        flow = flow_ds.GetRasterBand(1).ReadAsArray()

        target_ds = gdal.Open(target_lyr.dataProvider().dataSourceUri())
        nodata = target_ds.GetRasterBand(1).GetNoDataValue()

        if not nodata:
            feedback.reportError(self.tr('Nodata value should be set in the raster properties'), True)
            return {}
        
        # TODO check target dtype
        target = np.float32(target_ds.GetRasterBand(1).ReadAsArray())

        ta.watershed(flow, target, feedback=feedback)

        target[flow == -1] = nodata

        if feedback.isCanceled():
            feedback.reportError(self.tr('Aborted'), True)
            return {}

        feedback.setProgress(100)
        feedback.pushInfo(self.tr('Write output ...'))

        driver = gdal.GetDriverByName('GTiff')

        dst = driver.Create(
            output,
            xsize=target_ds.RasterXSize,
            ysize=target_ds.RasterYSize,
            bands=1,
            eType=gdal.GDT_Float32,
            options=['TILED=YES', 'COMPRESS=DEFLATE'])
        dst.SetGeoTransform(target_ds.GetGeoTransform())
        # dst.SetProjection(srs.exportToWkt())
        dst.SetProjection(target_lyr.crs().toWkt())

        dst.GetRasterBand(1).WriteArray(np.asarray(target))
        dst.GetRasterBand(1).SetNoDataValue(nodata)

        # Properly close GDAL resources
        flow_ds = None
        target_ds = None
        dst = None

        return {self.OUTPUT: output}
