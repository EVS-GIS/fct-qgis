# Getting started

## Quick install

The latest stable release of the Fluvial Corridor Toolbox is now available from the official QGIS plugins repository. 

## Install the plugin from source (for development purpose)

### Create a virtualenv for the fct-qgis package

    python3 -m venv env --system-site-packages
    echo /usr/share/qgis/python/plugins > ./env/lib/python<version>/site-packages/qgis_plugins.pth

    source ./env/bin/activate
    python -m pip install -U pip
    python -m pip install -r requirements.txt
    python -m pip install --no-build-isolation -e .


### Using `doit`

On all platforms, you can install/update the plugin automatically with `doit` dependency.
The following command will install the plugin in your local plugin folder:

    python -m doit install

### Without `doit`

#### On Windows

On Windows, copy the directory `fct` to your local plugin folder,
and rename it to `FluvialCorridorToolbox`.

#### On Linux or Mac OS

On Linux or Mac OS, you can use the provided Makefile.

The following command will install the plugin in your local plugin folder :

    make

If needed, you can set `QGIS_USER_DIR`
to point to your local folder where QGis stores installed plugins.

	make QGIS_USER_DIR=/path/to/qgis/plugin/folder

On Linux, the default is `$(HOME)/.local/share/QGIS/QGIS3/profiles/default`.

### Building Cython Extensions

Cython extensions are built when you install fct-qgis. 

Alternatively, you can build and install the Cython extension for Terrain Analysis algorithms
with the following command :

    make extensions

Alternatively, you can cd into the `cython` directory and type :

	python3 setup.py install --install-platlib=/path/to/plugin/lib

where `/path/to/plugin` is the installation folder for the FCT plugin,
for example `$QGIS_USER_DIR/FluvialCorridorToolbox`.

*[FCT]: Fluvial Corridor Toolbox

### Testing algorithms

Unit tests can be run with pytest an pytest-cov packages : 

    pytest --cov=fct --cov-report json:test/reports/coverage.json test

