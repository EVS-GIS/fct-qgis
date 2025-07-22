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
import numpy as np
import rasterio as rio
import fiona
import processing

from shapely.geometry import shape
from shapely.wkt import loads

from collections import defaultdict, Counter
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterNumber,
    QgsApplication,
    QgsProcessingParameterField,
    QgsVectorLayer,
    QgsProcessingFeedback,
    QgsFeature
)

from .DrainageTasks import PrepareDEMTask
from ..metadata import AlgorithmMetadata
from ...utils.assertions import assertLayersCompatibility
from ...utils.tiles import FctTileset, FctTiledDataset
from ...utils.config import getFCTconfig
    
class PrepareDEM(AlgorithmMetadata, QgsProcessingAlgorithm):

    METADATA = AlgorithmMetadata.read(__file__, 'PrepareDEM')
    
    DEM = 'DEM'
    NETWORK = 'NETWORK'
    FROM_NODE_FIELD = 'FROM_NODE_FIELD'
    TO_NODE_FIELD = 'TO_NODE_FIELD'
    OUTPUT = 'OUTPUT'
    OUTPUT_LABELS = 'OUTPUT_LABELS'
    WINDOW = 'WINDOW'
    BURN = 'BURN'
    EXTERIOR = 'EXTERIOR'
    
    def initAlgorithm(self, configuration):

        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DEM,
            self.tr('Input elevation raster (DEM)'),
            [QgsProcessing.TypeRaster]))
        
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.NETWORK,
            self.tr('Stream network layer'),
            [QgsProcessing.TypeVectorLine]))

        self.addParameter(QgsProcessingParameterField(
            self.FROM_NODE_FIELD,
            self.tr('From Node Field'),
            parentLayerParameterName=self.NETWORK,
            type=QgsProcessingParameterField.Numeric,
            defaultValue='NODEA',
            optional=True))

        self.addParameter(QgsProcessingParameterField(
            self.TO_NODE_FIELD,
            self.tr('To Node Field'),
            parentLayerParameterName=self.NETWORK,
            type=QgsProcessingParameterField.Numeric,
            defaultValue='NODEB',
            optional=True))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.WINDOW,
            self.tr('Focal mean window size in pixels (0 = no focal mean filter)'),
            defaultValue=5,
            minValue=0))
    
        self.addParameter(QgsProcessingParameterNumber(
            self.BURN,
            self.tr('Deep of the stream burning in projection unit (0 = no stream burning)'),
            defaultValue=1.0,
            minValue=0))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.EXTERIOR,
            self.tr('Exterior height value (set high to force flow inside, low to force flow outside)'),
            defaultValue=9000.0))
        
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT,
            self.tr('Output prepared DEM')))
        
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT_LABELS,
            self.tr('Output watersheds labels')))

    def processAlgorithm(self, parameters, context, feedback): 

        with getFCTconfig() as config:

            assertLayersCompatibility([
                self.parameterAsRasterLayer(parameters, self.DEM, context),
                self.parameterAsVectorLayer(parameters, self.NETWORK, context)
            ], feedback, nodata_set=True, band_count=1)

            window_size = self.parameterAsInt(parameters, self.WINDOW, context)
            overlap = window_size * 2 if window_size != 0 else 10

            burn = self.parameterAsInt(parameters, self.BURN, context)
            exterior = self.parameterAsInt(parameters, self.EXTERIOR, context)

            # Open and tile DEM
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
                context=context,
                feedback=feedback, 
                overwrite=config['overwrite'])
            
            # Open network
            network = self.parameterAsVectorLayer(parameters, self.NETWORK, context)
            from_node_field = self.parameterAsString(parameters, self.FROM_NODE_FIELD, context)
            to_node_field = self.parameterAsString(parameters, self.TO_NODE_FIELD, context)


            network_processing = processing.run("native:multiparttosingleparts", 
                                                {
                                                    'INPUT': network,
                                                    'OUTPUT': os.path.join(config['output_dir'], 'RAW_HYDROGRAPHY.gpkg')
                                                }, context=context, feedback=feedback, is_child_algorithm=True)

            network = QgsVectorLayer(network_processing['OUTPUT'])

            if not from_node_field or not to_node_field:
                identifynodes = processing.run('fct:identifynetworknodes', {
                    'INPUT': self.parameterAsVectorLayer(parameters, self.INPUT, context),
                    'NODES': QgsProcessing.TEMPORARY_OUTPUT,
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }, context=context, feedback=feedback, is_child_algorithm=True)

                network = QgsVectorLayer(identifynodes['OUTPUT'])
                from_node_field = 'NODEA'
                to_node_field = 'NODEB'

            # Drape network
            draped_network = os.path.join(config['output_dir'], "DRAPED_HYDROGRAPHY.gpkg")
            DrapeNetworkAndAdjustElevations(dem=dem_tiled, networkfile=network.source(), output=draped_network, feedback=feedback)

            # Split network into tiles
            SplitStreamNetworkIntoTiles(networkfile=draped_network, 
                                        tileset=tileset, 
                                        output_dir=os.path.join(config['output_dir'], 'DRAPED'),
                                        feedback=feedback)

            feedback.setProgressText("Parallel processing of DEM tiles")

            tasks = list()
            output_dataset = FctTiledDataset("PrepareDEM", config['output_dir'], tileset)
            output_labels_dataset = FctTiledDataset("WatershedLabels", config['output_dir'], tileset)

            for tile in dem_tiled.getDataTiles():
                output_tile = output_dataset.appendTile(tile.row, tile.col)
                output_labels_tile = output_labels_dataset.appendTile(tile.row, tile.col)

                task = PrepareDEMTask(
                    dem_layer = tile, 
                    network = os.path.join(config['output_dir'], 'DRAPED', f'DRAPED_{tile.row}_{tile.col}.gpkg'),
                    output = output_tile, 
                    output_labels = output_labels_tile,
                    window_size = window_size, 
                    burn = burn,
                    exterior = exterior,
                    overwrite=config['overwrite']
                )
                
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


            result = output_dataset.mergeTiles(
                output=self.parameterAsOutputLayer(parameters, self.OUTPUT, context), 
                vrt=config['keep_tiles'],
                context=context,
                feedback=feedback
            )
                            
        return {self.OUTPUT: result}


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