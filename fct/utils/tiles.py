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

from pathlib import Path
from rasterio.merge import merge

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
    QgsVectorFileWriter,
    QgsProcessingContext
)
from qgis.PyQt.QtCore import QMetaType


class FctTileset():

    def __init__(self,
                 datasource: QgsRasterLayer, 
                 resolution: int = 10000,
                 output_dir: str = None,
                 overlap: int = 0,
                 overwrite: bool = True):
        
        self.resolution = resolution
        self.overlap = overlap
        self.tile_size = resolution + 2*overlap

        self.main_tileset_path = os.path.join(output_dir, 'main_tileset.gpkg') if output_dir else QgsProcessing.TEMPORARY_OUTPUT
        self.aux_tileset_path = os.path.join(output_dir, 'aux_tileset.gpkg') if output_dir else QgsProcessing.TEMPORARY_OUTPUT

        if not overwrite and os.path.exists(self.main_tileset_path) and os.path.exists(self.aux_tileset_path):
            QgsMessageLog.logMessage("Tilesets already exist and overwrite is set to False.", 'Fluvial Corridor Toolbox', Qgis.Warning)
            return

        resolution = datasource.rasterUnitsPerPixelX() * resolution
        overlap = datasource.rasterUnitsPerPixelX() * overlap

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
        
        main_tileset = QgsVectorLayer('Polygon', "main_tileset", 'memory')
        main_tileset.setCrs(crs)
        main_tileset.dataProvider().addAttributes(schema)
        main_tileset.updateFields()

        aux_tileset = QgsVectorLayer('Polygon', 'aux_tileset', 'memory')
        aux_tileset.setCrs(crs)
        aux_tileset.dataProvider().addAttributes(schema)
        aux_tileset.updateFields()
        
        minx -= (resolution)
        miny -= (resolution)
        
        maxx += (resolution)
        maxy += (resolution)
        
        gx, gy = np.arange(minx, maxx, resolution), np.arange(miny, maxy, resolution)

        gid = 1

        for i in range(len(gx)-1):
            for j in range(len(gy)-1):

                aux_minx, main_minx = gx[i]-overlap, gx[i]
                aux_maxx, main_maxx = gx[i+1]+overlap, gx[i+1]
                aux_miny, main_miny = gy[j]-overlap, gy[j]
                aux_maxy, main_maxy = gy[j+1]+overlap, gy[j+1]
                
                main_coordinates = [(main_minx,main_miny),(main_minx,main_maxy),(main_maxx,main_maxy),(main_maxx,main_miny)]
                main_coordinates = [QgsPointXY(x, y) for x, y in main_coordinates]

                aux_coordinates = [(aux_minx,aux_miny),(aux_minx,aux_maxy),(aux_maxx,aux_maxy),(aux_maxx,aux_miny)]
                aux_coordinates = [QgsPointXY(x, y) for x, y in aux_coordinates]
                
                main_feature = QgsFeature()
                main_feature.setGeometry(QgsGeometry.fromPolygonXY([main_coordinates]))
                main_feature.setAttributes([gid, len(gy)-j-1, i+1, main_minx, main_maxy])
                main_tileset.dataProvider().addFeature(main_feature)

                aux_feature = QgsFeature()
                aux_feature.setGeometry(QgsGeometry.fromPolygonXY([aux_coordinates]))
                aux_feature.setAttributes([gid, len(gy)-j-1, i+1, aux_minx, aux_maxy])
                aux_tileset.dataProvider().addFeature(aux_feature)

                gid+=1
        
        main_tileset.updateExtents()
        main_tileset.commitChanges()
        QgsVectorFileWriter.writeAsVectorFormatV3(main_tileset, self.main_tileset_path, 
                                                main_tileset.transformContext(), 
                                                QgsVectorFileWriter.SaveVectorOptions())
        
        aux_tileset.updateExtents()
        aux_tileset.commitChanges()
        QgsVectorFileWriter.writeAsVectorFormatV3(aux_tileset, self.aux_tileset_path, 
                                                aux_tileset.transformContext(), 
                                                QgsVectorFileWriter.SaveVectorOptions())
        
        self.main_tileset = main_tileset
        self.aux_tileset = aux_tileset


    def getTiles(self):
        for main, aux in zip(self.main_tileset.getFeatures(), self.aux_tileset.getFeatures()):

            assert main.attribute('ROW') == aux.attribute('ROW')
            assert main.attribute('COL') == aux.attribute('COL')

            yield (main, aux)


    def getTileFromIndex(self, row: int, col: int):
        
        self.main_tileset.selectByExpression(f"ROW={row} AND COL={col}")
        self.aux_tileset.selectByExpression(f"ROW={row} AND COL={col}")

        return (self.main_tileset.selectedFeatures()[0], self.aux_tileset.selectedFeatures()[0])
    

class FctTiledDataset():

    def __init__(self, name: str, working_directory: str, tileset: FctTileset = None):

        self.name = name
        self.wd = working_directory
        self.directory = os.path.join(working_directory, name)
        self.tileset = tileset
        self.vrt: str = None
        self.tindex = list()

        os.makedirs(self.directory, exist_ok=True)


    def fromDatasource(self, 
                       datasource: QgsRasterLayer, 
                       tileset: FctTileset,
                       context: QgsProcessingContext=None,
                       feedback: QgsProcessingFeedback=None,
                       overwrite: bool = True):
        """
        Tile an input datasource (GeoTIFF or VRT) and update the FctTiledDataset object
        """

        feedback.setProgressText("Tiling dataset for multiprocessing")

        self.tileset = tileset

        tasks = list()
        for tile in tileset.getTiles():
            datatile = FctRasterTile(self, tile[0].attribute("ROW"), tile[0].attribute("COL"))
            task = ExtractTile(datasource=datasource, tile=datatile, overwrite=overwrite)
            QgsApplication.taskManager().addTask(task)
            tasks.append(task)

        # Wait for all tasks to finish
        while any(task.progress() < 100 for task in tasks):
            if feedback.isCanceled():
                for task in tasks:
                    task.cancel()
                feedback.pushInfo("Multiprocessing cancelled")
                break

            # Count the number of finished tasks
            finished_tasks = sum(1 for task in tasks if task.progress() == 100)
            feedback.setProgress(int((finished_tasks / len(tasks)) * 100))

        self.tindex: list[FctRasterTile] = [t.output for t in tasks if t.output and os.path.exists(t.output.file)]

        self.mergeTiles(output = os.path.join(self.wd, f"{self.name}.vrt"), 
                        vrt = True,
                        context=context,
                        feedback=feedback)


    def appendTile(self, row: int, col: int):
        tile = FctRasterTile(self, row, col)
        self.tindex.append(tile)

        return tile


    def getDataTiles(self):
        for tile in self.tindex:
            yield tile


    # def buildVRT(self, context, feedback):

    #     vrt_path = os.path.join(Path(os.path.dirname(self.directory)).parent, f"{self.name}.vrt")
    #     tlist = [t.file for t in self.tindex]

    #     with rio.open(self.tindex[0].file) as first_tile:
    #         nodata = first_tile.nodata

    #     vrt = processing.run("gdal:buildvirtualraster",
    #                         {
    #                             'INPUT': tlist,
    #                             'RESAMPLING': 0,  # Nearest neighbor
    #                             'OUTPUT': vrt_path,
    #                             'SRC_NODATA': nodata,
    #                             "SEPARATE": False,
    #                         },
    #                         context=context,
    #                         feedback=feedback,
    #                         is_child_algorithm=True)

    #     self.vrt = vrt['OUTPUT']


    def mergeTiles(self,
                   output: str, 
                   context: QgsProcessingContext,
                   feedback: QgsProcessingFeedback,
                   vrt: bool = False) -> str:
        
        
        feedback.setProgressText("Crop output overlapping tiles")

        output_tiles_dir = os.path.join(self.wd, "OUTPUT")
        os.makedirs(output_tiles_dir, exist_ok=True)

        tasks = list()
        for tile in self.getDataTiles():
            task = CropTile(tile=tile, output_dir=output_tiles_dir)
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

        feedback.setProgressText("Merging output tiles")
        
        if vrt:
            output_tiles = [t.output for t in tasks]
            with rio.open(self.tindex[0].file) as first_tile:
                nodata = first_tile.nodata

            vrt_processing = processing.run("gdal:buildvirtualraster",
                                            {
                                                'INPUT': output_tiles,
                                                'RESAMPLING': 0,  # Nearest neighbor
                                                'OUTPUT': output,
                                                'SRC_NODATA': nodata,
                                                "SEPARATE": False,
                                            },
                                            context=context,
                                            feedback=feedback,
                                            is_child_algorithm=True)
            
            self.vrt = vrt_processing['OUTPUT']
            return self.vrt

        else:
            output_tiles = [rio.open(t.output) for t in tasks]

            merge(output_tiles, dst_path=output)

            for t in output_tiles:
                t.close()

            return output
    

class FctRasterTile():

    def __init__(self, dataset: FctTiledDataset, row: int, col: int):
        
        self.dataset = dataset
        self.row = row
        self.col = col

        self.file = os.path.join(self.dataset.directory, f"{self.dataset.name}_{self.row}_{self.col}.tif")
        self.features = self.dataset.tileset.getTileFromIndex(self.row, self.col)

        
class ExtractTile(QgsTask):
    def __init__(self, datasource: QgsRasterLayer, tile: FctRasterTile, overwrite: bool = False):

        super().__init__(f"Extract tile - ROW{tile.row} COL{tile.col}", QgsTask.CanCancel)
        self.datasource = datasource
        self.tile = tile
        # self.name = self.tile.dataset.name
        # self.output_dir = output_dir
        self.overwrite = overwrite

        self.row = self.tile.row
        self.col = self.tile.col
        self.output = tile
        self.setProgress(0)
        

    def run(self):

        if not self.overwrite and os.path.exists(self.output):
            self.exception = Exception(f"Output file {self.output} already exists and overwrite is set to False.")
            self.setProgress(100)
            return False
        
        main_tile_geom = self.tile.features[0].geometry()
        aux_tile_geom = self.tile.features[1].geometry()
        
        with rio.open(self.datasource.dataProvider().dataSourceUri()) as ds:
            # Get the window for the main tile geometry
            window = rio.windows.from_bounds(
                main_tile_geom.boundingBox().xMinimum(),
                main_tile_geom.boundingBox().yMinimum(),
                main_tile_geom.boundingBox().xMaximum(),
                main_tile_geom.boundingBox().yMaximum(),
                transform=ds.transform
            )
            
            # Read the data within the window
            flow = ds.read(1, window=window, boundless=True, fill_value=ds.nodata)

            if np.all(flow == ds.nodata):
                self.exception = Exception(f"Tile {self.row}_{self.col} contains only nodata values.")
                self.setProgress(100)
                return False
            else:
                # Get the window for the aux tile geometry
                window = rio.windows.from_bounds(
                    aux_tile_geom.boundingBox().xMinimum(),
                    aux_tile_geom.boundingBox().yMinimum(),
                    aux_tile_geom.boundingBox().xMaximum(),
                    aux_tile_geom.boundingBox().yMaximum(),
                    transform=ds.transform
                )
                
                # Read the data within the window
                flow = ds.read(1, window=window, boundless=True, fill_value=ds.nodata)
                self.setProgress(50)

        
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
        with rio.open(self.output.file, 'w', **profile) as dst:
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


class CropTile(QgsTask):
    def __init__(self, tile: FctRasterTile, output_dir: str):

        super().__init__("Extracting tile", QgsTask.CanCancel)
        self.tile = tile
        self.output_dir = output_dir
        self.output = os.path.join(self.output_dir, f"{self.tile.dataset.name}_{self.tile.row}_{self.tile.col}.tif")

        self.setProgress(0)
        os.makedirs(output_dir, exist_ok=True)
        

    def run(self):

        main_tile, _ = self.tile.features

        with rio.open(self.tile.file) as src:
            window = rio.windows.from_bounds(
                main_tile.geometry().boundingBox().xMinimum(),
                main_tile.geometry().boundingBox().yMinimum(),
                main_tile.geometry().boundingBox().xMaximum(),
                main_tile.geometry().boundingBox().yMaximum(),
                transform=src.transform
            )

            flow = src.read(1, window=window, boundless=True, fill_value=src.nodata)

        self.setProgress(50)

        height, width = flow.shape
        transform = src.transform * src.transform.translation(window.col_off, window.row_off)
        
        profile = src.profile.copy()
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

