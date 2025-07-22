# coding: utf-8

"""
DOCME

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
import rasterio as rio
import numpy as np

from scipy.ndimage import convolve

from qgis.core import (
    Qgis,
    QgsTask,
    QgsMessageLog
)

from ...utils.tiles import FctTiledDataset, FctDataTile


class PrepareDEMTask(QgsTask):
        
    def __init__(self, dem_layer: FctDataTile, output: FctDataTile, window_size: int, overwrite: bool = False):
        
        super().__init__("Extracting tile", QgsTask.CanCancel)
        self.dem_layer = dem_layer
        self.output = output
        self.window_size = window_size
        self.overwrite = overwrite

        os.makedirs(os.path.dirname(self.output.file), exist_ok=True)
        self.setProgress(0)
    
    def run(self):

        if os.path.exists(self.output.file) and not self.overwrite:
            self.exception = Exception(f"Output file {self.output.file} already exists and overwrite is set to False.")
            self.setProgress(100)
            return False
        
        with rio.open(self.dem_layer.file) as ds:

            data = ds.read(1)
            data[data == ds.nodata] = np.nan
            kernel = np.ones((self.window_size, self.window_size))
            out = convolve(data, kernel) / kernel.size
            profile = ds.profile.copy()
            self.setProgress(50)

        with rio.open(self.output.file, 'w', **profile) as dst:
            dst.write(out, 1)
            self.setProgress(100)

        return True
    

    def finished(self, result):
        
        if not result:
            if self.exception:
                QgsMessageLog.logMessage(f'Task "{self.description}" Exception: {self.exception}', 'Fluvial Corridor Toolbox', Qgis.Warning)
            else:
                QgsMessageLog.logMessage(f'Task "{self.description}" failed.', 'Fluvial Corridor Toolbox', Qgis.Critical)
    

    def cancel(self):
        QgsMessageLog.logMessage(f'Task "{self.description}" cancelled', 'Fluvial Corridor Toolbox', Qgis.Info)
        super().cancel()

