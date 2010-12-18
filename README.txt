imgdiff
=======

A command-line tool that combines two pictures into a single, larger
one, and opens a GUI window (provided by the Python Imaging Library)
or an external image viewer.

You could use it with a version control tool, e.g. ::

  bzr diff *.png --using=imgdiff


Installation
------------

``pip install imgdiff`` or `download it from PyPI
<http://pypi.python.org/pypi/imgdiff>`_.


Command-Line Help
-----------------

::

    Usage: imgdiff.py image1 image2

    Compare two images side-by-side

    Options:
      -h, --help          show this help message and exit
      -o OUTFILE          write the combined image to a file instead of showing it
      --viewer=VIEWER     use an external program to view an image instead using
                          the builtin viewer
      --grace=GRACE       seconds to wait before removing temporary file when
                          using an external viewer, in case it forks into
                          background
      --auto              pick orientation automatically (default)
      --lr, --left-right  force orientation to left-and-right
      --tb, --top-bottom  force orientation to top-and-bottom


Support and Development
-----------------------

The source code can be found in this Bazaar repository:
https://code.launchpad.net/~mgedmin/imgdiff/trunk.

To check it out, use ``bzr branch lp:imgdiff``.

Report bugs at https://bugs.launchpad.net/imgdiff.
