# -*- coding: utf-8 -*-

"""
FlowAccumulation

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
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer
)

from ..metadata import AlgorithmMetadata

class FlowDirection(AlgorithmMetadata, QgsProcessingAlgorithm):
    """
    Compute D8 Flow Direction from Digital Elevation Model
    """

    METADATA = AlgorithmMetadata.read(__file__, 'FlowDirection')

    ELEVATIONS = 'ELEVATIONS'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, configuration): 

        self.addParameter(QgsProcessingParameterRasterLayer(
            self.ELEVATIONS,
            self.tr('Digital Elevation Model')))

        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT,
            self.tr('Flow Direction')))

    def canExecute(self): 

        try:
            
            from ...lib.terrain_analysis import flowdir
            return True, ''
        except ImportError:
            return False, self.tr('Missing dependency: FCT terrain_analysis')

    def processAlgorithm(self, parameters, context, feedback): 

        
        from ...lib.terrain_analysis import flowdir

        elevations_lyr = self.parameterAsRasterLayer(parameters, self.ELEVATIONS, context)
        output = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        driver = gdal.GetDriverByName('GTiff')

        elevations_ds = gdal.Open(elevations_lyr.dataProvider().dataSourceUri())
        elevations = elevations_ds.GetRasterBand(1).ReadAsArray()
        nodata = elevations_ds.GetRasterBand(1).GetNoDataValue()

        if not nodata:
            feedback.reportError(self.tr('Nodata value should be set in the raster properties'), True)
            return {}
        
        flow = flowdir(elevations, nodata)

        if feedback.isCanceled():
            feedback.reportError(self.tr('Aborted'), True)
            return {}

        feedback.setProgress(50)
        feedback.pushInfo(self.tr('Write output ...'))

        dst = driver.Create(
            output,
            xsize=elevations_ds.RasterXSize,
            ysize=elevations_ds.RasterYSize,
            bands=1,
            eType=gdal.GDT_Int16,
            options=['TILED=YES', 'COMPRESS=DEFLATE'])

        dst.SetGeoTransform(elevations_ds.GetGeoTransform())
        dst.SetProjection(elevations_lyr.crs().toWkt())
        dst.GetRasterBand(1).WriteArray(flow)
        dst.GetRasterBand(1).SetNoDataValue(-1)

        feedback.setProgress(100)

        # Properly close GDAL resources
        elevations_ds = None
        dst = None

        return {self.OUTPUT: output}
