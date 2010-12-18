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
    from PIL import Image, ImageDraw
except ImportError:
    import Image, ImageDraw


__version__ = "1.3.0"


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
    img.paste(img1, pos1)
    img.paste(img2, pos2)
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


if __name__ == '__main__':
    main()
