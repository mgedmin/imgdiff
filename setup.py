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
    r = re.compile(r'''^__version__ = (["'])(.+)\1$''')
    for line in read('imgdiff.py').splitlines():
        m = r.match(line)
        if m:
            return m.group(2)


def get_description():
    readme = read('README.rst')
    readme = readme.replace('.. figure:: ',
                            '.. figure:: https://pythonhosted.org/imgdiff/')
    changelog = read('CHANGES.rst')
    return readme + '\n\n\n' + changelog


setup(name='imgdiff',
      version=get_version(),
      author='Marius Gedminas',
      author_email='marius@gedmin.as',
      url='https://github.com/mgedmin/imgdiff',
      license='MIT',
      description='Present two images side-by-side for visual comparison',
      long_description=get_description(),
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Intended Audience :: End Users/Desktop',
          'License :: OSI Approved :: MIT License',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: Implementation :: CPython',
          'Programming Language :: Python :: Implementation :: PyPy',
          'Topic :: Multimedia :: Graphics',
      ],
      py_modules=['imgdiff'],
      test_suite='imgdiff.test_suite',
      zip_safe=False,
      install_requires=['Pillow'],
      entry_points="""
          [console_scripts]
          imgdiff = imgdiff:main
      """)
