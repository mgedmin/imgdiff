Changes
=======

1.8.0 (2024-10-09)
------------------

- Add support for Python 3.8, 3.9, 3.10, 3.11, 3.12, and 3.13.

- Drop support for Python 2.7, 3.5 and 3.6.


1.7.1 (2019-04-23)
------------------

- Claim Python 3.6 and 3.7 support (no code changes required).

- Drop Python 3.3 and 3.4 support.


1.7.0 (2016-09-17)
------------------

- Clarify the help message for the ``--opacity`` option.

- Add Python 3.5 support.

- Drop Python 2.6 and 3.2 support.


1.6.0 (2014-12-01)
------------------

- Add Python 3 support.

- Make the --timeout option actually work.

- Drop the --selftest option.  Add a real test suite with 100% coverage
  (which actually means little, since these are smoke tests that don't
  inspect the results for correctness.)


1.5.0 (2013-08-11)
------------------

- Suppress progress output if stderr is not a terminal.

- Make it possible to abort --highligh/--smart-highlight logic by pressing ^C.

- Abort --highlight/--smart-highlight logic if it takes longer than 10 seconds
  (timeout changeable with --timeout; use 0 to turn it off).


1.4.1 (2013-08-09)
------------------

- Depend on Pillow instead of PIL.

- Moved to GitHub.


1.4.0 (2010-12-19)
------------------

- Accepts directory names: ``imgdiff dir1/img.png dir2/``.

- Centers images relative to each other if they have different width/height.

- Automatic orientation (--auto) uses the golden ratio (1:1.618) as its goal
  for desired height:width instead of a 1:1 square.

- New experimental options: --highlight (-H) and --smart-highlight (-S).
  These highlight areas that are different and fade out areas that are
  similar.  Or at least they try.

- New options for tweaking the output: --bgcolor, --sepcolor, --spacing,
  --border, --opacity.

- New option: --eog as alias for --viewer eog, but shorter.  Guess what
  desktop environment I'm using.  ;-)

- A puny "test suite", runnable with imgdiff --selftest.

- Better source code documentation via docstrings.


1.3.0 (2010-12-18)
------------------

- First public release.  Options supported: -o, --viewer, --grace, --auto,
  --lr, --tb, --help.
