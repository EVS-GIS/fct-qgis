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

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterNumber,
    QgsApplication,
)  

from .DrainageTasks import MeanFilterTask
from ..metadata import AlgorithmMetadata
from ...utils.assertions import assertLayersCompatibility
from ...utils.tiles import CreateTilesets, TileDataset, MergeTiles
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
                self.parameterAsRasterLayer(parameters, self.DEM, context)
            ], feedback, nodata_set=True, band_count=1)

            dem_layer = self.parameterAsRasterLayer(parameters, self.DEM, context)
            tileset = CreateTilesets(dem_layer, resolution=config['tiles_size'], output_dir=config['output_dir'], overwrite=config['overwrite'])[0]
            
            tiles_list = TileDataset(dem_layer, tileset, directory=config['output_dir'], feedback=feedback, overwrite=config['overwrite'])

            # Mean filter (focal mean)
            feedback.pushInfo("Applying focal mean filter to DEM tiles...")

            tasks = list()

            ######
            ### MEAN FILTER

            window_size = self.parameterAsInt(parameters, self.WINDOW, context)
            if window_size != 0:
                for tile in tiles_list:
                    output = os.path.join(config['output_dir'], "MeanFilter", f"MeanFilter_{tile[0]}_{tile[1]}_{tile[2]}.tif")

                    task = MeanFilterTask(
                        dem_layer = tile[3], 
                        output = output, 
                        window_size = window_size, 
                        overwrite=config['overwrite']
                        )
                    
                    QgsApplication.taskManager().addTask(task)
                    tasks.append((tile[0], tile[1], tile[2], task))

                # Wait for all tasks to finish
                while any(task[3].progress() < 100 for task in tasks):
                    if feedback.isCanceled():
                        for task in tasks:
                            task[3].cancel()
                        feedback.pushInfo("Multiprocessing cancelled.")
                        break

                    # Count the number of finished tasks
                    finished_tasks = sum(1 for task in tasks if task[3].progress() == 100)
                    feedback.setProgress(int((finished_tasks / len(tasks)) * 100))

                tiles_list = [(t[0], t[1], t[2], t[3].output) for t in tasks if t[3].output and os.path.exists(t[3].output)]

            ######
            ### BURN

            if tiles_list:
                tiles_paths = [tile[3] for tile in tiles_list]

                feedback.pushInfo("Merging tiles for output...")
                result = MergeTiles(tiles_paths, self.parameterAsOutputLayer(parameters, self.OUTPUT, context), context=context, feedback=feedback, keep_tiles=config['keep_tiles'])
                            
        return {self.OUTPUT: result}
        