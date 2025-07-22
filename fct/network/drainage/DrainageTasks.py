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

from collections import defaultdict, Counter
from scipy.ndimage import convolve
from shapely.geometry import shape
from shapely.wkt import loads

from qgis.core import (
    Qgis,
    QgsTask,
    QgsMessageLog,
    QgsProcessingFeedback,
    QgsFeature
)

from ...utils.tiles import FctDataTile, FctTiledDataset, FctTileset


class PrepareDEMTask(QgsTask):
        
    def __init__(self, dem_layer: FctDataTile, output: FctDataTile, window_size: int, burn: int, overwrite: bool = False):
        
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


def DrapeNetworkAndAdjustElevations(dem: FctTiledDataset, networkfile: str, output: str, feedback: QgsProcessingFeedback):
    """
    Drape hydrography vectors on DEM
    and adjust elevation profile to ensure
    monotonic decreasing z across network.
    """

    networklayer = None
    if "|layername=" in networkfile:
        networkfile, networklayer = networkfile.split('|layername=')

    graph = defaultdict(list)
    indegree = Counter()
    features = list()

    feedback.setProgressText('Drape Stream Vectors on DEM')

    feedback.setProgress(0)
    with rio.open(dem.vrt) as ds:
        with fiona.open(networkfile, layer=networklayer) as fs:

            feature_count = len(fs)
            options = dict(driver=fs.driver, crs=fs.crs, schema=fs.schema)
                
            for i, feature in enumerate(fs):

                a = feature['properties']['NODEA']
                b = feature['properties']['NODEB']
                coordinates = np.array(feature['geometry']['coordinates'])

                z = np.array(list(ds.sample(coordinates[:, :2], 1)))
                coordinates[:, 2] = np.ravel(z)
                feature['geometry']['coordinates'] = coordinates
                
                idx = len(features)
                graph[a].append((b, idx))
                indegree[b] += 1
                features.append(feature)

                feedback.setProgress((i/feature_count)*100)

    feedback.setProgressText('Adjust Elevation Profile')

    nodez = defaultdict(lambda: float('inf'))
    queue = [node for node in graph if indegree[node] == 0]

    with fiona.open(output, 'w', **options) as fst:
        while queue:

            source = queue.pop(0)

            for node, idx in graph[source]:

                feature = features[idx]
                coordinates = feature['geometry']['coordinates']
                a = feature['properties']['NODEA']
                b = feature['properties']['NODEB']

                zmin = nodez[a]

                for k, z in enumerate(coordinates[:, 2]):
                            
                    if z != ds.nodata and z <= zmin:
                        zmin = z
                    
                    # Clamp z to upstream elevation
                    coordinates[k, 2] = zmin

                if not np.isinf(feature['geometry']['coordinates']).any():
                    fst.write(feature)

                nodez[b] = zmin
                indegree[node] -= 1

                if indegree[node] == 0:
                    queue.append(node)


def SplitStreamNetworkIntoTiles(networkfile: str, tileset: FctTileset, output_dir: str, feedback: QgsProcessingFeedback):

    feedback.setProgressText("Split network into tiles")
    feedback.setProgress(0)

    os.makedirs(output_dir, exist_ok=True)

    with fiona.open(networkfile) as fs:

        properties = fs.schema['properties'].copy()
        properties.update(
            ROW='int',
            COL='int'
        )

        schema = dict(
            geometry=fs.schema['geometry'],
            properties=properties)

        options = dict(driver=fs.driver, crs=fs.crs, schema=schema)

        ntiles = tileset.aux_tileset.featureCount()

        for i, t in enumerate(tileset.getTiles()):
            tile: QgsFeature = t[1]

            output = os.path.join(output_dir, f"DRAPED_{tile.attribute('ROW')}_{tile.attribute('COL')}.gpkg")
            with fiona.open(output, 'w', **options) as dst:

                tile_geom = loads(tile.geometry().boundingBox().asWktPolygon())
                bbox = (
                    tile.geometry().boundingBox().xMinimum(),
                    tile.geometry().boundingBox().yMinimum(),
                    tile.geometry().boundingBox().xMaximum(),
                    tile.geometry().boundingBox().yMaximum()
                )

                for feature in fs.filter(bbox=bbox):

                    intersection = shape(feature['geometry']).intersection(tile_geom)

                    if intersection.geom_type == 'LineString':

                        props = feature['properties']
                        props.update(ROW=tile.attribute('ROW'), COL=tile.attribute('COL'))
                        dst.write({
                            'geometry': intersection.__geo_interface__,
                            'properties': props
                        })

                    elif intersection.geom_type in ('MultiLineString', 'GeometryCollection'):

                        for geom in intersection.geoms:
                            if geom.geometryType() == 'LineString':

                                props = feature['properties']
                                props.update(ROW=tile.attribute('ROW'), COL=tile.attribute('COL'))
                                dst.write({
                                    'geometry': geom.__geo_interface__,
                                    'properties': props
                                })

            feedback.setProgress((i/ntiles)*100)