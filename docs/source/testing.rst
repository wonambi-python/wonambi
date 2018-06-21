Development
===========
**wonambi** follows a `test-driven development <https://en.wikipedia.org/wiki/Test-driven_development>`_ paradigm, in which tests reflect real-life problems and code is added to **wonambi** to solve those problems.
Tests are necessary to make sure that **wonambi** is working correctly.

Development consists of separate steps:

| :ref:`testfiles`: collect the data used in the tests,
| :ref:`testtest`: run the tests,
| :ref:`testcov`: check if tests cover all the relevant code,
| :ref:`testdocs`: prepare the documentation (optional),
| :ref:`testrelease`: make a new release (optional).

These steps can be run using the convenience script ``setup_wonambi.py``::

    usage: setup_wonambi [-h] [-r] [-m] [-g] [-t] [--test_import] [-d] [-c]
                         [--clean_all]

    Run tests and documentation for wonambi
                     
    optional arguments:
      -h, --help           show this help message and exit
      -r, --release        create a point release
      -m, --major_release  create a major release
      -g, --get_files      download datasets to run tests
      -t, --tests          run tests
      --test_import        run tests, but without optional depencencies
      -d, --docs           create documentations (run tests first)
      -c, --clean          clean up docs (including intermediate files)
      --clean_all          clean up docs (--clean) and files for tests

Prepare Test Environment
------------------------
Testing and documentation have additional requirements.
Tests rely on ``pytest``, with the add-ons (``pytest-qt`` and ``pytest-cov``), while documentation runs on ``sphinx``.

Install all the requirements this way::

    pip install pytest pytest-qt pytest-cov
    pip install sphinx sphinx_rtd_theme

.. _testfiles:

1. Get Files
------------
::

    setup_wonambi.py --get_files

Before you can run the tests, you need to collect the data.
Data comes from publicly available repositories (see source code for ``setup_wonambi.py`` for links). 
Sometimes, however, data is not readily available and might contain information that cannot be publicly shared.
These datasets are stored on a cloud service with a private URL.

.. NOTE::
   Before you run ``setup_wonambi.py --get_files``, you need to specify these environmental variables:
   * ``DATA_URL`` : the private URL (contact the authors for info)
   * ``BCI2000_USER``, ``BCI2000_PASSWORD`` : the username and password of the BCI2000 svn repo (create a new account on the `BCI2000 website <https://www.bci2000.org/useradmin/>`_)

This function will create new folders in ``wonambi/tests/downloads`` (where the downloaded files are cached) and ``wonambi/tests/data`` (the data that will be used for the tests).
There is an additional folder (``wonambi/tests/exported``), where files created during the tests are stored.
 
.. _testtest:

2. Run the Tests
----------------

Run all the tests
^^^^^^^^^^^^^^^^^
::

    setup_wonambi.py --tests

This function will run all the tests. 
Note that quite some tests will show an image or a window, do not click on those windows while the tests are running.

See :ref:`testtricks` for suggestions on how to write tests.

Run a specific test
^^^^^^^^^^^^^^^^^^^
Running all the tests might be quite time consuming.
If you want to run only one specific file in the test directory do::

   pytest tests/test_datatype.py

Test ImportError
^^^^^^^^^^^^^^^^
``wonambi`` should run on a minimal environment with only ``numpy`` and ``scipy`` installed.
It should not throw any ``ImportError`` if other optional packages (f.e. ``PyQt5`` or ``nibabel``) are not installed, but you should get an informative ``ImportError`` if you do try to run a function that requires an optional dependency (in other words, no errors when importing the program, only when running the program).

To test that the ``ImportError`` is correctly raised when you need functions from optional dependencies, you should run::

    setup_wonambi.py --test_import

.. NOTE::
   You should run this only in an environment that does not have the optional dependencies installed. 
   Use ``python -m venv`` to create a minimal environment.
   Then install ``numpy`` and ``scipy`` with ``pip install numpy scipy``.
   Also remember to install the packages needed for the tests (``pip install pytest pytest-cov``).

When importing a function from an optional module, you should wrap the import statement in this way::

   from ..utils import MissingDependency
   try:
       from optionalmodule import function
   except ImportError as err:
       function = MissingDependency(err)

Note that ``optionalmodule`` and ``function`` are placeholders. 
You need to change only those two names.
Also, you might need to adjust the relative import of ``..utils`` depending on which module you're working on.

All the import tests should be in ``wonambi/tests/test_import.py``.

.. _testcov:

3. Coverage
-----------
After running ``setup_wonambi.py --tests``, you can open (with a browser) the file ``wonambi/htmlcov/index.html`` which will give you a report of the lines being covered by the tests.

.. _testdocs:

4. Documentation
----------------
::

    setup_wonambi.py --docs

The documentation consists of a mix of normal ``.rst`` pages (such as this one), ``.rst`` pages that contains images, and pages containing the API.
The images and the API pages (``wonambi/docs/source/api``) are generated automatically.

.. NOTE::
   The images are all generated automatically by the tests, so you always need to first run the tests and then generate the documentation.

To read the documentation, open ``wonambi/docs/build/html/index.html`` with your browser.

.. _testrelease:

5. Release
----------
::

    setup_wonambi.py --release

for minor releases or 
::

    setup_wonambi.py --major

for major releases.

.. NOTE::
   The script will ask you for a release comment, which will be used in the :ref:`changelog`.

New features or major bug-fixes deserve their own release.
``wonambi`` has a major and a minor release number, and version 1 is when the program was initially released (not the stable API, which will never be achieved for a work-in-progress).
This keeps the version number clear and avoids version numbers starting with a zero.

Releases are handled by ``github`` and ``travis``.
A new release consists of a ``git tag``, which is uploaded to ``github``.
``travis`` takes care of creating a complete package and uploading it to `pypi <https://pypi.python.org/pypi/wonambi>`_.

.. _testtricks:

Tips and Tricks
---------------

Writing tests with ``pytest`` is quite straightforward. 
Simply add a function called ``test_...`` and write the code you want to test.
To check if the result is what you expect, use ``assert``.
Floating-point errors can be prevented by using ``pytest.approx``.

Files
^^^^^
All the files to be used in the tests and those generated by tests should be enumerated in ``tests/paths.py``.

Raises tests
^^^^^^^^^^^^
To test if a specific call raises an exception, write::

    from pytest import raises

    def test_raises():
        with raises(SyntaxError):
            True = False

Images
^^^^^^

All images in the documentation should be generated by the tests (so that we don't have images belonging to old versions).

Vispy
"""""
``vispy`` is a highly efficient package to plot OpenGL images. 
This is particularly useful for 3D images. 
Unfortunately, ``vispy`` requires some complicated syntax to make simpler plots (for that, you can use ``plotly``).

Images belonging to the ``viz`` module using ``vispy`` should be stored in the ``VIZ_PATH`` directory.
Save the images in that directory (making sure to use a unique name for each figure).
Then when you write the documentation (in the ``wonambi/docs/source/analysis/`` folder), simply point to that figure::

    .. image:: images/viz3_01_XXX.png

.. NOTE::
   If you want to show in the documentation the code that was used to generate the image, you can refer to the test script using this syntax::

       .. literalinclude:: ../../../tests/test_viz_plot3d.py
           :lines: 23-26

Plotly
""""""
``plotly`` can be used to plot interactive plots.
The syntax is very intuitive, but unfortunately it doesn't work well for 3D plots with lots of points (for that, use ``vispy``).

In the documentation, we can use interactive plots as well.
You can create a test by simply preparing a figure (here called ``example_interactive_image``) and saving it with the function ``tests.utils.save_plotly_fig``::

    fig = go.Figure(data=[{'y': (1, 2)}])
    save_plotly_fig(fig, 'example_interactive_image')

Then, in the documentation (in the ``wonambi/docs/source/analysis/`` folder), first you need to use this line at the very top::

    .. raw:: html
    
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>

In the same doc file, to insert the interactive image, you can use::

    .. raw:: html
        :file: plotly/example_interactive_image.html

You can use ``literalinclude`` to show the actual code in the tests.

Qt test
^^^^^^^
Testing using Qt is often complicated and verbose, but it's still very important to test it right.
A simple test should be written as::

    def test_mainwindow(qtbot):
        w = MainWindow()
        qtbot.addWidget(w)

Modal Dialog
""""""""""""
Modal dialogs are those dialog that block the main window and keep it on the background.
I don't know how to interact with the modal dialog, so we just skip the dialog and we pass ``test_filename`` as additional argument to the method::

    def make_new_group(self, checked=False, test_name=None):
        if test_name is None:
           new_name = QInputDialog.getText(self, 'New Group',
                                          'Enter Name')
        else:
           new_name = [test_name, True]  # like output of getText

Screenshots
"""""""""""
Screenshot of a window or a part of a window (widget), you can highlight a widget in red and create a screenshot with::

    def test_grab_screenshot(qtbot):

        w = MainWindow()
        qtbot.addWidget(w)
        w.labels.setStyleSheet("background-color: red;")
        w.grab().save(str(GUI_PATH / 'xxx.png'))
        w.labels.setStyleSheet("")

If you use a menubar, there is no simple way to get a screenshot, so you need to capture the whole screen::

    def test_widget_notes_import_fasst(qtbot):

        w = MainWindow()
        qtbot.addWidget(w)

        menubar = w.menuBar()

        # --- Complex code to capture screenshot of menubar ---#
        def screenshot():
            screen = QApplication.primaryScreen()
            png_name = str(GUI_PATH / 'notes_04_import_fasst.png')
            screen.grabWindow(0, w.x(), w.y(), w.width(), w.height()).save(png_name)

        # lots of processEvents needed
        QApplication.processEvents()
        QTimer.singleShot(3000, screenshot)
        QApplication.processEvents()
        sleep(5)
        QApplication.processEvents()
        w.close()
        # --- ---#
