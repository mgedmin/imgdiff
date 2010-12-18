#!/usr/bin/python
import os, re

from setuptools import setup


def relative(filename):
    here = os.path.dirname('__file__')
    return os.path.join(here, filename)


def read(filename):
    f = open(relative(filename))
    try:
        return f.read()
    finally:
        f.close()


def get_version():
    r = re.compile('^__version__ = "(.+)"$')
    for line in read('imgdiff.py').splitlines():
        m = r.match(line)
        if m:
            return m.group(1)


setup(name='imgdiff',
      version=get_version(),
      author='Marius Gedminas',
      author_email='marius@gedmin.as',
      url='http://pypi.python.org/pypi/imgdiff/',
      license='MIT',
      description='Present two images side-by-side for visual comparison',
      long_description="""
      A command-line tool that combines two pictures into a single, larger
      one, and opens a GUI window (provided by the Python Imaging Library)
      or an external image viewer.

      You could use it with a version control tool, e.g. ::

          bzr diff --using=imgdiff *.png

      """,
      classifiers=[
          'Programming Language :: Python :: 2',
      ],
      py_modules=['imgdiff'],
      zip_safe=False,
      install_requires=['PIL'],
      entry_points="""
          [console_scripts]
          imgdiff = imgdiff:main
      """)

