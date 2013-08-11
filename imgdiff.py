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


__version__ = "1.5.0"


def parse_color(color):
    """Parse a color value.

    I've decided not to expect a leading '#' because it's a comment character
    in some shells.

        >>> parse_color('4bf') == (0x44, 0xbb, 0xff, 0xff)
        True
        >>> parse_color('ccce') == (0xcc, 0xcc, 0xcc, 0xee)
        True
        >>> parse_color('d8b4a2') == (0xd8, 0xb4, 0xa2, 0xff)
        True
        >>> parse_color('12345678') == (0x12, 0x34, 0x56, 0x78)
        True

    Raises ValueError on errors.
    """
    if len(color) not in (3, 4, 6, 8):
        raise ValueError('bad color %s' % repr(color))
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
    """Validate and convert an option value of type 'color'.

    ``option`` is an optparse.Option instance.

    ``opt`` is a string with the user-supplied option name (e.g. '--bgcolor').

    ``value`` is the user-supplied value.
    """
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
    parser = optparse.OptionParser('%prog [options] image1 image2',
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
                      help='highlight differences in a smarter way (EXPERIMENTAL)')
    parser.add_option('--opacity', type='int', default='64',
                      help='minimum opacity for highlighting (default %default)')
    parser.add_option('--timeout', type='int', default='10',
                      help='skip highlighting if it takes too long'
                           ' (default: %default seconds)')

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
    """Launch an external program to view an image.

    ``img`` is an Image object.

    ``viewer`` is a command name.  Arguments are not allowed; exactly one
    argument will be passed: the name of the image file.

    ``filename`` is the suggested filename for a temporary file.

    ``grace`` is the number of seconds to wait after spawning the viewer
    before removing the temporary file.  Useful if your viewer forks
    into background before it opens the file.
    """
    tempdir = tempfile.mkdtemp('imgdiff')
    try:
        imgfile = os.path.join(tempdir, filename)
        img.save(imgfile)
        started = time.time()
        subprocess.call([viewer, imgfile])
        elapsed = time.time() - started
        if elapsed < grace:
            # Program exited too quickly. I think it forked and so may not
            # have had enough time to even start looking for the temp file
            # we just created. Wait a bit before removing the temp file.
            time.sleep(grace - elapsed)
    finally:
        shutil.rmtree(tempdir)


def tweak_diff(diff, opacity):
    """Adjust a difference map into an opacity mask for a given lowest opacity.

    Performs a linear map from [0; 255] to [opacity; 255].

    The result is that similar areas will have a given opacity, while
    dissimilar areas will be opaque.
    """
    mask = diff.point(lambda i: opacity + i * (255 - opacity) // 255)
    return mask


def diff(img1, img2, (x1, y1), (x2, y2)):
    """Compare two images with given alignments.

    Returns a difference map.

    ``(x1, y1)`` specify the top-left corner of the aligned area with respect
    to ``img1``.

    ``(x2, y2)`` specify the top-left corner of the aligned area with respect
    to ``img2``.

    Either ``x1`` or ``x2`` must be 0, depending on whether ``img1`` is
    narrower or wider than ``img2``.  Both must be 0 if the two images
    have the same width.

    Either ``y1`` or ``y2`` must be 0, depending on whether ``img2`` is
    shorter or taller than ``img2``.  Both must be 0 if the two images
    have the same height.

    Suppose ``img1`` is bigger than ``img2``::

        +----------------------------------+
        | img1     ^                       |
        |          | y1                    |
        |          v                       |
        |      +------------------------+  |
        |      | img2                   |  |
        |<---->|                        |  |
        |  x1  |                        |  |
        |      +------------------------+  |
        +----------------------------------+

    In this case ``x2`` and ``y2`` are zero, ``0 <= x1 <= (w1 - w2)``, and
    ``0 <= y1 <= (h1 - h2)``, where ``(w1, h1) == img1.size`` and
    ``(w2, h2) == img2.size``.

    If ``img2`` is smaller than ``img1``, just swap the labels in the
    description above.

    Suppose ``img1`` is wider but shorter than ``img2``::

               +------------------------+
               | img2     ^             |
               |          | y2          |
               |          v             |
        +------|------------------------|--+
        | img1 |                        |  |
        |      |                        |  |
        |<---->|                        |  |
        |  x1  |                        |  |
        |      |                        |  |
        +------|------------------------|--+
               +------------------------+

    In this case ``x2`` and ``y1`` are zero, ``0 <= x1 <= (w1 - w2)``, and
    ``0 <= y2 <= (h2 - h1)``, where ``(w1, h1) == img1.size`` and
    ``(w2, h2) == img2.size``.

    If ``img1`` is narrower but taller than ``img2``, just swap the labels
    in the description above.
    """
    w1, h1 = img1.size
    w2, h2 = img2.size
    w, h = min(w1, w2), min(h1, h2)
    diff = ImageChops.difference(img1.crop((x1, y1, x1+w, y1+h)),
                                 img2.crop((x2, y2, x2+w, y2+h)))
    diff = diff.convert('L')
    return diff


def diff_badness(diff):
    """Estimate the "badness" value of a difference map.

    Returns 0 if the pictures are identical

    Returns a large number if the pictures are completely different
    (e.g. a black field and a white field).  More specifically, returns
    ``255 * width * height`` where ``(width, height) == diff.size``.

    Returns something in between for other situations.
    """
    # identical pictures = black image = return 0
    # completely different pictures = white image = return lots
    return sum(i * n for i, n in enumerate(diff.histogram()))


class Timeout(KeyboardInterrupt):
    pass


class Progress(object):

    def __init__(self, total, delay=1.0, timeout=10.0, what='possible alignments'):
        self.started = time.time()
        self.delay = delay
        self.total = total
        self.what = what
        self.position = 0
        self.shown = False
        self.timeout = timeout
        self.stream = sys.stderr
        self.isatty = self.stream.isatty()

    def _say_if_terminal(self, msg):
        if self.isatty:
            self.stream.write('\r')
            self.stream.write(msg)
            self.stream.flush()
            self.shown = True

    def _say(self, msg):
        if self.isatty:
            self.stream.write('\r')
        self.stream.write(msg)
        self.stream.flush()
        self.shown = True

    def next(self):
        self.position += 1
        if self.timeout and time.time() - self.started > self.timeout:
            self._say('Highlighting takes too long: timed out after %.0f seconds'
                      % self.timeout)
            raise Timeout
        if time.time() - self.started > self.delay:
            self._say_if_terminal('%d%% (%d out of %d %s)'
                                  % (self.position * 100 // self.total,
                                     self.position, self.total, self.what))
        if self.position == self.total:
            self.done()

    def done(self):
        if self.shown:
            self._say('\n')
            self.shown = False


def best_diff(img1, img2):
    """Find the best alignment of two images that minimizes the differences.

    Returns (diff, alignments) where ``diff`` is a difference map, and
    ``alignments`` is a tuple ((x1, y2), (x2, y2)).

    See ``diff()`` for the description of the alignment numbers.
    """
    w1, h1 = img1.size
    w2, h2 = img2.size
    w, h = min(w1, w2), min(h1, h2)
    best = None
    best_value = 255 * w * h + 1

    xr = abs(w1 - w2) + 1
    yr = abs(h1 - h2) + 1

    p = Progress(xr * yr)
    for x in range(xr):
        if w1 > w2:
            x1, x2 = x, 0
        else:
            x1, x2 = 0, x
        for y in range(yr):
            if h1 > h2:
                y1, y2 = y, 0
            else:
                y1, y2 = 0, y
            p.next()
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

    The algorithm works by comparing every possible alignment of the images,
    finding the aligment that minimzes the differences, and then smoothing
    it a bit to reduce spurious matches in areas that are perceptibly
    different (e.g. text).
    """

    try:
        diff, ((x1, y1), (x2, y2)) = best_diff(img1, img2)
    except KeyboardInterrupt:
        return None, None
    diff = diff.filter(ImageFilter.MaxFilter(9))
    diff = tweak_diff(diff, opts.opacity)
    # If the images have different sizes, the areas outside the alignment
    # zone are considered to be dissimilar -- filling them with 0xff.
    # Perhaps it would be better to compare those bits with bars of solid
    # color, filled with opts.bgcolor?
    mask1 = Image.new('L', img1.size, 0xff)
    mask2 = Image.new('L', img2.size, 0xff)
    mask1.paste(diff, (x1, y1))
    mask2.paste(diff, (x2, y2))
    return mask1, mask2


def slow_highlight(img1, img2, opts):
    """Try to find similar areas between two images.

    Produces two masks for img1 and img2.

    The algorithm works by comparing every possible alignment of the images,
    smoothing it a bit to reduce spurious matches in areas that are
    perceptibly different (e.g. text), and then taking the point-wise minimum
    of all those difference maps.

    This way if you insert a few pixel rows/columns into an image, similar
    areas should match even if different areas need to be aligned with
    different shifts.

    As you can imagine, this brute-force approach can be pretty slow, if
    there are many possible alignments.  The closer the images are in size,
    the faster this will work.

    If would work better if it could compare alignments that go beyond the
    outer boundaries of the images, in case some pixels got shifted closer
    to an edge.
    """
    w1, h1 = img1.size
    w2, h2 = img2.size
    W, H = max(w1, w2), max(h1, h2)

    pimg1 = Image.new('RGB', (W, H), opts.bgcolor)
    pimg2 = Image.new('RGB', (W, H), opts.bgcolor)

    pimg1.paste(img1, (0, 0))
    pimg2.paste(img2, (0, 0))

    diff = Image.new('L', (W, H), 255)
    # It is not a good idea to keep one diff image; it should track the
    # relative positions of the two images.  I think that's what explains
    # the fuzz I see near the edges of the different areas.

    xr = abs(w1 - w2) + 1
    yr = abs(h1 - h2) + 1

    try:
        p = Progress(xr * yr)
        for x in range(xr):
            for y in range(yr):
                p.next()
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
    except KeyboardInterrupt:
        return None, None

    diff = diff.filter(ImageFilter.MaxFilter(5))

    diff1 = diff.crop((0, 0, w1, h1))
    diff2 = diff.crop((0, 0, w2, h2))

    mask1 = tweak_diff(diff1, opts.opacity)
    mask2 = tweak_diff(diff2, opts.opacity)

    return mask1, mask2


def test_suite():
    """Collect all the tests into a test suite."""
    return doctest.DocTestSuite()


def run_tests():
    """Run the test suite.

    Invokes sys.exit() with a zero or non-zero status code as appropriate
    """
    unittest.main(defaultTest='test_suite')


if __name__ == '__main__':
    main()
