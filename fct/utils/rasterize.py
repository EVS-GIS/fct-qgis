# coding: utf-8

"""
LineString Rasterization

***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

import math
import numpy as np

def rasterize_linestring(a, b):
    """
    Returns projected segment
    as a sequence of (px, py) coordinates.

    See https://en.wikipedia.org/wiki/Bresenham%27s_line_algorithm

    Parameters
    ----------

    a, b: vector of coordinate pair
        end points of segment [AB]

    Returns
    -------

    Generator of (x, y, z) coordinates
    corresponding to the intersection of raster cells with segment [AB],
    yielding one data point per intersected cell.
    """

    x = float(a[0])
    y = float(a[1])

    dx = abs(b[0] - a[0])
    dy = abs(b[1] - a[1])
    

    if dx > 0 or dy > 0:

        if dx > dy:
            count = dx
            dx = 1.0
            dy = dy / count
        else:
            count = dy
            dy = 1.0
            dx = dx / count

        if a[0] > b[0]:
            dx = -dx
        if a[1] > b[1]:
            dy = -dy

        # click.secho('Count (float) = %f' % count)
        # click.secho('Count (int) = %d' % math.ceil(count))

        for i in range(math.ceil(count)):

            if i > count:
                break

            yield int(round(x)), int(round(y))

            x = x + dx
            y = y + dy

    else:

        yield int(round(x)), int(round(y))

def rasterize_linestring_with_s(a, b):
    """
    Returns projected segment
    as a sequence of (px, py) coordinates.

    See https://en.wikipedia.org/wiki/Bresenham%27s_line_algorithm

    Parameters
    ----------

    a, b: vector of coordinate pair
        end points of segment [AB]

    Returns
    -------

    Generator of (x, y, z) coordinates
    corresponding to the intersection of raster cells with segment [AB],
    yielding one data point per intersected cell.
    """

    x = float(a[0])
    y = float(a[1])

    dx = abs(b[0] - a[0])
    dy = abs(b[1] - a[1])
    

    if dx > 0 or dy > 0:

        if dx > dy:
            count = dx
            dx = 1.0
            dy = dy / count
        else:
            count = dy
            dy = 1.0
            dx = dx / count

        if a[0] > b[0]:
            dx = -dx
        if a[1] > b[1]:
            dy = -dy

        # click.secho('Count (float) = %f' % count)
        # click.secho('Count (int) = %d' % math.ceil(count))

        for i in range(math.ceil(count)):

            if i > count:
                break

            yield int(round(x)), int(round(y)), float(i/count)

            x = x + dx
            y = y + dy

    else:

        yield int(round(x)), int(round(y)), 0.0

def rasterize_linestringz(a, b):
    """
    Returns projected segment
    as a sequence of (px, py) coordinates.

    See https://en.wikipedia.org/wiki/Bresenham%27s_line_algorithm

    Parameters
    ----------

    a, b: vector of coordinate pair
        end points of segment [AB]

    Returns
    -------

    Generator of (x, y, z) coordinates
    corresponding to the intersection of raster cells with segment [AB],
    yielding one data point per intersected cell.
    """

    az = a[2]
    bz = b[2]
    x = float(a[0])
    y = float(a[1])
    z = float(az)

    dx = abs(b[0] - a[0])
    dy = abs(b[1] - a[1])
    
    if np.isinf(az) or np.isinf(bz):
        dz = 0
    else:
        dz = float(bz - az)

    if dx > 0 or dy > 0:

        if dx > dy:
            count = dx
            dx = 1.0
            dy = dy / count
            dz = dz / count
        else:
            count = dy
            dy = 1.0
            dx = dx / count
            dz = dz / count

        if a[0] > b[0]:
            dx = -dx
        if a[1] > b[1]:
            dy = -dy

        # click.secho('Count (float) = %f' % count)
        # click.secho('Count (int) = %d' % math.ceil(count))

        for i in range(math.ceil(count)):

            if i > count:
                break

            yield int(round(x)), int(round(y)), z

            x = x + dx
            y = y + dy
            if dz != 0:
                z = z + dz

    else:

        yield int(round(x)), int(round(y)), z
