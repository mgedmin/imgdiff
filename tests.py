import unittest
import doctest


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite('imgdiff'),
    ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
