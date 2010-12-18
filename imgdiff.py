#!/usr/bin/python
"""
imgdiff version 1.3.0 by Marius Gedminas <marius@gedmin.as>

Released under the MIT licence.
"""
import os
import optparse
import shutil
import subprocess
import tempfile
import time

# There are two ways PIL is packaged
try:
    from PIL import Image, ImageDraw, ImageChops, ImageFilter
except ImportError:
    import Image, ImageDraw, ImageChops, ImageFilter


__version__ = "1.3.1dev"


def main():
    parser = optparse.OptionParser('%prog image1 image2',
                description='Compare two images side-by-side')
    parser.add_option('-o', dest='outfile',
                      help='write the combined image to a file'
                           ' instead of showing it')
    parser.add_option('--viewer', default='builtin',
                      help='use an external program to view an image'
                           ' instead using the builtin viewer')
    parser.add_option('--grace', type='int', default=1.0,
                      help='seconds to wait before removing temporary file'
                           ' when using an external viewer, in case it forks'
                           ' into background')
    parser.add_option('-H', '--highlight', action='store_true',
                      help='highlight differences (EXPERIMENTAL)')
    parser.add_option('--auto', action='store_const', const='auto',
                      dest='orientation', default='auto',
                      help='pick orientation automatically (default)')
    parser.add_option('--lr', '--left-right', action='store_const', const='lr',
                      dest='orientation',
                      help='force orientation to left-and-right')
    parser.add_option('--tb', '--top-bottom', action='store_const', const='tb',
                      dest='orientation',
                      help='force orientation to top-and-bottom')
    opts, args = parser.parse_args()
    if len(args) != 2:
        parser.error('expecting two arguments, got %d' % len(args))

    separator = 3
    bgcolor = (0xff, 0xff, 0xff, 0xff)
    separator_color = (0xcc, 0xcc, 0xcc, 0xff)

    file1, file2 = args
    img1 = Image.open(file1).convert("RGBA")
    img2 = Image.open(file2).convert("RGBA")

    w1, h1 = img1.size
    w2, h2 = img2.size

    # there are two possible tilings; pick one that's closer in shape to
    # a square
    size_a = (w1 + separator + w2, max(h1, h2, 1))
    size_b = (max(w1, w2, 1), h1 + separator + h2)

    if opts.orientation == 'auto':
        aspect_a = max(size_a) / min(size_a)  # this way it's >= 1
        aspect_b = max(size_b) / min(size_b)  # ditto
        vsplit = (aspect_a < aspect_b)
    else:
        vsplit = (opts.orientation == 'lr')

    if vsplit:
        size = size_a
        pos1 = (0, 0)
        pos2 = (w1 + separator, 0)
        separator_line = [(w1+separator//2, 0), (w1+separator//2, size[1])]
    else:
        size = size_b
        pos1 = (0, 0)
        pos2 = (0, h1 + separator)
        separator_line = [(0, h1+separator//2), (size[0], h1+separator//2)]

    img = Image.new('RGBA', size, bgcolor)

    if opts.highlight:
        w, h = min(w1, w2), min(h1, h2)
        diff, ((x1, y1), (x2, y2)) = best_diff(img1, img2)
        diff = diff.point(lambda i: 64 + i * 2 // 3)
        diff = diff.filter(ImageFilter.MaxFilter(9))
        mask1 = Image.new('L', img1.size)
        mask2 = Image.new('L', img2.size)
        mask1.paste(diff, (x1, y1))
        mask2.paste(diff, (x2, y2))
        img.paste(img1, pos1, mask1)
        img.paste(img2, pos2, mask2)
    else:
        img.paste(img1, pos1, img1)
        img.paste(img2, pos2, img2)

    ImageDraw.Draw(img).line(separator_line, fill=separator_color)
    if opts.outfile:
        img.save(opts.outfile)
    elif opts.viewer == 'builtin':
        img.show()
    else:
        tempdir = tempfile.mkdtemp('imgdiff')
        try:
            imgfile = os.path.join(tempdir,
                                   os.path.basename(file1) + '-vs-'
                                    + os.path.basename(file2) + '.png')
            img.save(imgfile)
            started = time.time()
            subprocess.call([opts.viewer, imgfile])
            # program exitted too quickly, I think it forked and so may not
            # have had enough time to even start looking for the temp file
            # we just created
            elapsed = time.time() - started
            if elapsed < opts.grace:
                time.sleep(opts.grace - elapsed)
        finally:
            shutil.rmtree(tempdir)


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


if __name__ == '__main__':
    main()
