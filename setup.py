from setuptools import setup, Extension
from setuptools.command.build_py import build_py as _build_py
from setuptools_scm import get_version
from packaging.version import Version
import re
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

class update_version(_build_py):
    def run(self):
        version = Version(get_version()).base_version
        path = "fct/metadata.txt"

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        content = re.sub(
            r"^version=.*",
            f"version={version}",
            content,
            flags=re.MULTILINE
        )

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        super().run()

setup(
    ext_modules=cythonize(extensions),
    cmdclass={"build_py": update_version}
)