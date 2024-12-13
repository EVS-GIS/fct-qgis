# -*- coding: utf-8 -*-

"""
AggregateLineSegmentsByCat - Merge continuous line segments into a single linestring

***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from collections import Counter, namedtuple

from qgis.PyQt.QtCore import ( 
    QVariant
)

from qgis.core import ( 
    QgsExpression,
    QgsGeometry,
    QgsLineString,
    QgsFeature,
    QgsFeatureRequest,
    QgsField,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingUtils,
    QgsProcessingException
)

import processing

from .graph import create_link_index
from ..metadata import AlgorithmMetadata
from ..util import asQgsFields, FidGenerator

Link = namedtuple('Link', ['a', 'b', 'feature_id'])

class AggregateStreamSegments(AlgorithmMetadata, QgsProcessingAlgorithm):
    """ Merge continuous line segments into a single linestring
    """

    METADATA = AlgorithmMetadata.read(__file__, 'AggregateStreamSegments')

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    CATEGORY_FIELD = 'CATEGORY_FIELD'
    FROM_NODE_FIELD = 'FROM_NODE_FIELD'
    TO_NODE_FIELD = 'TO_NODE_FIELD'
    COPY_FIELDS = 'COPY_FIELDS'

    def initAlgorithm(self, configuration): 

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT,
            self.tr('Input linestrings'),
            [QgsProcessing.TypeVectorLine]))

        self.addParameter(QgsProcessingParameterField(
            self.CATEGORY_FIELD,
            self.tr('Category Field'),
            parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Any,
            optional=True))

        self.addParameter(QgsProcessingParameterField(
            self.FROM_NODE_FIELD,
            self.tr('From Node Field'),
            parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric,
            defaultValue='NODEA',
            optional=True))

        self.addParameter(QgsProcessingParameterField(
            self.TO_NODE_FIELD,
            self.tr('To Node Field'),
            parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric,
            defaultValue='NODEB',
            optional=True))

        self.addParameter(QgsProcessingParameterField(
            self.COPY_FIELDS,
            self.tr('Fields To Copy'),
            parentLayerParameterName=self.INPUT,
            allowMultiple=True,
            type=QgsProcessingParameterField.Any))

        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT,
            self.tr('Aggregated Lines'),
            QgsProcessing.TypeVectorLine))

    def processAlgorithm(self, parameters, context, feedback): 

        layer = self.parameterAsSource(parameters, self.INPUT, context)
        category_field = self.parameterAsString(parameters, self.CATEGORY_FIELD, context)
        from_node_field = self.parameterAsString(parameters, self.FROM_NODE_FIELD, context)
        to_node_field = self.parameterAsString(parameters, self.TO_NODE_FIELD, context)
        copy_fields = self.parameterAsFields(parameters, self.COPY_FIELDS, context)

        if not from_node_field or not to_node_field:
            identifynodes = processing.run('fct:identifynetworknodes', {
                'INPUT': self.parameterAsVectorLayer(parameters, self.INPUT, context),
                'NODES': QgsProcessing.TEMPORARY_OUTPUT,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }, context=context, feedback=feedback, is_child_algorithm=True)

            layer = QgsProcessingUtils.variantToSource(identifynodes['OUTPUT'], context)
            from_node_field = 'NODEA'
            to_node_field = 'NODEB'

        feedback.pushInfo('%s' % copy_fields)

        if category_field:
            category_field_idx = layer.fields().lookupField(category_field)
            category_field_instance = layer.fields().at(category_field_idx)
        else:
            category_field_instance = QgsField('CATEGORY', QVariant.String, len=16)

        copy_fields_instances = []
        for copy_field in copy_fields:
            field_idx = layer.fields().lookupField(copy_field)
            copy_fields_instances.append(layer.fields().at(field_idx))

        fields = asQgsFields(
            QgsField('GID', type=QVariant.Int, len=10),
            QgsField('LENGTH', QVariant.Double),
            category_field_instance,
            QgsField(from_node_field, type=QVariant.Int, len=10),
            QgsField(to_node_field, type=QVariant.Int, len=10),
            *copy_fields_instances
        )

        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT, context,
                                               fields, layer.wkbType(), layer.sourceCrs())

        fid = FidGenerator()
        categories = Counter()

        def countCategories():
            """ List unique values in field `category_field`
                and count features by category
            """

            total = 100.0 / layer.featureCount() if layer.featureCount() else 0

            for current, feature in enumerate(layer.getFeatures()):

                if feedback.isCanceled():
                    raise QgsProcessingException(self.tr('Cancelled by user'))

                category = feature.attribute(category_field)
                categories[category] += 1

                feedback.setProgress(int(current * total))

        def processCategory(category=None):
            """ Aggregate segments of given category,
                or all segments if `category` is None
            """

            if feedback.isCanceled():
                return

            feedback.pushInfo(self.tr("Build node index ..."))

            adjacency = list()
            degree = Counter()

            if category is None:

                total = 100.0 / layer.featureCount() if layer.featureCount() else 0
                iterator = layer.getFeatures()

            else:

                total = 100.0 / categories[category]

                expression = QgsExpression('%s = %s' % (category_field, category))
                query = QgsFeatureRequest(expression)
                iterator = layer.getFeatures(query)

            for current, feature in enumerate(iterator):

                if feedback.isCanceled():
                    raise QgsProcessingException(self.tr('Cancelled by user'))

                from_node = feature.attribute(from_node_field)
                to_node = feature.attribute(to_node_field)
                adjacency.append(Link(from_node, to_node, feature.id()))
                degree[from_node] += 1
                degree[to_node] += 1

                # if measure_field:
                #     measure = feature.attribute(measure_field)
                # else:
                #     measure = 0.0

                feedback.setProgress(int(current * total))

            feedback.pushInfo(self.tr("Aggregate lines ..."))

            # Index links by upstream node
            downward_index = create_link_index(adjacency, lambda link: link.a)


            # Find source nodes
            process_stack = [link.a for link in adjacency if degree[link.a] == 1]

            current = 0
            seen_nodes = set()

            while process_stack:

                if feedback.isCanceled():
                    raise QgsProcessingException(self.tr('Cancelled by user'))

                from_node = process_stack.pop()
                if from_node in seen_nodes:
                    continue

                seen_nodes.add(from_node)

                for link in downward_index[from_node]:

                    segment = next(layer.getFeatures(QgsFeatureRequest(link.feature_id)))
                    copy_values = [segment.attribute(field) for field in copy_fields]
                    vertices = [v for v in segment.geometry().vertices()]

                    current = current + 1
                    feedback.setProgress(int(current * total))

                    while degree[link.b] == 2 and downward_index[link.b]:

                        next_link = downward_index[link.b][0]
                        segment = next(layer.getFeatures(QgsFeatureRequest(next_link.feature_id)))
                        vertices = vertices[:-1] + [v for v in segment.geometry().vertices()]

                        current = current + 1
                        feedback.setProgress(int(current * total))

                        link = next_link

                    feature = QgsFeature()
                    feature.setGeometry(QgsGeometry(QgsLineString(vertices)))
                    feature.setAttributes([
                        next(fid),
                        feature.geometry().length(),
                        category,
                        from_node,
                        link.b
                    ] + copy_values)
                    sink.addFeature(feature)

                    process_stack.append(link.b)


        if category_field:

            countCategories()

            for category in categories:
                processCategory(category)

        else:

            processCategory()

        feedback.pushInfo("Created %d line features" % fid.value)

        return {self.OUTPUT: dest_id}
