from setuptools import setup, find_packages
from distutils.extension import Extension
import numpy
from Cython.Build import cythonize


extensions = [

    Extension(
        'fct.lib.terrain_analysis',
        ['cython/terrain/terrain_analysis.pyx'],
        language='c++',
        include_dirs=[numpy.get_include()]
    )

]

setup(
    name='fct-qgis',
    version='1.1.0',
    packages=find_packages(),
    ext_modules=cythonize(extensions),
    include_package_data=True,
    install_requires=[
        'Click>=7.0',
        'numpy>=1.26',
        'scipy>=1.11',
        'plotly>=3.3',
        'pytest>=8.3',
    ],
    entry_points='''
[console_scripts]
autodoc=fct.cli.autodoc:autodoc
fct=fct.cli.algorithms:fct
fcw=fct.cli.algorithms:workflows
    ''',
)
