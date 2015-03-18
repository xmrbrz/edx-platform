"""
Test cases for image processing functions in the profile image package.
"""

from itertools import product
import os
from tempfile import NamedTemporaryFile

from django.core.files.uploadedfile import UploadedFile
from django.test import TestCase
from django.test.utils import override_settings
import ddt
import mock
from PIL import Image

from ..images import (
    validate_uploaded_image,
    generate_profile_images,
    remove_profile_images,
    DevMsg,
    ImageValidationError,
)
from .helpers import make_image_file, make_uploaded_file


@ddt.ddt
class TestValidateUploadedImage(TestCase):
    """
    Test validate_uploaded_image
    """

    @ddt.data(
        (99, DevMsg.FILE_TOO_SMALL),
        (100, ),
        (1024, ),
        (1025, DevMsg.FILE_TOO_LARGE),
    )
    @ddt.unpack
    @override_settings(PROFILE_IMAGE_MIN_BYTES=100, PROFILE_IMAGE_MAX_BYTES=1024)
    def test_file_size(self, upload_size, failure_message=None):
        """
        Ensure that files outside the accepted size range fail validation.
        """
        uploaded_file = make_uploaded_file(
            dimensions=(1, 1),
            extension=".png",
            content_type="image/png",
            force_size=upload_size
        )
        if failure_message is not None:
            with self.assertRaises(ImageValidationError) as cm:
                validate_uploaded_image(uploaded_file)
            self.assertEqual(cm.exception.message, failure_message)
        else:
            validate_uploaded_image(uploaded_file)
            self.assertEqual(uploaded_file.tell(), 0)

    @ddt.data(
        (".gif", "image/gif"),
        (".jpg", "image/jpeg"),
        (".jpeg", "image/jpeg"),
        (".png", "image/png"),
        (".bmp", "image/bmp", DevMsg.FILE_BAD_TYPE),
        (".tif", "image/tiff", DevMsg.FILE_BAD_TYPE),
    )
    @ddt.unpack
    def test_extension(self, extension, content_type, failure_message=None):
        """
        Ensure that files whose extension is not supported fail validation.
        """
        uploaded_file = make_uploaded_file(extension=extension, content_type=content_type)
        if failure_message is not None:
            with self.assertRaises(ImageValidationError) as cm:
                validate_uploaded_image(uploaded_file)
            self.assertEqual(cm.exception.message, failure_message)
        else:
            validate_uploaded_image(uploaded_file)
            self.assertEqual(uploaded_file.tell(), 0)

    def test_extension_mismatch(self):
        """
        Ensure that validation fails when the file extension does not match the
        file data.
        """
        # make a bmp, try to fool the function into thinking its a jpeg
        bmp_file = make_image_file(extension=".bmp")
        fake_jpeg_file = NamedTemporaryFile(suffix=".jpeg")
        fake_jpeg_file.write(bmp_file.read())
        fake_jpeg_file.seek(0)
        uploaded_file = UploadedFile(
            fake_jpeg_file,
            content_type="image/jpeg",
            size=os.path.getsize(fake_jpeg_file.name)
        )
        with self.assertRaises(ImageValidationError) as cm:
            validate_uploaded_image(uploaded_file)
        self.assertEqual(cm.exception.message, DevMsg.FILE_BAD_EXT)

    def test_content_type(self):
        """
        Ensure that validation fails when the content_type header and file
        extension do not match
        """
        with self.assertRaises(ImageValidationError) as cm:
            validate_uploaded_image(
                make_uploaded_file(extension=".jpeg", content_type="image/gif")
            )
        self.assertEqual(cm.exception.message, DevMsg.FILE_BAD_MIMETYPE)


@ddt.ddt
class TestGenerateProfileImages(TestCase):
    """
    Test generate_profile_images
    """

    @ddt.data(
        *product(
            ["gif", "jpg", "png"],
            [(1, 1), (10, 10), (100, 100), (1000, 1000), (1, 10), (10, 100), (100, 1000), (1000, 999)],
        )
    )
    @ddt.unpack
    def test_generation(self, format, dimensions):
        """
        Ensure that regardless of the input format or dimensions, the outcome
        of calling the function is square jpeg files with explicitly-requested
        dimensions being saved to the profile image storage backend.
        """
        extension = "." + format
        content_type = "image/" + format
        uploaded_file = make_uploaded_file(dimensions=dimensions, extension=extension, content_type=content_type)

        requested_sizes = {
            10: "ten.jpg",
            100: "hundred.jpg",
            1000: "thousand.jpg",
        }
        mock_storage = mock.Mock()
        with mock.patch(
                "openedx.core.djangoapps.profile_images.images.get_profile_image_storage",
                return_value=mock_storage
        ):
            generate_profile_images(uploaded_file, requested_sizes)
            names_and_files = [v[0] for v in mock_storage.save.call_args_list]
            actual_sizes = {}
            for name, file in names_and_files:
                # get the size of the image file and ensure it's square jpeg
                image_obj = Image.open(file)
                width, height = image_obj.size
                self.assertEqual(width, height)
                self.assertEqual(image_obj.format, 'JPEG')
                actual_sizes[width] = name
            self.assertEqual(requested_sizes, actual_sizes)
            mock_storage.save.reset_mock()


class TestRemoveProfileImages(TestCase):
    """
    Test remove_profile_images
    """

    def test_remove(self):
        """
        Ensure that the outcome of calling the function is that the named images
        are deleted from the profile image storage backend.
        """
        requested_sizes = {
            10: "ten.jpg",
            100: "hundred.jpg",
            1000: "thousand.jpg",
        }
        mock_storage = mock.Mock()
        with mock.patch(
                "openedx.core.djangoapps.profile_images.images.get_profile_image_storage",
                return_value=mock_storage
        ):
            remove_profile_images(requested_sizes)
            deleted_names = [v[0][0] for v in mock_storage.delete.call_args_list]
            self.assertEqual(requested_sizes.values(), deleted_names)
            mock_storage.save.reset_mock()
