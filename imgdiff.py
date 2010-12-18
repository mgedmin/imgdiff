#!/usr/bin/python
"""
imgdiff by Marius Gedminas <marius@gedmin.as>

Released under the MIT licence.
"""
import os
import sys
import optparse
import shutil
import subprocess
import tempfile
import time
import doctest
import unittest

# There are two ways PIL is packaged
try:
    from PIL import Image, ImageDraw, ImageChops, ImageFilter
except ImportError:
    import Image, ImageDraw, ImageChops, ImageFilter


__version__ = "1.4.0dev"


def parse_color(color):
    """Parse a color constant.

        >>> parse_color('4bf') == (0x44, 0xbb, 0xff, 0xff)
        True
        >>> parse_color('ccce') == (0xcc, 0xcc, 0xcc, 0xee)
        True
        >>> parse_color('d8b4a2') == (0xd8, 0xb4, 0xa2, 0xff)
        True
        >>> parse_color('12345678') == (0x12, 0x34, 0x56, 0x78)
        True

    """
    if len(color) not in (3, 4, 6, 8):
        raise ValueError('bad color %r; expected rgb/rgba/rrggbb/rrggbbaa'
                          % color)
    if len(color) in (3, 4):
        r = int(color[0], 16) * 0x11
        g = int(color[1], 16) * 0x11
        b = int(color[2], 16) * 0x11
    elif len(color) in (6, 8):
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
    if len(color) == 4:
        a = int(color[3], 16) * 0x11
    elif len(color) == 8:
        a = int(color[6:8], 16)
    else:
        a = 0xff
    return (r, g, b, a)


def check_color(option, opt, value):
    try:
        return parse_color(value)
    except ValueError:
        raise optparse.OptionValueError("option %s: invalid color value: %r"
                                         % (opt, value))


class MyOption(optparse.Option):
    TYPES = optparse.Option.TYPES + ("color", )
    TYPE_CHECKER = optparse.Option.TYPE_CHECKER.copy()
    TYPE_CHECKER["color"] = check_color


def main():
    parser = optparse.OptionParser('%prog image1 image2',
                description='Compare two images side-by-side',
                option_class=MyOption)

    parser.add_option('-o', dest='outfile',
                      help='write the combined image to a file')
    parser.add_option('--viewer', default='builtin', metavar='COMMAND',
                      help='use an external image viewer (default: %default)')
    parser.add_option('--eog', action='store_const', dest='viewer', const='eog',
                      help='use Eye of Gnome (same as --viewer eog)')
    parser.add_option('--grace', type='int', default=1.0, metavar='SECONDS',
                      help='seconds to wait before removing temporary file'
                           ' when using an external viewer (default: %default)')

    parser.add_option('-H', '--highlight', action='store_true',
                      help='highlight differences (EXPERIMENTAL)')
    parser.add_option('-S', '--smart-highlight', action='store_true',
                      help='highlight differences in a smarter way (EXPERIMENTAL, SLOW)')

    parser.add_option('--auto', action='store_const', const='auto',
                      dest='orientation', default='auto',
                      help='pick orientation automatically (default)')
    parser.add_option('--lr', '--left-right', action='store_const', const='lr',
                      dest='orientation',
                      help='force orientation to left-and-right')
    parser.add_option('--tb', '--top-bottom', action='store_const', const='tb',
                      dest='orientation',
                      help='force orientation to top-and-bottom')

    parser.add_option('--bgcolor', default='fff', type='color', metavar='RGB',
                      help='background color (default: %default)')
    parser.add_option('--sepcolor', default='ccc', type='color', metavar='RGB',
                      help='separator line color (default: %default)')
    parser.add_option('--spacing', type='int', default=3, metavar='N',
                      help='spacing between images (default: %default pixels)')
    parser.add_option('--border', type='int', default=0, metavar='N',
                      help='border around images (default: %default pixels)')

    parser.add_option('--selftest', action='store_true',
                      help='run unit tests')

    opts, args = parser.parse_args()

    if opts.selftest:
        sys.argv[1:] = args
        run_tests() # calls sys.exit()

    if len(args) != 2:
        parser.error('expecting two arguments, got %d' % len(args))

    file1, file2 = args

    if os.path.isdir(file1) and os.path.isdir(file2):
        parser.error('at least one argument must be a file, not a directory')
    if os.path.isdir(file2):
        file2 = os.path.join(file2, os.path.basename(file1))
    elif os.path.isdir(file1):
        file1 = os.path.join(file1, os.path.basename(file2))

    img1 = Image.open(file1).convert("RGB")
    img2 = Image.open(file2).convert("RGB")

    if opts.smart_highlight:
        mask1, mask2 = slow_highlight(img1, img2, opts)
    elif opts.highlight:
        mask1, mask2 = simple_highlight(img1, img2, opts)
    else:
        mask1 = mask2 = None

    img = tile_images(img1, img2, mask1, mask2, opts)

    if opts.outfile:
        img.save(opts.outfile)
    elif opts.viewer == 'builtin':
        img.show()
    else:
        name = '%s-vs-%s.png' % (os.path.basename(file1),
                                 os.path.basename(file2))
        spawn_viewer(opts.viewer, img, name, grace=opts.grace)


def pick_orientation(img1, img2, spacing, desired_aspect=1.618):
    """Pick a tiling orientation for two images.

    Returns either 'lr' for left-and-right, or 'tb' for top-and-bottom.

    Picks the one that makes the combined image have a better aspect
    ratio, where 'better' is defined as 'closer to 1:1.618'.
    """
    w1, h1 = img1.size
    w2, h2 = img2.size

    size_a = (w1 + spacing + w2, max(h1, h2, 1))
    size_b = (max(w1, w2, 1), h1 + spacing + h2)

    aspect_a = size_a[0] / size_a[1]
    aspect_b = size_b[0] / size_b[1]

    goodness_a = min(desired_aspect, aspect_a) / max(desired_aspect, aspect_a)
    goodness_b = min(desired_aspect, aspect_b) / max(desired_aspect, aspect_b)

    return 'lr' if goodness_a >= goodness_b else 'tb'


def tile_images(img1, img2, mask1, mask2, opts):
    """Combine two images into one by tiling them.

    ``mask1`` and ``mask2`` provide optional masks for alpha-blending;
    pass None to avoid.

    Fills unused areas with ``opts.bgcolor``.

    Puts a ``opts.spacing``-wide bar with a thin line of ``opts.sepcolor``
    color between them.

    ``opts.orientation`` can be 'lr' for left-and-right, 'tb' for
    top-and-bottom, or 'auto' for automatic.
    """
    w1, h1 = img1.size
    w2, h2 = img2.size

    if opts.orientation == 'auto':
        opts.orientation = pick_orientation(img1, img2, opts.spacing)

    B, S = opts.border, opts.spacing

    if opts.orientation == 'lr':
        w, h = (B + w1 + S + w2 + B, B + max(h1, h2) + B)
        pos1 = (B, (h - h1) // 2)
        pos2 = (B + w1 + S, (h - h2) // 2)
        separator_line = [(B + w1 + S//2, 0), (B + w1 + S//2, h)]
    else:
        w, h = (B + max(w1, w2) + B, B + h1 + S + h2 + B)
        pos1 = ((w - w1) // 2, B)
        pos2 = ((w - w2) // 2, B + h1 + S)
        separator_line = [(0, B + h1 + S//2), (w, B + h1 + S//2)]

    img = Image.new('RGBA', (w, h), opts.bgcolor)

    img.paste(img1, pos1, mask1)
    img.paste(img2, pos2, mask2)

    ImageDraw.Draw(img).line(separator_line, fill=opts.sepcolor)

    return img


def spawn_viewer(viewer, img, filename, grace):
    tempdir = tempfile.mkdtemp('imgdiff')
    try:
        imgfile = os.path.join(tempdir, filename)
        img.save(imgfile)
        started = time.time()
        subprocess.call([viewer, imgfile])
        # program exited too quickly, I think it forked and so may not
        # have had enough time to even start looking for the temp file
        # we just created
        elapsed = time.time() - started
        if elapsed < grace:
            time.sleep(grace - elapsed)
    finally:
        shutil.rmtree(tempdir)


def tweak_diff(diff):
    diff = diff.point(lambda i: 64 + i * 2 // 3)
    return diff


def diff(img1, img2, (x1, y1), (x2, y2)):
    w1, h1 = img1.size
    w2, h2 = img2.size
    w, h = min(w1, w2), min(h1, h2)
    diff = ImageChops.difference(img1.crop((x1, y1, x1+w, y1+h)),
                                 img2.crop((x2, y2, x2+w, y2+h)))
    diff = diff.convert('L')
    return diff


def diff_badness(diff):
    # identical pictures = black image = return 0
    # completely different pictures = white image = return lots
    return sum(i * n for i, n in enumerate(diff.histogram()))


def best_diff(img1, img2):
    w1, h1 = img1.size
    w2, h2 = img2.size
    w, h = min(w1, w2), min(h1, h2)
    best = None
    best_value = 255 * w * h + 1
    for x in range(abs(w1 - w2) + 1):
        if w1 > w2:
            x1, x2 = x, 0
        else:
            x1, x2 = 0, x
        for y in range(abs(h1 - h2) + 1):
            if h1 > h2:
                y1, y2 = y, 0
            else:
                y1, y2 = 0, y
            this = diff(img1, img2, (x1, y1), (x2, y2))
            this_value = diff_badness(this)
            if this_value < best_value:
                best = this
                best_value = this_value
                best_pos = (x1, y1), (x2, y2)
    return best, best_pos


def simple_highlight(img1, img2, opts):
    """Try to align the two images to minimize pixel differences.

    Produces two masks for img1 and img2.
    """
    diff, ((x1, y1), (x2, y2)) = best_diff(img1, img2)
    diff = tweak_diff(diff)
    diff = diff.filter(ImageFilter.MaxFilter(9))
    mask1 = Image.new('L', img1.size)
    mask2 = Image.new('L', img2.size)
    mask1.paste(diff, (x1, y1))
    mask2.paste(diff, (x2, y2))
    return mask1, mask2


def slow_highlight(img1, img2, opts):
    """Try to find similar areas between two images.

    Produces two masks for img1 and img2.
    """
    w1, h1 = img1.size
    w2, h2 = img2.size
    W, H = max(w1, w2), max(h1, h2)

    pimg1 = Image.new('RGB', (W, H), opts.bgcolor)
    pimg2 = Image.new('RGB', (W, H), opts.bgcolor)

    pimg1.paste(img1, (0, 0))
    pimg2.paste(img2, (0, 0))

    diff = Image.new('L', (W, H), 255)

    xr = abs(w1 - w2) + 1
    yr = abs(h1 - h2) + 1

    for x in range(xr):
        for y in range(yr):
            this = ImageChops.difference(pimg1, pimg2).convert('L')
            this = this.filter(ImageFilter.MaxFilter(7))
            diff = ImageChops.darker(diff, this)
            if h1 > h2:
                pimg2 = ImageChops.offset(pimg2, 0, 1)
            else:
                pimg1 = ImageChops.offset(pimg1, 0, 1)
        if h1 > h2:
            pimg2 = ImageChops.offset(pimg2, 0, -yr)
        else:
            pimg1 = ImageChops.offset(pimg1, 0, -yr)
        if w1 > w2:
            pimg2 = ImageChops.offset(pimg2, 1, 0)
        else:
            pimg1 = ImageChops.offset(pimg1, 1, 0)

    diff = diff.filter(ImageFilter.MaxFilter(5))

    diff1 = diff.crop((0, 0, w1, h1))
    diff2 = diff.crop((0, 0, w2, h2))
    return tweak_diff(diff1), tweak_diff(diff2)


def test_suite():
    return doctest.DocTestSuite()


def run_tests():
    unittest.main(defaultTest='test_suite')


if __name__ == '__main__':
    main()
