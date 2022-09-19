# Tutorials

## From DEM to DGO

One of the main goals of the Fluvial Corridor Toolbox for QGIS is to produce a disaggregated valley bottom using a DEM and an hydrographic network polyline. This procedure has been simplified in the Fluvial Corridor Workflows included with the toolbox. 
Example data from french [IGN-F](https://geoservices.ign.fr/) is available in the tutorials directory. 

### Produce a valley bottom layer

To produce the valley bottom layer, you will need a DEM and an hydrographic network layer. The hydrographic network does not have to match perfectly the DEM, but it's better if it does. If you don't have an hydrographic network layer, it's possible to calculate it from the DEM. 

The accuracy of the resulting valley bottom depends on the resolution of your DEM. Make sure the z-coordinate accuracy is also sufficient to limit flat areas in wide valley bottoms.

In tutorials data, you will find an extract from the french IGN's BDAlti DEM at a resolution of 25m. This resolution is sufficient for the Romanche valley bottom, an alpine watercourse in a region with marked relief. You will also find a polyline of the Romanche river extracted from the french IGN's BDTopo. 

#### Prepare your layers

First, make sure your polyline type is single LineString and not MultiLineString. If not, you can use the [Aggregate Undirected Lines](../algorithms/hydrography/AggregateUndirectedLines/) algorithm or the QGIS ```Multipart to singleparts``` algorithm to fix it. 

With some DEM, you will also have to fill small depressions to avoid errors in flow direction calculation. To do it, use the [Fill Depressions](../algorithms/terrain/FillDepressions/) algorithm.

#### Calculate the valley bottom

Use the [Valley Bottom Workflow](../workflows/spatialcomponents/ValleyBottom/) to calculate the valley bottom.
The calculation of the valley bottom requires the prior calculation of the detrended DEM. This detrended DEM is saved in a temporary file if you use the [Valley Bottom Workflow](../workflows/spatialcomponents/ValleyBottom/). If you want to keep it in a raster layer, you should use the [Valley Bottom Algorithm](../algorithms/spatialcomponents/ValleyBottom/) instead.

You will have to choose between 3 detrending methods. Refer to the [Valley Bottom Workflow](../workflows/spatialcomponents/ValleyBottom/) documentation to decide which is better for you. The ```nearest``` method should be a good solution in most of the cases. 

In wide flat areas, if the resulting valley bottom is too narrow, try to increase the ```Large buffer size``` parameter. 

#### Refine valley bottom

To process the nexts steps, your valley bottom layer must respect the following conditions:

- Only one fully connected feature for each river. If there are deconnections in narrow valleys, try increasing the ```Maximum threshold value``` of the previous step. You can also merge polygons by manually drawing missing features. 
- No small polygons outside of the main polygon. If there are ones, try to increase the ```Aggregation distance``` of the previous step or remove them manually.
- A numeric field with an identifier to associate each network polyline with his valley bottom polygon. If there is no such field, create one. 

### Calculate the oriented centerline

You can directly calculate the DGOs using the network polyline but the result is better using the centerline (ie. medial axis) of the valley bottom. 
To calculate it, you will need a polyline that intersects the valley bottom polygon at least upstream and downstream. You can use the QGIS ```Extend Lines``` algorithm with the network polyline or just draw a dummy polyline that does the job. This polyline will never be used after. 

Run the [Oriented Centerline Workflow](../workflows/spatialcomponents/OrientedCenterline/) with your DEM, your refined valley bottom, and your polyline that instersect it. The result is a centerline which is oriented upstream to downstream. If you want to smooth it more, you can use the QGIS ```Simplify``` Douglas-Peucker algorithm, then the QGIS ```Smooth Geometry``` algorithm.

### Disaggregate the valley bottom along the centerline

Before carrying out the disaggregation, we advise to simplify the valley bottom polygon with the QGIS ```Simplify``` Douglas-Peucker algorithm. Disaggregating the raw valley bottom is possible, but will take a lot of time and resources. 

From now, you are ready to disaggregate the valley bottom in DGOs. Use the [Segmentation Workflow](../workflows/disaggregation/Segmentation/) to do it, using the valley bottom polygon as feature to segment and the oriented centerline. Choose the segmentation step (in map unit) you want for your DGOs size. 

