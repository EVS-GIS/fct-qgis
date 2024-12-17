# -*- coding: utf-8 -*-

"""
HubertTest

***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""


from ...algorithms.metrics.AggregateFeatures import AggregateFeatures

from ..metadata import AlgorithmMetadata

class HubertTest(AggregateFeatures):
    """
    Hubert test
    """

    METADATA = AlgorithmMetadata.read(__file__, 'HubertTest')
    
