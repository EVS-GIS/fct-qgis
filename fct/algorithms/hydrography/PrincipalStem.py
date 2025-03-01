# -*- coding: utf-8 -*-

"""
Export Main Drain

***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from collections import defaultdict

from qgis.core import ( 
    QgsFeatureRequest,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingException,
)

from ..metadata import AlgorithmMetadata

class PrincipalStem(AlgorithmMetadata, QgsProcessingAlgorithm):
    """
    Filter stream network with multiple flow path
    in order to retain only the principal stem.
    """

    METADATA = AlgorithmMetadata.read(__file__, 'PrincipalStem')

    INPUT = 'INPUT'
    FROM_NODE_FIELD = 'FROM_NODE_FIELD'
    TO_NODE_FIELD = 'TO_NODE_FIELD'
    COST = 'COST'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, configuration): 

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT,
            self.tr('Stream network (polylines)'),
            [QgsProcessing.TypeVectorLine]))

        self.addParameter(QgsProcessingParameterField(
            self.FROM_NODE_FIELD,
            self.tr('From Node Field'),
            parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric,
            defaultValue='NODEA'))

        self.addParameter(QgsProcessingParameterField(
            self.TO_NODE_FIELD,
            self.tr('To Node Field'),
            parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric,
            defaultValue='NODEB'))

        self.addParameter(QgsProcessingParameterField(
            self.COST,
            self.tr('Traversal Cost Field'),
            parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric,
            defaultValue='COST'))

        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT,
            self.tr('Principal Stem'),
            QgsProcessing.TypeVectorLine))


    def processAlgorithm(self, parameters, context, feedback): 

        layer = self.parameterAsSource(parameters, self.INPUT, context)
        from_node_field = self.parameterAsString(parameters, self.FROM_NODE_FIELD, context)
        to_node_field = self.parameterAsString(parameters, self.TO_NODE_FIELD, context)
        cost_field = self.parameterAsString(parameters, self.COST, context)

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            layer.fields(),
            layer.wkbType(),
            layer.sourceCrs())

        feedback.setProgressText(self.tr('Build Upward Index ...'))

        # forwardtracks = { nb: list(segment, na, cost) }
        forwardtracks = defaultdict(list)
        total = 100.0 / layer.featureCount() if layer.featureCount() else 0
        anodes = set()

        for current, feature in enumerate(layer.getFeatures()):

            # toi = feature.attribute('TOI')
            # if toi == 0:
            #     continue

            a = feature.attribute(from_node_field)
            b = feature.attribute(to_node_field)
            cost = feature.attribute(cost_field)

            forwardtracks[b].append((feature.id(), a, cost))
            anodes.add(a)

            feedback.setProgress(int(current * total))

        feedback.setProgressText(self.tr('Walk up from Outlets to Sources ...'))

        # backtracks = { ba: segment, nb, cost }
        backtracks = dict()
        sources = list()
        stack = list(set(forwardtracks.keys()) - anodes)
        del anodes

        while stack:

            if feedback.isCanceled():
                raise QgsProcessingException(self.tr('Cancelled by user'))

            nb = stack.pop()

            if nb in backtracks:
                sb, nbb, cost = backtracks[nb]
            else:
                cost = 0.0

            for segment, na, step_cost in forwardtracks[nb]:

                new_cost = cost + step_cost

                if na in backtracks:

                    sa, nba, costa = backtracks[na]
                    if new_cost < costa:
                        backtracks[na] = (segment, nb, new_cost)

                else:

                    backtracks[na] = (segment, nb, new_cost)

                    if na in forwardtracks:
                        stack.append(na)
                    else:
                        sources.append(na)

        feedback.setProgressText(self.tr('Select main drain ...'))

        current = 0
        segments = set()

        for source in sources:

            if feedback.isCanceled():
                raise QgsProcessingException(self.tr('Cancelled by user'))

            na = source

            while na in backtracks:

                if feedback.isCanceled():
                    raise QgsProcessingException(self.tr('Cancelled by user'))

                segment, nb, cost = backtracks[na]

                if segment not in segments:

                    # feature = network.getFeatures(QgsFeatureRequest(segment)).next()
                    segments.add(segment)

                    current = current + 1
                    feedback.setProgress(int(current * total))

                na = nb

        feedback.setProgressText(self.tr('Export selected features ...'))

        request = QgsFeatureRequest().setFilterFids([fid for fid in segments])
        total = 100.0 / len(segments) if segments else 0

        for current, feature in enumerate(layer.getFeatures(request)):

            sink.addFeature(feature)
            feedback.setProgress(int(current*total))

        return {
            self.OUTPUT: dest_id
        }
