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
import fiona

from scipy.ndimage import convolve

from qgis.core import (
    Qgis,
    QgsTask,
    QgsMessageLog,
)

from ...lib import terrain_analysis as ta
from ...utils.tiles import FctRasterTile
from ...utils.rasterize import rasterize_linestringz


class PrepareDEMTask(QgsTask):
        
    def __init__(self, dem_layer: FctRasterTile, network: str, output: FctRasterTile, output_labels: FctRasterTile, window_size: int, burn: int, exterior: float, overwrite: bool = False):
        
        super().__init__(f"Prepare DEM - ROW{dem_layer.row} COL{dem_layer.col}", QgsTask.CanCancel)
        self.dem_layer = dem_layer
        self.network = network
        self.output = output
        self.output_labels = output_labels
        self.window_size = window_size
        self.overwrite = overwrite
        self.burn = burn
        self.exterior = exterior
        self.output_graph = os.path.join(output.dataset.wd, 'WATERSHED_GRAPH', f'WATERSHED_GRAPH_{dem_layer.row}_{dem_layer.col}.npz')

        os.makedirs(os.path.dirname(self.output.file), exist_ok=True)
        os.makedirs(os.path.dirname(self.output_labels.file), exist_ok=True)
        os.makedirs(os.path.dirname(self.output_graph), exist_ok=True)

        self.setProgress(0)
    
    def run(self):

        if os.path.exists(self.output.file) and not self.overwrite:
            self.exception = Exception(f"Output file {self.output.file} already exists and overwrite is set to False.")
            self.setProgress(100)
            return False

        with rio.open(self.dem_layer.file) as ds:

            data = ds.read(1)
            nodata = ds.nodata
            data[data == ds.nodata] = np.nan
            profile = ds.profile.copy()

        # MEAN FILTER
        if self.window_size != 0:

            kernel = np.ones((self.window_size, self.window_size))
            data = convolve(data, kernel) / kernel.size 

        self.setProgress(15)

        # BURN
        if self.burn > 0:

            height, width = data.shape

            if os.path.exists(self.network):

                with fiona.open(self.network) as fs:
                    for feature in fs:

                        geom = np.array(feature['geometry']['coordinates'], dtype=np.float32)
                        geom[:, :2] = np.fliplr(ta.worldtopixel(geom, ds.transform, gdal=False))

                        for a, b in zip(geom[:-1], geom[1:]):
                            for px, py, z in rasterize_linestringz(a, b):
                                if all([py >= 0, py < height, px >= 0, px < width, not np.isinf(z)]):
                                    data[py, px] = z - self.burn

            else:
                QgsMessageLog(f'File not found: {self.network}')
        
        self.setProgress(30)

        # LABEL FLATS
        labels, graph = ta.watershed_labels(data, nodata, self.exterior)
        labels = np.uint32(labels)

        self.setProgress(75)

        # SAVE OUTPUT
        with rio.open(self.output.file, 'w', **profile) as dst:
            dst.write(data, 1)

        with rio.open(self.output_labels.file, 'w', **profile) as dst:
            dst.write(labels, 1)
        
        self.setProgress(85)
        
        np.savez(
            self.output_graph,
            z=np.array([
                data[0, :],
                data[:, -1],
                np.flip(data[-1, :], axis=0),
                np.flip(data[:, 0], axis=0)]),
            labels=np.array([
                labels[0, :],
                labels[:, -1],
                np.flip(labels[-1, :], axis=0),
                np.flip(labels[:, 0], axis=0)]),
            graph=np.array(list(graph.items()), dtype=object)
        )

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

