[![Build terrain analysis extension](https://github.com/EVS-GIS/fct-qgis/actions/workflows/build.yml/badge.svg)](https://github.com/EVS-GIS/fct-qgis/actions/workflows/build.yml)
[![Documentation](https://github.com/EVS-GIS/fct-qgis/actions/workflows/pages/pages-build-deployment/badge.svg)](https://github.com/EVS-GIS/fct-qgis/actions/workflows/pages/pages-build-deployment)
[![Release](https://github.com/EVS-GIS/fct-qgis/actions/workflows/release.yml/badge.svg?branch=master)](https://github.com/EVS-GIS/fct-qgis/actions/workflows/release.yml)

[![Ubuntu / QGIS 3.34](https://github.com/EVS-GIS/fct-qgis/actions/workflows/ubuntu-qgis334.yml/badge.svg)](https://github.com/EVS-GIS/fct-qgis/actions/workflows/ubuntu-qgis334.yml)
[![Ubuntu / QGIS 3.40](https://github.com/EVS-GIS/fct-qgis/actions/workflows/ubuntu-qgis340.yml/badge.svg)](https://github.com/EVS-GIS/fct-qgis/actions/workflows/ubuntu-qgis340.yml)

# Fluvial Corridor Toolbox

![Corridor Width Profile Example (River le Var, France)](https://github.com/tramebleue/fct-cli/blob/master/docs/img/width_profile.png)

The Fluvial Corridor Toolbox is a set of geoalgorithms intended to describe and measure fluvial features and processes.

Documentation (in progress) is available at : https://evs-gis.github.io/fct-qgis

If your are looking for the ArcGIS version of the toolbox,
please go to [Fluvial Corridor Toolbox for ArcGIS](https://github.com/EVS-GIS/Fluvial-Corridor-Toolbox-ArcGIS).

## Supported versions of QGis

This toolbox is maintained only for LTR versions of QGIS, but should work with all versions >= 3.34.

## Quick start

### Installation

The latest stable release of the Fluvial Corridor Toolbox is now available from the official QGIS plugins repository. 

### Usage

Most of the users will find all the tools they are looking for in the Fluvial Corridor Workflows, in the QGIS Processing panel. 

![The FCT Workflows in the QGIS toolbox](docs/img/fct_workflows.png)

The Fluvial Corridor Workflows are sets of algorithms from the Fluvial Corridor Toolbox prepared to math common users needs like calculating a Valley Bottom from a DEM, creating centerlines of polygons, disaggregate polygons or polylines and calculate metrics.

In the Fluvial Corridor Toolbox, you will find all the detailed algorithms used in the workflow, and many more!

## Acknowledgements

The toolbox is developed within the programme
[Trame bleue, espaces et continuités](https://www.tramebleue.fr/)
in collaboration with :

* [GeoPeka](http://www.geopeka.com)
* [UMR 5600 Environnement, ville et société](http://umr5600.cnrs.fr/fr/accueil/).

Funding and support have been kindly provided by :

* [European Union](http://www.europe-en-france.gouv.fr/Centre-de-ressources/Actualites/Le-FEDER-qu-est-ce-que-c-est)
  and [Région Auvergne-Rhône-Alpes](https://www.auvergnerhonealpes.fr/)
* [Association nationale pour la recherche technologique](http://www.anrt.asso.fr/fr)
* [Agence de l'eau Rhône-Méditerranée-Corse](https://www.eaurmc.fr/)

## License

The Fluvial Corridor Toolbox is released under the [GNU Public License][].

[GNU Public License]: https://github.com/EVS-GIS/fct-qgis/blob/master/LICENSE
