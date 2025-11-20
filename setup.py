from setuptools import setup, Extension
import numpy
from Cython.Build import cythonize

extensions = [
    Extension(
        name="fct.lib.terrain_analysis",
        sources=["cython/terrain/terrain_analysis.pyx"],
        language="c++",
        include_dirs=[numpy.get_include()],
    )
]

setup(
    ext_modules=cythonize(extensions)
)