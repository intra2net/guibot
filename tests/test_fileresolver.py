#!/usr/bin/python3
# Copyright 2013-2018 Intranet AG and contributors
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
import logging
import shutil
from unittest import mock
from tempfile import mkdtemp, mkstemp

import common_test
from guibot.fileresolver import FileResolver, CustomFileResolver
from guibot.errors import FileNotFoundError


class FileResolverTest(unittest.TestCase):
    """Tests for the FileResolverTest class."""

    @classmethod
    def setUpClass(cls):
        # Change to 'tests' directory
        cls.saved_working_dir = os.getcwd()
        os.chdir(common_test.unittest_dir)

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.saved_working_dir)

    def setUp(self):
        self.resolver = FileResolver()
        # Clear paths from any previous unit test since
        # the paths are shared between all FileResolver instances
        self.resolver.clear()

    def test_deprecated_class(self):
        """Check that the deprecated :py:class:`Path` class still works."""
        logger = logging.getLogger("guibot.path")
        # import the legacy path module should log a warning
        with mock.patch.object(logger, "warn") as mock_warn:
            mock_warn.assert_not_called()
            from guibot.path import Path
            # TODO replace by assert_called_once when support for Python 3.5 is dropped
            self.assertEqual(len(mock_warn.mock_calls), 1)
            self.assertEqual(Path, FileResolver)

    def test_add_path(self):
        """Test that adding a path works."""
        self.resolver.add_path("paths")

    def test_remove_path(self):
        """Test that removing a path works."""
        self.resolver.add_path("images")
        self.assertEqual(True, self.resolver.remove_path("images"))
        self.assertEqual(False, self.resolver.remove_path("images"))

    def test_remove_unknown_path(self):
        """Check that removing unknown paths doesn't break anything."""
        self.resolver.remove_path("foobar_does_not_exist")

    def test_search(self):
        """Check that different :py:class:`FileResolver` instances contain the same paths."""
        self.resolver.add_path("images")
        self.assertEqual("images/shape_black_box.png", self.resolver.search("shape_black_box.png"))

        new_finder = FileResolver()
        self.assertEqual("images/shape_black_box.png", new_finder.search("shape_black_box"))

    def test_search_fail(self):
        """Test failed search."""
        self.resolver.add_path("images")
        self.assertRaises(FileNotFoundError, self.resolver.search, "foobar_does_not_exist")

    def test_search_type(self):
        """Test that searching file names without extension works."""
        self.resolver.add_path("images")

        # Test without extension
        self.assertEqual("images/shape_black_box.png", self.resolver.search("shape_black_box"))
        self.assertEqual("images/mouse down.txt", self.resolver.search("mouse down"))
        self.assertEqual("images/circle.steps", self.resolver.search("circle"))

    def test_search_precedence(self):
        """Check the precedence of extensions when searching."""
        self.resolver.add_path("images")

        # Test correct precedence of the checks
        self.assertEqual("images/shape_blue_circle.xml", self.resolver.search("shape_blue_circle.xml"))
        self.assertEqual("images/shape_blue_circle.png", self.resolver.search("shape_blue_circle"))

    def test_search_keyword(self):
        """Check if the path restriction results in an empty set."""
        self.resolver.add_path("images")
        self.assertEqual("images/shape_black_box.png", self.resolver.search("shape_black_box.png", "images"))
        self.assertRaises(FileNotFoundError, self.resolver.search, "shape_black_box.png", "other-images")

    def test_search_silent(self):
        """Check that we can disable exceptions from being raised when searching."""
        self.resolver.add_path("images")
        self.assertEqual("images/shape_black_box.png", self.resolver.search("shape_black_box.png", silent=True))

        # Fail if the path restriction results in an empty set
        target = self.resolver.search("shape_missing_box.png", silent=True)
        self.assertIsNone(target)

    def test_paths_iterator(self):
        """Test that the FileResolver iterator yields the correct list."""
        self.assertListEqual(self.resolver._target_paths, [x for x in self.resolver])

class CustomFileResolverTest(unittest.TestCase):
    """Tests for the CustomFileResolver class."""

    def test_custom_paths(self):
        """Test if custom paths work correctly."""
        # temporary directory 1
        tmp_dir1 = mkdtemp()
        fd_tmp_file1, tmp_file1 = mkstemp(prefix=tmp_dir1 + "/", suffix=".txt")
        os.close(fd_tmp_file1)

        # temporary directory 2
        tmp_dir2 = mkdtemp()
        fd_tmp_file2, tmp_file2 = mkstemp(prefix=tmp_dir2 + "/", suffix=".txt")
        os.close(fd_tmp_file2)

        filename1 = os.path.basename(tmp_file1)
        filename2 = os.path.basename(tmp_file2)
        try:
            file_resolver = FileResolver()
            file_resolver.add_path(tmp_dir1)
            file_resolver.add_path(tmp_dir2)
            # sanity check - assert that normal path resolution works
            self.assertEqual(file_resolver.search(filename1), tmp_file1)
            self.assertEqual(file_resolver.search(filename2), tmp_file2)

            # now check that only one of these are found in our scope
            with CustomFileResolver(tmp_dir2) as p:
                self.assertEqual(p.search(filename2), tmp_file2)
                self.assertRaises(FileNotFoundError, p.search, filename1)

            # finally check that we've correctly restored everything on exit
            self.assertEqual(file_resolver.search(filename1), tmp_file1)
            self.assertEqual(file_resolver.search(filename2), tmp_file2)
        finally:
            # clean up
            FileResolver().remove_path(os.path.dirname(tmp_dir1))
            shutil.rmtree(tmp_dir1)
            shutil.rmtree(tmp_dir2)

if __name__ == '__main__':
    unittest.main()
