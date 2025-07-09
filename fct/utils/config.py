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

from processing.core.ProcessingConfig import ProcessingConfig

from qgis.core import (
    QgsProject,
)


def getFCTconfig():
    output_dir = os.path.join(
        ProcessingConfig.getSetting("FCN_TILES_DIR"),
        QgsProject.instance().baseName() or "tmp")
    tiles_size = int(ProcessingConfig.getSetting("FCN_TILES_SIZE"))
    keep_tiles = ProcessingConfig.getSetting("FCN_KEEP_TEMP_TILES")
    overwrite = not ProcessingConfig.getSetting("FCN_RESUME")

    return {
        'output_dir': output_dir,
        'tiles_size': tiles_size,
        'keep_tiles': keep_tiles,
        'overwrite': overwrite,
    }