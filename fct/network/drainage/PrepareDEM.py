# -*- coding: utf-8 -*-

"""
Prepare DEM for Drainage Analysis

***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

import os
# import fiona
import numpy as np
import rasterio as rio

from collections import defaultdict, Counter
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterNumber,
    QgsApplication,
    QgsProcessingFeedback,
)  

# from shapely.geometry import (
#     asShape,
#     box
# )

from .DrainageTasks import PrepareDEMTask
from ..metadata import AlgorithmMetadata
from ...utils.assertions import assertLayersCompatibility
from ...utils.tiles import FctTileset, FctTiledDataset, FctDataTile
from ...utils.config import getFCTconfig
    
class PrepareDEM(AlgorithmMetadata, QgsProcessingAlgorithm):

    METADATA = AlgorithmMetadata.read(__file__, 'PrepareDEM')
    
    DEM = 'DEM'
    NETWORK = 'NETWORK'
    OUTPUT = 'OUTPUT'
    WINDOW = 'WINDOW'
    BURN = 'BURN'
    
    def initAlgorithm(self, configuration):

        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DEM,
            self.tr('Input elevation raster (DEM)'),
            [QgsProcessing.TypeRaster]))
        
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.NETWORK,
            self.tr('Stream network layer'),
            [QgsProcessing.TypeVectorLine]))

        self.addParameter(QgsProcessingParameterNumber(
            self.WINDOW,
            self.tr('Focal mean window size in pixels (0 = no focal mean filter)'),
            defaultValue=5,
            minValue=0))
    
        self.addParameter(QgsProcessingParameterNumber(
            self.BURN,
            self.tr('Deep of the stream burning in projection unit (0 = no stream burning)'),
            defaultValue=1,
            minValue=0))
        
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT,
            self.tr('Output smoothed elevation raster')))

    def processAlgorithm(self, parameters, context, feedback): 

        with getFCTconfig() as config:

            assertLayersCompatibility([
                self.parameterAsRasterLayer(parameters, self.DEM, context),
                self.parameterAsVectorLayer(parameters, self.NETWORK, context)
            ], feedback, nodata_set=True, band_count=1)

            window_size = self.parameterAsInt(parameters, self.WINDOW, context)
            overlap = window_size * 2 if window_size != 0 else 10

            dem_layer = self.parameterAsRasterLayer(parameters, self.DEM, context)
            tileset = FctTileset(dem_layer, 
                                 resolution=config['tiles_size'], 
                                 output_dir=config['output_dir'], 
                                 overlap=overlap, 
                                 overwrite=config['overwrite'])
            
            dem_tiled = FctTiledDataset("DEM", config['output_dir'])
            dem_tiled.fromDatasource(
                datasource=dem_layer, 
                tileset=tileset, 
                feedback=feedback, 
                overwrite=config['overwrite'])


            feedback.pushInfo("Processing DEM tiles...")

            tasks = list()
            output_dataset = FctTiledDataset("PrepareDEM", config['output_dir'], tileset)

            for tile in dem_tiled.getDataTiles():
                output_tile = output_dataset.appendTile(tile.row, tile.col)

                task = PrepareDEMTask(
                    dem_layer = tile, 
                    output = output_tile, 
                    window_size = window_size, 
                    overwrite=config['overwrite']
                )
                
                QgsApplication.taskManager().addTask(task)
                tasks.append(task)

            # Wait for all tasks to finish
            while any(task.progress() < 100 for task in tasks):
                if feedback.isCanceled():
                    for task in tasks:
                        task.cancel()
                    feedback.pushInfo("Multiprocessing cancelled.")
                    break

                # Count the number of finished tasks
                finished_tasks = sum(1 for task in tasks if task.progress() == 100)
                feedback.setProgress(int((finished_tasks / len(tasks)) * 100))


            result = output_dataset.mergeTiles(
                output=self.parameterAsOutputLayer(parameters, self.OUTPUT, context), 
                vrt=config['keep_tiles'],
                context=context,
                feedback=feedback
            )
                            
        return {self.OUTPUT: result}

