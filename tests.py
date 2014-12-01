import doctest
import os
import shutil
import sys
import tempfile
import unittest
from cStringIO import StringIO

import mock

import imgdiff


@mock.patch('sys.stderr', StringIO())
class TestMain(unittest.TestCase):

    def setUp(self):
        self.tmpdir = None

    def tearDown(self):
        if self.tmpdir:
            shutil.rmtree(self.tmpdir)

    def mkdtemp(self):
        if self.tmpdir is None:
            self.tmpdir = tempfile.mkdtemp(prefix='imgdiff-tests-')
        return self.tmpdir

    def main(self, *args):
        try:
            imgdiff.main(['imgdiff'] + list(args))
        except SystemExit:
            pass

    def assertIn(self, member, container):  # Python 2.6 compat
        if member not in container:
            self.fail('%s not found in %s' % (repr(member), repr(container)))

    def test_color_parsing_in_options(self):
        self.main('--bgcolor', 'invalid')
        self.assertIn("error: option --bgcolor: invalid color value: 'invalid'",
                      sys.stderr.getvalue())

    def test_wrong_number_of_arguments(self):
        self.main('foo.png')
        self.assertIn("error: expecting two arguments, got 1",
                      sys.stderr.getvalue())
        self.main('foo.png', 'bar.png', 'baz.png')
        self.assertIn("error: expecting two arguments, got 3",
                      sys.stderr.getvalue())

    def test_two_directories(self):
        self.main('set1', 'set2')
        self.assertIn("error: at least one argument must be a file, not a directory",
                      sys.stderr.getvalue())

    def test_all_ok(self):
        self.main('example1.png', 'example2.png', '--viewer', 'true')

    def test_highlight(self):
        self.main('example1.png', 'example2.png', '-H', '--viewer', 'true')

    def test_smart_highlight(self):
        self.main('example1.png', 'example2.png', '-S', '--viewer', 'true')

    def test_outfile(self):
        fn = os.path.join(self.mkdtemp(), 'diff.png')
        self.main('example1.png', 'example2.png', '-o', fn)
        self.assertTrue(os.path.exists(fn))

    @mock.patch('imgdiff.Image.Image.show')
    def test_builtin_viewer(self, mock_show):
        self.main('example1.png', 'example2.png')
        self.assertTrue(mock_show.called)

    def test_one_directory(self):
        self.main('set1/canary.png', 'set2', '--viewer', 'true')
        self.main('set1', 'set2/canary.png', '--viewer', 'true', '--tb')


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(imgdiff),
        unittest.defaultTestLoader.loadTestsFromName(__name__),
    ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
