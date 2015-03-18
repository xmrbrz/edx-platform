"""
Helper methods for use in profile image tests.
"""
import os
from tempfile import NamedTemporaryFile

from django.core.files.uploadedfile import UploadedFile
from PIL import Image



def make_image_file(dimensions=(320, 240), extension=".jpeg", force_size=None):
    """
    Returns a named temporary file created with the specified image type and options.

    Note the default dimensions are unequal (not a square) ensuring that center-square
    cropping logic will be exercised during tests.
    """
    image = Image.new('RGB', dimensions, "green")
    image_file = NamedTemporaryFile(suffix=extension)
    image.save(image_file)
    if force_size is not None:
        image_file.seek(0, os.SEEK_END)
        bytes_to_pad = force_size - image_file.tell()
        # write in hunks of 256 bytes
        hunk, byte_ = bytearray([0] * 256), bytearray([0])
        num_hunks, remainder = divmod(bytes_to_pad, 256)
        for _ in xrange(num_hunks):
            image_file.write(hunk)
        for _ in xrange(remainder):
            image_file.write(byte_)
        image_file.flush()
    image_file.seek(0)
    return image_file


def make_uploaded_file(content_type, *a, **kw):
    """
    Wrap the result of make_image_file in a django UploadedFile
    """
    image_file = make_image_file(*a, **kw)
    return UploadedFile(
        image_file,
        content_type=content_type,
        size=os.path.getsize(image_file.name),
    )


