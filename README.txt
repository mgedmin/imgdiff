imgdiff
=======

A command-line tool that combines two pictures into a single, larger
one, and opens a GUI window (provided by the Python Imaging Library)
or an external image viewer.

You could use it with a version control tool, e.g. ::

  bzr diff *.png --using=imgdiff

or ::

  bzr diff *.png --using='imgdiff --eog -H'


Installation
------------

``pip install imgdiff`` or `download it from PyPI
<http://pypi.python.org/pypi/imgdiff>`_.


Usage
-----

Run ``imgdiff --help`` to see this help message::

    Usage: imgdiff image1 image2

    Compare two images side-by-side

    Options:
      -h, --help            show this help message and exit
      -o OUTFILE            write the combined image to a file
      --viewer=COMMAND      use an external image viewer (default: builtin)
      --eog                 use Eye of Gnome (same as --viewer eog)
      --grace=SECONDS       seconds to wait before removing temporary file when
                            using an external viewer (default: 1.0)
      -H, --highlight       highlight differences (EXPERIMENTAL)
      -S, --smart-highlight
                            highlight differences in a smarter way (EXPERIMENTAL)
      --opacity=OPACITY     minimum opacity for highlighting (default 64)
      --auto                pick orientation automatically (default)
      --lr, --left-right    force orientation to left-and-right
      --tb, --top-bottom    force orientation to top-and-bottom
      --bgcolor=RGB         background color (default: fff)
      --sepcolor=RGB        separator line color (default: ccc)
      --spacing=N           spacing between images (default: 3 pixels)
      --border=N            border around images (default: 0 pixels)
      --selftest            run unit tests


Output Examples
---------------

First example::

    imgdiff set1/42.png set3/

.. figure:: example1.png
   :alt: example #1

Here the images are wide and short, so imgdiff decided to put them one above
the other.

Same example, with highlighting enabled::

    imgdiff set1/42.png set3/ -H

.. figure:: example2.png
   :alt: example #2

You can see that it doesn't work very well, although it can produce nice
results in simpler cases::

    imgdiff set1/42.png set2/ -H

.. figure:: example3.png
   :alt: example #3


Support and Development
-----------------------

The source code can be found in this Git repository:
https://github.com/mgedmin/imgdiff.

To check it out, use ``git clone https://github.com/mgedmin/imgdiff``.

Report bugs at https://github.com/mgedmin/imgdiff/issues.
