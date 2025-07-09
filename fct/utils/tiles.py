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
import numpy as np
import rasterio as rio
import processing

from qgis.core import (
    Qgis,
    QgsProcessing,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProcessingFeedback,
    QgsTask,
    QgsApplication,
    QgsMessageLog, 
    QgsProcessingContext,
    QgsVectorFileWriter,
    QgsProject
)
from qgis.PyQt.QtCore import QMetaType


class ExtractTile(QgsTask):
    def __init__(self, datasource: QgsRasterLayer, tile: QgsFeature, output_dir: str, overwrite: bool = False, tileset_name: str = 'MAIN'):

        super().__init__("Extracting tile", QgsTask.CanCancel)
        self.datasource = datasource
        self.tile = tile
        self.output_dir = output_dir
        self.overwrite = overwrite
        self.tileset_name = tileset_name

        output_dir = os.path.join(self.output_dir, self.datasource.name())
        os.makedirs(output_dir, exist_ok=True)

        self.row = self.tile.attribute('ROW')
        self.col = self.tile.attribute('COL')
        self.output = os.path.join(output_dir, f"{self.datasource.name()}_{self.tileset_name}_{self.row}_{self.col}.tif")
        self.setProgress(0)
        

    def run(self):
        
        tile_geom = self.tile.geometry()

        if not self.overwrite and os.path.exists(self.output):
            self.exception = Exception(f"Output file {self.output} already exists and overwrite is set to False.")
            self.setProgress(100)
            return False
        
        with rio.open(self.datasource.dataProvider().dataSourceUri()) as ds:
            # Get the window for the tile geometry
            window = rio.windows.from_bounds(
                tile_geom.boundingBox().xMinimum(),
                tile_geom.boundingBox().yMinimum(),
                tile_geom.boundingBox().xMaximum(),
                tile_geom.boundingBox().yMaximum(),
                transform=ds.transform
            )
            
            # Read the data within the window
            flow = ds.read(1, window=window, boundless=True, fill_value=ds.nodata)
            self.setProgress(50)

        if np.all(flow == ds.nodata):
            self.exception = Exception(f"Tile {self.tile.attribute('ROW')}_{self.tile.attribute('COL')} contains only nodata values.")
            self.setProgress(100)
            return False
        
        height, width = flow.shape
        transform = ds.transform * ds.transform.translation(window.col_off, window.row_off)
        
        profile = ds.profile.copy()
        profile.update(
            driver='GTiff',
            height=height,
            width=width,
            transform=transform,
            compress='deflate'
        )

        # Write the extracted tile to a new file
        with rio.open(self.output, 'w', **profile) as dst:
            dst.write(flow, 1)

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


def MergeTiles(tiles: list[str], output: str, context: QgsProcessingContext = None , feedback: QgsProcessingFeedback = None, keep_tiles: bool = True) -> str:
    """
    Merges a list of raster tiles into a single raster file.

    :param tiles: list[str]
        List of file paths to the raster tiles to be merged.
    :param output: str
        File path for the output merged raster.
    :param feedback: QgsProcessingFeedback, optional
        Feedback object for reporting progress and messages.
    :return: str
        File path of the merged raster.
    """

    with rio.open(tiles[0]) as first_tile:
        nodata = first_tile.nodata

    if keep_tiles:
        vrt_output = output
    else:
        vrt_output = QgsProcessing.TEMPORARY_OUTPUT

    vrt = processing.run("gdal:buildvirtualraster",
                         {
                             'INPUT': tiles,
                             'RESAMPLING': 0,  # Nearest neighbor
                             'OUTPUT': vrt_output,
                             'SRC_NODATA': nodata,
                             "SEPARATE": False,
                         },
                        context=context,
                        feedback=feedback,
                        is_child_algorithm=True)
    
    if keep_tiles:
        return vrt['OUTPUT']
    
    else:
        tiff = processing.run("gdal:translate",
                                {
                                    'INPUT': vrt['OUTPUT'],
                                    'OUTPUT': output,
                                    'DATA_TYPE': 0,
                                    'COPY_SUBDATASETS': False,
                                },
                                context=context,
                                feedback=feedback,
                                is_child_algorithm=True)

        return tiff['OUTPUT']


def TileDataset(datasource: QgsRasterLayer, 
                tileset: tuple[str, QgsVectorLayer],
                directory: str = None,
                feedback: QgsProcessingFeedback=None,
                overwrite: bool = True) -> list[str]:

    feedback.pushInfo("Tiling dataset for multiprocessing...")

    tasks = list()

    for tile in tileset[1].getFeatures():
        task = ExtractTile(datasource=datasource, tile=tile, output_dir=directory, overwrite=overwrite, tileset_name=tileset[0])
        QgsApplication.taskManager().addTask(task)
        tasks.append(task)

    # Wait for all tasks to finish
    while any(task.progress() < 100 for task in tasks):
        if feedback.isCanceled():
            for task in tasks:
                task.cancel()
            feedback.pushInfo("Tiling process cancelled.")
            break

        # Count the number of finished tasks
        finished_tasks = sum(1 for task in tasks if task.progress() == 100)
        feedback.setProgress(int((finished_tasks / len(tasks)) * 100))

    output_tiles = [(tileset[0], t.row, t.col, t.output) for t in tasks if t.output and os.path.exists(t.output)]

    return output_tiles


def CreateTilesets(datasource: QgsRasterLayer, 
                  resolution: int = 10000,
                  output_dir: str = None,
                  overwrite: bool = True) -> tuple[tuple[str, QgsVectorLayer], tuple[str, QgsVectorLayer]]:
    """
    Creates two tilesets in GeoPackage format (.gpkg) with rectangular polygons that tile the bounding box of 
    the given datasource according to a resolution parameter. The first tileset contains polygons that are 
    aligned with the bounding box, whereas the second tileset contains polygons that are shifted by half the 
    resolution in both the x and y directions.

    :param datasource: str, default='bdalti'
        The name of the datasource as specified in the application's configuration file.
    :param resolution: float, default=10000
        The width and height of the rectangular polygons in the tilesets (in pixels).
    :return: tuple
        A tuple containing two QgsVectorLayer objects representing the main tileset and the auxiliary tileset
        respectively.
    """

    main_tileset_path = os.path.join(output_dir, 'main_tileset.gpkg') if output_dir else QgsProcessing.TEMPORARY_OUTPUT
    aux_tileset_path = os.path.join(output_dir, 'aux_tileset.gpkg') if output_dir else QgsProcessing.TEMPORARY_OUTPUT

    if not overwrite and os.path.exists(main_tileset_path) and os.path.exists(aux_tileset_path):
        QgsMessageLog.logMessage("Tilesets already exist and overwrite is set to False.", 'Fluvial Corridor Toolbox', Qgis.Warning)
        return (('MAIN', QgsVectorLayer(main_tileset_path, "main_tileset", 'ogr')), 
                ('AUX', QgsVectorLayer(aux_tileset_path, "aux_tileset", 'ogr')))

    resolution = datasource.rasterUnitsPerPixelX() * resolution

    schema = [QgsField('GID', QMetaType.Type.Int),
              QgsField('ROW', QMetaType.Type.Int),
              QgsField('COL', QMetaType.Type.Int),
              QgsField('X0', QMetaType.Type.Double),
              QgsField('Y0', QMetaType.Type.Double)]
    
    extent = datasource.dataProvider().extent()
    crs = datasource.crs()
    minx, miny, maxx, maxy = (
        extent.xMinimum(),
        extent.yMinimum(),
        extent.xMaximum(),
        extent.yMaximum()
    )
    
    # Tileset 1
    main_tileset = QgsVectorLayer('Polygon', "main_tileset", 'memory')
    main_tileset.setCrs(crs)
    main_tileset.dataProvider().addAttributes(schema)
    main_tileset.updateFields()
    
    minx -= (resolution)
    miny -= (resolution)
    
    maxx += (resolution)
    maxy += (resolution)
    
    gx, gy = np.arange(minx, maxx, resolution), np.arange(miny, maxy, resolution)

    gid = 1

    for i in range(len(gx)-1):
        for j in range(len(gy)-1):
            
            coordinates = [(gx[i],gy[j]),(gx[i],gy[j+1]),(gx[i+1],gy[j+1]),(gx[i+1],gy[j])]
            coordinates = [QgsPointXY(x, y) for x, y in coordinates]
            
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPolygonXY([coordinates]))
            feature.setAttributes([gid, len(gy)-j-1, i+1, gx[i], gy[j+1]])

            main_tileset.dataProvider().addFeature(feature)

            gid+=1
    
    main_tileset.updateExtents()
    main_tileset.commitChanges()
    
    # Tileset 2 (shifted)
    aux_tileset = QgsVectorLayer('Polygon', 'aux_tileset', 'memory')
    aux_tileset.setCrs(crs)
    aux_tileset.dataProvider().addAttributes(schema)
    aux_tileset.updateFields()
    
    minx -= (resolution/2)
    miny -= (resolution/2)

    maxx += (resolution/2)
    maxy += (resolution/2)
    
    gx, gy = np.arange(minx, maxx, resolution), np.arange(miny, maxy, resolution)

    gid = 1

    for i in range(len(gx)-1):
        for j in range(len(gy)-1):
            
            coordinates = [(gx[i],gy[j]),(gx[i],gy[j+1]),(gx[i+1],gy[j+1]),(gx[i+1],gy[j])]
            coordinates = [QgsPointXY(x, y) for x, y in coordinates]
            
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPolygonXY([coordinates]))
            feature.setAttributes([gid, len(gy)-j-1, i+1, gx[i], gy[j+1]])

            aux_tileset.dataProvider().addFeature(feature)

            gid+=1

    aux_tileset.updateExtents()

    QgsVectorFileWriter.writeAsVectorFormatV3(main_tileset, main_tileset_path, 
                                              main_tileset.transformContext(), 
                                              QgsVectorFileWriter.SaveVectorOptions())
    QgsVectorFileWriter.writeAsVectorFormatV3(aux_tileset, aux_tileset_path, 
                                              aux_tileset.transformContext(), 
                                              QgsVectorFileWriter.SaveVectorOptions())

    return (('MAIN', main_tileset), ('AUX', aux_tileset))
