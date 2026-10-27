"""
Sphinx configuration for the config_resolver documentation.
"""

from pathlib import Path

project = "config_resolver"
author = "Michel Albert"
copyright = "2013-2026, Michel Albert"

# The package version lives in a single file read by setuptools as well.
release = (
    (Path(__file__).parent.parent / "config_resolver" / "version.txt")
    .read_text()
    .strip()
)
version = ".".join(release.split(".")[:2])

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    "michel_albert_sphinx",
]

autosectionlabel_prefix_document = True
# The changelog repeats subsection titles ("Fixed") under every release.
autosectionlabel_maxdepth = 2
exclude_patterns = ["_build"]

html_theme_options = {
    "repo_url": "https://github.com/exhuma/config_resolver",
    "repo_name": "exhuma/config_resolver",
    "edit_uri": "blob/master/doc",
    "features": [
        "content.code.copy",
        "navigation.top",
        "toc.follow",
    ],
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "packaging": ("https://packaging.pypa.io/en/stable/", None),
}
