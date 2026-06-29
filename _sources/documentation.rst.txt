Documentation
==============


How to update the documentation
------------------------------------------
Update directly the files in the doc folder. These will be compiled and updated through github (github actions) upon push in the main branch.

How to build locally the documentation
-------------------------------------------------
In the repository in your computed, use the following commands : 

.. code-block:: bash

   sphinx-build doc _build

Then: 

.. code-block:: bash

   sphinx-build doc -W -b linkcheck -d _build/doctrees _build/html

This should build locally the html pages in the repo :guilabel:`_build` that can be deleted afterwards. It is also useful to use these commands to check an update of the documetation on the local computer before pushing to github.

How to have autodoc and autosummary for different functions
---------------------------------------------------------------
:guilabel:`autodoc` and :guilabel:`autosummary` are powerful tools to get the docstring of your code and represent it. There are a few conditions for it to work correctly: 

#. The path to your module should be added in ``conf.py``

#. The scripts you want to docstring should pass a standard import, i.e they must be compatible with your local python. This is obvious for your local machine, but not for the github action. You need to be careful that all the modules are installed when running the github action that will, in the end, generate the ``html files``.

#. The scripts should be importable as modules. This project currently documents its scripts **manually** in :guilabel:`codedocumentation.rst` (no autodoc), so the docs build stays light and does not need glaciercore / heavy dependencies installed in the GitHub Action. If you reintroduce autodoc for an importable module, add its path to ``conf.py`` and reference it with ``automodule`` / ``autoclass`` / ``autofunction``.

#. Sphinx :guilabel:`autodoc` reference available https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#module-sphinx.ext.autodoc

Conventions to write documentation in github page for Corintis
---------------------------------------------------------------
These are the following settings that are used so far and ideally we should stick to it, or adapt them everywhere for consistency.

1. The documentation is written in restructured text (rst) format. This is the format used by sphinx. It is automatically map into a html format by sphinx, through github actions.

2. Code convention. Inline lines of code can be written like this ``comandline_example`` and block of code with the code block syntax like that : 

.. code-block:: python

   import numpy as np


3. Specific folders/files or program names can be put in perspective either with guilabel like :guilabel:`this` or with the inline code convention like ``that``. Both are ok, ideally :guilabel:`folders` and ``files`` follow the guilabel/inline code convention like this.

4. Math formulas can be written in :guilabel:`latex` syntax either inline like this with the math marker :math:`\alpha+\beta=\gamma` or in a block like navier-stokes equations :eq:`navier_stokes`, which is a copy-paste of the latex in the notion page https://www.notion.so/Navier-Stokes-strong-form-5b3fc5c2546c427389d6355e13cfee40  :

.. math:: 
   :label: navier_stokes

   &\text{div}(\rho_0 \boldsymbol{U}_{3d}\otimes \boldsymbol{U}_{3d})=-\boldsymbol{\nabla}P_{3d}+\text{div}(2 \mu \epsilon(\boldsymbol{U}_{3d}))-A_{opt}\boldsymbol{U}_{3d}, \\\\
   &\text{div}\left( \boldsymbol{U_{3d}}\right) =0.

Unfortunately, it seems that the references to different equations can not be passed between different pages (to be further investigated).

5. In order to use cross-page references the easiest and most convenient use is the target reference like :ref:`this <plotting-section>`, which is a direct reference to the :guilabel:`usage` page's plotting section. The label is declared just above that heading with ``.. _plotting-section:``.
