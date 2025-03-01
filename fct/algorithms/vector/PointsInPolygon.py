import os

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtCore import QCoreApplication

from qgis.core import (QgsApplication,
                       QgsProcessingAlgorithm,
                       QgsGeometry,
                       QgsFeatureSink,
                       QgsFeatureRequest,
                       QgsFeature,
                       QgsField,
                       QgsProcessing,
                       QgsProcessingException,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterString,
                       QgsProcessingParameterField,
                       QgsSpatialIndex)

# from processing.algs.qgis.QgisAlgorithm import QgisAlgorithm

# pluginPath = os.path.split(os.path.split(os.path.dirname(__file__))[0])[0]


class PointsInPolygon(QgsProcessingAlgorithm):

    POLYGONS = 'POLYGONS'
    POINTS = 'POINTS'
    OUTPUT = 'OUTPUT'
    FIELD = 'FIELD'
    WEIGHT = 'WEIGHT'
    CLASSFIELD = 'CLASSFIELD'

    # def icon(self):
    #     return QgsApplication.getThemeIcon("/algorithms/mAlgorithmSumPoints.svg")

    # def svgIconPath(self):
    #     return QgsApplication.iconPath("/algorithms/mAlgorithmSumPoints.svg")

    def group(self):
        return self.tr('Tools for Vectors')

    def groupId(self):
        return 'vector'

    def initAlgorithm(self, config=None):

        self.addParameter(QgsProcessingParameterFeatureSource(self.POLYGONS,
                                                              self.tr('Polygons'), [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterFeatureSource(self.POINTS,
                                                              self.tr('Points'), [QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterField(self.WEIGHT,
                                                      self.tr('Weight field'), parentLayerParameterName=self.POINTS,
                                                      optional=True))
        self.addParameter(QgsProcessingParameterField(self.CLASSFIELD,
                                                      self.tr('Class field'), parentLayerParameterName=self.POINTS,
                                                      optional=True))
        self.addParameter(QgsProcessingParameterString(self.FIELD,
                                                       self.tr('Count field name'), defaultValue='NUMPOINTS'))
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr('Count'), QgsProcessing.TypeVectorPolygon))

    def name(self):
        return 'countpointsinpolygon'

    def displayName(self):
        return self.tr('Count points in polygon')

    def tr(self, string, context=''):
        
        if context == '':
            context = 'FluvialCorridorToolbox'

        return QCoreApplication.translate(context, string)

    def processAlgorithm(self, parameters, context, feedback):

        poly_source = self.parameterAsSource(parameters, self.POLYGONS, context)
        if poly_source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.POLYGONS))

        point_source = self.parameterAsSource(parameters, self.POINTS, context)
        if point_source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.POINTS))

        weight_field = self.parameterAsString(parameters, self.WEIGHT, context)
        weight_field_index = -1
        if weight_field:
            weight_field_index = point_source.fields().lookupField(weight_field)

        class_field = self.parameterAsString(parameters, self.CLASSFIELD, context)
        class_field_index = -1
        if class_field:
            class_field_index = point_source.fields().lookupField(class_field)

        field_name = self.parameterAsString(parameters, self.FIELD, context)

        fields = poly_source.fields()
        if fields.lookupField(field_name) < 0:
            fields.append(QgsField(field_name, QVariant.Int))
        field_index = fields.lookupField(field_name)

        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT, context,
                                               fields, poly_source.wkbType(), poly_source.sourceCrs())
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        spatialIndex = QgsSpatialIndex(point_source.getFeatures(
            QgsFeatureRequest().setSubsetOfAttributes([]).setDestinationCrs(poly_source.sourceCrs(), context.transformContext())), feedback)

        point_attribute_indices = []
        if weight_field_index >= 0:
            point_attribute_indices.append(weight_field_index)
        if class_field_index >= 0:
            point_attribute_indices.append(class_field_index)

        features = poly_source.getFeatures()
        total = 100.0 / poly_source.featureCount() if poly_source.featureCount() else 0
        for current, polygon_feature in enumerate(features):
            if feedback.isCanceled():
                raise QgsProcessingException(self.tr('Cancelled by user'))

            count = 0
            output_feature = QgsFeature()
            if polygon_feature.hasGeometry():
                geom = polygon_feature.geometry()
                engine = QgsGeometry.createGeometryEngine(geom.constGet())
                engine.prepareGeometry()

                count = 0
                classes = set()

                points = spatialIndex.intersects(geom.boundingBox())
                if len(points) > 0:
                    request = QgsFeatureRequest().setFilterFids(points).setDestinationCrs(poly_source.sourceCrs(), context.transformContext())
                    request.setSubsetOfAttributes(point_attribute_indices)
                    for point_feature in point_source.getFeatures(request):
                        if feedback.isCanceled():
                            raise QgsProcessingException(self.tr('Cancelled by user'))

                        if engine.contains(point_feature.geometry().constGet()):
                            if weight_field_index >= 0:
                                weight = point_feature.attributes()[weight_field_index]
                                try:
                                    count += float(weight)
                                except:
                                    # Ignore fields with non-numeric values
                                    pass
                            elif class_field_index >= 0:
                                point_class = point_feature.attributes()[class_field_index]
                                if point_class not in classes:
                                    classes.add(point_class)
                            else:
                                count += 1

                output_feature.setGeometry(geom)

            attrs = polygon_feature.attributes()

            if class_field_index >= 0:
                score = len(classes)
            else:
                score = count
            if field_index == len(attrs):
                attrs.append(score)
            else:
                attrs[field_index] = score
            output_feature.setAttributes(attrs)
            sink.addFeature(output_feature, QgsFeatureSink.FastInsert)

            feedback.setProgress(int(current * total))

        return {self.OUTPUT: dest_id}

    def createInstance(self):
        return type(self)()