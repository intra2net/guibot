#!/usr/bin/python3
# Copyright 2013-2020 Intranet AG and contributors
#
# guibot is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# guibot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with guibot.  If not, see <http://www.gnu.org/licenses/>.

import os
import unittest
from PIL.Image import Image
from unittest.mock import MagicMock, patch

from guibot.imagelogger import ImageLogger
from guibot.config import GlobalConfig, TemporaryConfig


class ImageLoggerTest(unittest.TestCase):
    """Tests for the ImageLogger class."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._original_logging_level = GlobalConfig.image_logging_level
        cls._original_destination = GlobalConfig.image_logging_destination
        ImageLogger.logging_destination
        GlobalConfig.image_logging_level = 10
        return super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        GlobalConfig.image_logging_level = cls._original_logging_level
        GlobalConfig.image_logging_destination = cls._original_destination
        return super().tearDownClass()

    def setUp(self) -> None:
        ImageLogger.step = 1
        self.imglog = ImageLogger()
        self.imglog.needle = MagicMock()
        self.imglog.needle.__str__.side_effect = lambda: "test_needle"
        self.imglog.haystack = MagicMock()
        self.imglog.haystack.__str__.side_effect = lambda: "test_haystack"
        self._patch_mkdir = patch("os.mkdir")
        self.mock_mkdir = self._patch_mkdir.start()

    def tearDown(self) -> None:
        self._patch_mkdir.stop()
        return super().tearDown()

    def test_step_print(self) -> None:
        """Test the string representation of the current step."""
        for i in range(1, 10):
            ImageLogger.step = i
            self.assertEqual(self.imglog.get_printable_step(), "00{}".format(i))

    def test_image_logging(self) -> None:
        """Test whether the log methods are called with the correct parameters."""
        level_mapping = {
            "debug": 10,
            "info": 20,
            "warning": 30,
            "error": 40,
            "critical": 50
        }
        for name, level in level_mapping.items():
            self.imglog.log = MagicMock()
            # call the corresponding log function
            getattr(self.imglog, name)()
            self.imglog.log.assert_called_once_with(level)

    def test_log_level(self) -> None:
        """Check that above a certain log level, images are not logged."""
        with TemporaryConfig() as cfg:
            cfg.image_logging_level = 35
            self.assertIsNone(ImageLogger().dump_matched_images())
            self.assertIsNone(ImageLogger().dump_hotmap(None, None))

    def test_image_dumping(self) -> None:
        """Check that images are dumped correctly."""
        ImageLogger.step = 18
        with patch("os.path.exists", side_effect=lambda _: False):
            self.imglog.dump_matched_images()
            self.mock_mkdir.assert_called_once_with(ImageLogger.logging_destination)
            # assert for folder creation and actual file saving
            self.imglog.needle.save.assert_called_once_with(os.path.join('imglog', 'imglog018-1needle-test_needle'))
            self.imglog.haystack.save.assert_called_once_with(os.path.join('imglog', 'imglog018-2haystack-test_haystack'))

    def test_hotmap_dumping(self) -> None:
        """Check that hotmaps are dumped correctly."""
        ImageLogger.step = 25
        ImageLogger.logging_destination = "some_path"
        image_mock = MagicMock(Image)
        with TemporaryConfig() as cfg, patch("os.path.exists", side_effect=lambda _: False):
            cfg.image_quality = 125
            path = os.path.join("some_path", "some_name")
            self.imglog.dump_hotmap("some_name", image_mock)
            # assert for folder creation and actual file saving
            self.mock_mkdir.assert_called_once_with(ImageLogger.logging_destination)
            image_mock.save.assert_called_once_with(path, compress_level=cfg.image_quality)

if __name__ == '__main__':
    unittest.main()
