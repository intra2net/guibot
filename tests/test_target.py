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
from unittest.mock import Mock, patch, call
from tempfile import NamedTemporaryFile, mkdtemp, mkstemp

import common_test
from guibot.target import Chain, Image, Pattern, Text
from guibot.finder import Finder, CVParameter
from guibot.errors import FileNotFoundError, UnsupportedBackendError
from guibot.fileresolver import FileResolver


class ImageTest(unittest.TestCase):

    def setUp(self):
        self.file_all_shapes = os.path.join(common_test.unittest_dir, 'images', 'all_shapes.png')

    def test_basic(self):
        image = Image(self.file_all_shapes)

        self.assertEqual(400, image.width)
        self.assertEqual(300, image.height)

        self.assertTrue(image.filename.find('all_shapes.png') != -1)
        self.assertIsInstance(image.match_settings, Finder)
        self.assertFalse(image.use_own_settings)

    def test_copy_object(self):
        image = Image(self.file_all_shapes)

        my_copy = image.copy()
        self.assertNotEqual(image.match_settings, my_copy.match_settings)
        self.assertEqual(image.filename, my_copy.filename)
        self.assertEqual(image.similarity, my_copy.similarity)
        self.assertEqual(image.pil_image, my_copy.pil_image)
        self.assertEqual(image.width, my_copy.width)
        self.assertEqual(image.height, my_copy.height)
        self.assertEqual(image.center_offset, my_copy.center_offset)

    def test_center_offset(self):
        image = Image(self.file_all_shapes)

        center_offset = image.center_offset
        self.assertEqual(0, center_offset.x)
        self.assertEqual(0, center_offset.y)

        new_image = image.with_center_offset(100, 30)
        self.assertEqual(image.filename, new_image.filename)
        self.assertEqual(image.similarity, new_image.similarity)
        self.assertEqual(image.pil_image, new_image.pil_image)
        self.assertEqual(image.width, new_image.width)
        self.assertEqual(image.height, new_image.height)
        self.assertNotEqual(image.center_offset, new_image.center_offset)

        center_offset = new_image.center_offset
        self.assertEqual(100, center_offset.x)
        self.assertEqual(30, center_offset.y)

        # check it's unchanged in the original
        center_offset = image.center_offset
        self.assertEqual(0, center_offset.x)
        self.assertEqual(0, center_offset.y)

    def test_similarity(self):
        image = Image(self.file_all_shapes)

        new_image = image.with_similarity(0.45)
        self.assertEqual(0.45, new_image.similarity)
        # TODO: create a separate config for defaults to extract this from there
        self.assertEqual(0.8, image.similarity)

        self.assertEqual(image.filename, new_image.filename)
        self.assertNotEqual(image.similarity, new_image.similarity)
        self.assertEqual(image.pil_image, new_image.pil_image)
        self.assertEqual(image.width, new_image.width)
        self.assertEqual(image.height, new_image.height)
        self.assertEqual(image.center_offset, new_image.center_offset)

    def test_save(self):
        image = Image(self.file_all_shapes)

        with NamedTemporaryFile(prefix='guibot', suffix='.png') as f:
            returned_image = image.save(f.name)
            loaded_image = Image(f.name)

            self.assertEqual(returned_image.filename, loaded_image.filename)
            self.assertEqual(image.width, loaded_image.width)
            self.assertEqual(image.height, loaded_image.height)

            image.use_own_settings = True
            returned_image = image.save(f.name)
            loaded_image = Image(f.name)
            os.unlink("%s.match" % f.name[:-4])

            for category in returned_image.match_settings.params.keys():
                self.assertIn(category, loaded_image.match_settings.params.keys())
                for key in returned_image.match_settings.params[category].keys():
                    self.assertIn(key, loaded_image.match_settings.params[category])
                    if not isinstance(returned_image.match_settings.params[category][key], CVParameter):
                        self.assertEqual(returned_image.match_settings.params[category][key],
                                         loaded_image.match_settings.params[category][key])
                        continue
                    self.assertAlmostEqual(returned_image.match_settings.params[category][key].value,
                                           loaded_image.match_settings.params[category][key].value)
                    self.assertEqual(returned_image.match_settings.params[category][key].range[0],
                                     loaded_image.match_settings.params[category][key].range[0])
                    self.assertEqual(returned_image.match_settings.params[category][key].range[1],
                                     loaded_image.match_settings.params[category][key].range[1])
                    self.assertEqual(returned_image.match_settings.params[category][key].delta,
                                     loaded_image.match_settings.params[category][key].delta)
                    self.assertEqual(returned_image.match_settings.params[category][key].tolerance,
                                     loaded_image.match_settings.params[category][key].tolerance)
                    self.assertEqual(returned_image.match_settings.params[category][key].fixed,
                                     loaded_image.match_settings.params[category][key].fixed)

    def test_nonexisting_image(self):
        try:
            Image('foobar_does_not_exist')
            self.fail('Exception not thrown')
        except FileNotFoundError:
            pass

    def test_image_cache(self):
        image = Image(self.file_all_shapes)

        second_image = Image(self.file_all_shapes)
        self.assertIs(image.pil_image, second_image.pil_image)

        # Clear image cache the hard way
        Image()._cache.clear()

        third_image = Image(self.file_all_shapes)
        self.assertIsNot(image.pil_image, third_image.pil_image)


class ChainTest(unittest.TestCase):
    """Tests for the chain target (series of steps)."""

    stepsfile_name = "some_stepsfile"
    stepsfile_fullname = "{}.steps".format(stepsfile_name)
    # special file that we will report as non-existing for some tests
    stepsfile_missing = "missing_stefile"
    # files that the mock should report as missing
    non_existing_files = [
        "{}.match".format(stepsfile_name),
        "{}.steps".format(stepsfile_missing),
        "/tmp/some_text_content.txt",
        "/tmp/some_text_content.txt.png",
        "/tmp/some_text_content.txt.xml",
        "/tmp/some_text_content.txt.txt",
        "/tmp/some_text_content.txt.csv",
        "/tmp/some_text_content.txt.steps",
        "/tmp/17.csv",
        "/tmp/17.csv.png",
        "/tmp/17.csv.xml",
        "/tmp/17.csv.txt",
        "/tmp/17.csv.csv",
        "/tmp/17.csv.steps",
    ]

    def setUp(self):
        """Create mocks and enable patches."""
        # start with a clean environment
        self._old_paths = list(FileResolver._target_paths)
        FileResolver().clear()

        self._tmpfiles = []
        self.stepsfile_content = ""
        self._patches = {
            # Chain class and it's parent checks the existence of some files, so let's
            # report that they are all there -- except for one that we need to be missing
            "path_exists": patch("os.path.exists", lambda f: f not in self.non_existing_files),
            # The Target class will build a match file for each item in the stepsfile
            "Finder_from_match_file": patch("guibot.finder.Finder.from_match_file", wraps=self._get_match_file),
            "Finder_to_match_file": patch("guibot.finder.Finder.to_match_file"),
            "PIL_Image_open": patch("PIL.Image.open")
        }
        self.mock_exists = self._patches["path_exists"].start()
        self.mock_match_read = self._patches["Finder_from_match_file"].start()
        self.mock_match_write = self._patches["Finder_to_match_file"].start()
        # this one is not that important -- no need to store
        self._patches["PIL_Image_open"].start()
        return super().setUp()

    def tearDown(self):
        """Cleanup removing any patches and files created."""
        # start with a clean environment
        for p in self._old_paths:
            FileResolver().add_path(p)

        # stop patches
        for p in self._patches.values():
            p.stop()
        for fn in self._tmpfiles:
            os.unlink(fn)
        return super().tearDown()

    def _build_chain(self, stepsfile_contents, stepsfile=None):
        """
        Create an instance of :py:class:`guibot.target.Chain` to be used by the tests.

        :param str stepsfile_contents: contents for the stepsfile to be passed when creating the finder
        :param str stepsfile: name of the stepsfile to load or None to use the default
        :returns: an instance of the finder
        :rtype: :py:class:`finder.Finder`
        """
        filename = self._create_temp_file(prefix=self.stepsfile_name,
            extension=".steps", contents=stepsfile_contents)
        return Chain(os.path.splitext(filename)[0])

    def _get_match_file(self, filename):
        """
        Mock function to replace py:func:`Finder.from_match_file`.

        It will generated a finder based on the filename provided.

        :param str filename: match filename for the configuration
        :returns: target finder with the parsed (and generated) settings
        :rtype: :py:class:`finder.Finder`
        """
        # guess the backend from the filename
        parts = filename.split("_")
        backend = parts[1] if len(parts) > 1 else parts[0]
        finder_mock = Mock()
        finder_mock.params = {
            "find": {
                "backend": backend
            }
        }
        return finder_mock

    def _create_temp_file(self, prefix=None, extension=None, contents=None):
        """
        Create a temporary file, keeping track of it for auto-removal.

        :param str prefix: string to prepend to the file name
        :param str extension: extension of the generated file
        :param str contents: contents to write on the file
        :returns: name of the temporary file generated
        :rtype: str
        """
        fd, filename = mkstemp(prefix=prefix, suffix=extension)
        if contents:
            os.write(fd, contents.encode("utf8"))
        os.close(fd)
        self._tmpfiles.append(filename)
        return filename

    def test_stepsfile_lookup(self):
        """Test that the stepsfile will be searched using :py:class:`guibot.fileresolver.FileResolver`."""
        tmp_dir = mkdtemp()
        tmp_steps_file = "{}/{}.steps".format(tmp_dir, self.stepsfile_missing)
        with open(tmp_steps_file, "w") as fp:
            fp.write("image_for_autopy.png	some_autopy_matchfile.match")
        filename = os.path.basename(os.path.splitext(tmp_steps_file)[0])

        try:
            with patch("guibot.fileresolver.FileResolver.search", wraps=lambda _: tmp_steps_file) as mock_search:
                Chain(self.stepsfile_missing)
                # but make sure we did search for the "missing" stepsfile
                mock_search.assert_any_call("{}.steps".format(filename))
        finally:
            os.unlink(tmp_steps_file)
            os.rmdir(tmp_dir)

    def test_finder_creation(self):
        """Test that all finders are correctly created from a stepsfile."""
        stepsfile_contents = [
            "item_for_contour.png	some_contour_matchfile.match",
            "item_for_tempfeat.png	some_tempfeat_matchfile.match",
            "item_for_feature.png	some_feature_matchfile.match",
            "item_for_deep.csv	some_deep_matchfile.match",
            "item_for_cascade.xml	some_cascade_matchfile.match",
            "item_for_template.png	some_template_matchfile.match",
            "item_for_autopy.png	some_autopy_matchfile.match",
            "item_for_text.txt	some_text_matchfile.match"
        ]
        self._build_chain(os.linesep.join(stepsfile_contents))

        calls = []
        for l in stepsfile_contents:
            item, match = l.split("\t")
            # we need to have a finder created for each .match file (inside Chain itself)
            calls.append(call(match))
            # and a finder for each target file (except for text and pattern items)
            if os.path.splitext(item)[1] not in [".txt", ".xml", ".csv"]:
                calls.append(call(os.path.splitext(item)[0] + ".match"))
        self.mock_match_read.assert_has_calls(calls)

    def test_steps_list(self):
        """Test that the resulting step chain contains all the items from the stepsfile."""
        stepsfile_contents = [
            "item_for_contour.png	some_contour_matchfile.match",
            "item_for_tempfeat.png	some_tempfeat_matchfile.match",
            "item_for_feature.png	some_feature_matchfile.match",
            "item_for_deep.csv	some_deep_matchfile.match",
            "item_for_cascade.xml	some_cascade_matchfile.match",
            "item_for_template.png	some_template_matchfile.match",
            "item_for_autopy.png	some_autopy_matchfile.match",
            "item_for_text.txt	some_text_matchfile.match"
        ]
        chain = self._build_chain(os.linesep.join(stepsfile_contents))
        expected_types = [Image, Image, Image, Pattern, Pattern, Image, Image, Text]
        self.assertEqual([type(s) for s in chain], expected_types)

    def test_step_save(self):
        """Test that dumping a chain to a file works and that the content is preserved."""
        # The Text target accepts either a file or a text string and we test
        # with both modes. For the first mode we need a real file.
        text_file = self._create_temp_file(prefix="some_text_file", extension=".txt")
        with open(text_file, "w") as fp:
            fp.write("ocr_string")

        # create real temp files for these -- they are saved using open() and we are not
        # mocking those calls. Also, the temp files will automatically be removed on tear down
        deep_csv = self._create_temp_file(prefix="item_for_deep", extension=".csv")
        cascade_xml = self._create_temp_file(prefix="item_for_cascade", extension=".xml")
        # no need to mock png files -- the Image target uses PIL.Image.save(), which we mocked

        # destination stepfile
        target_filename = self._create_temp_file(extension=".steps")

        stepsfile_contents = [
            "item_for_contour.png	some_contour_matchfile.match",
            "item_for_tempfeat.png	some_tempfeat_matchfile.match",
            "item_for_feature.png	some_feature_matchfile.match",
            "{}	some_deep_matchfile.match".format(deep_csv),
            "17	some_deep_matchfile.match",
            "{}	some_cascade_matchfile.match".format(cascade_xml),
            "item_for_template.png	some_template_matchfile.match",
            "item_for_autopy.png	some_autopy_matchfile.match",
            "{}	some_text_matchfile.match".format(os.path.splitext(text_file)[0]),
            "some_text_content	some_text_matchfile.match"
        ]

        expected_content = [
            "item_for_contour.png	item_for_contour.match",
            "item_for_tempfeat.png	item_for_tempfeat.match",
            "item_for_feature.png	item_for_feature.match",
            "{0}.csv	{0}.match".format(os.path.splitext(deep_csv)[0]),
            "17	17.match",
            "{0}.xml	{0}.match".format(os.path.splitext(cascade_xml)[0]),
            "item_for_template.png	item_for_template.match",
            "item_for_autopy.png	item_for_autopy.match",
            "{0}.txt	{0}.match".format(os.path.splitext(text_file)[0]),
            "some_text_content	some_text_content.match"
        ]

        source_stepsfile = self._create_temp_file(prefix=self.stepsfile_name,
            extension=".steps", contents=os.linesep.join(stepsfile_contents))

        FileResolver().add_path(os.path.dirname(text_file))
        try:
            chain = Chain(os.path.splitext(source_stepsfile)[0])
            chain.save(target_filename)

            with open(target_filename, "r") as f:
                generated_content = f.read().splitlines()

            # assert that the generated steps file has the expected content
            self.assertEqual(generated_content, expected_content)

            # build a list of the match filenames generated from
            # the calls to `Finder.to_match_file()`
            generated_match_names = []
            for c in self.mock_match_write.call_args_list:
               generated_match_names.append(c[0][1])

            # get a list
            expected_match_names = [x.split("\t")[1] for x in expected_content]
            expected_match_names.insert(0, os.path.splitext(source_stepsfile)[0] + ".match")

            # and assert that a match file was generated for each line
            # and for the steps file itself
            self.assertEqual(generated_match_names, expected_match_names)
        finally:
            FileResolver().remove_path(os.path.dirname(text_file))

    def test_malformed_stepsfile(self):
        """Test that the malformed stepsfiles are correctly handled."""
        stepsfile_contents = [
            "item_for_contour.png	some_contour_matchfile.match",
            "some_text_content	with	tabs	some_text_content.match"
        ]
        self.assertRaises(IOError, self._build_chain, os.linesep.join(stepsfile_contents))

        stepsfile_contents = [
            "item_for_contour.png	some_contour_matchfile.match",
            "some_text_content",
            "spanning multiple lines 	some_text_content.match"
        ]
        self.assertRaises(IOError, self._build_chain, os.linesep.join(stepsfile_contents))

    def test_invalid_backends(self):
        """Test that unsupported backends are detected when loading and saving."""
        # test on load
        stepsfile_contents = [
            "item_for_contour.png	some_contour_matchfile.match",
            "some_text_content	some_unknown_content.match"
        ]
        self.assertRaises(UnsupportedBackendError, self._build_chain, os.linesep.join(stepsfile_contents))

        # test on save
        finder = Finder(False, False)
        finder.params["find"] = { "backend": "unknown" }
        chain = self._build_chain("")
        chain._steps.append(Text("", finder))
        self.assertRaises(UnsupportedBackendError, chain.save, "foobar")

    def test_nested_stepsfiles(self):
        """Test that stepsfiles within stepsfiles are correctly handled."""
        # phisically create the files -- mocking os.open() would be too cumbersome
        stepsfile1 = self._create_temp_file(extension=".steps",
            contents="item_for_text.txt	some_text_matchfile.match")

        # second step file contains a reference to the first
        stepsfile2 = self._create_temp_file(extension=".steps",
            contents=stepsfile1)

        stepsfile3_contents = [
            "item_for_contour.png	some_contour_matchfile.match",
            "item_for_cascade.xml	some_cascade_matchfile.match",
            # third step file contains a reference to the second
            stepsfile2
        ]

        stepsfile3 = self._create_temp_file(prefix=self.stepsfile_name,
            extension=".steps", contents=os.linesep.join(stepsfile3_contents))

        chain = Chain(stepsfile3)
        expected_types = [Image, Pattern, Text]
        self.assertEqual([type(s) for s in chain._steps], expected_types)

    def test_nested_stepsfiles_order(self):
        """Test that stepsfiles within stepsfiles are loaded in order."""
        # phisically create the files -- mocking os.open() would be too cumbersome
        stepsfile1 = self._create_temp_file(extension=".steps",
            contents="item_for_text.txt	some_text_matchfile.match")
        stepsfile2 = self._create_temp_file(extension=".steps",
            contents="item_for_contour.png	some_contour_matchfile.match")

        stepsfile3_contents = [
            stepsfile1,
            "item_for_cascade.xml	some_cascade_matchfile.match",
            stepsfile2
        ]

        # second step file contains a reference to the third
        stepsfile3 = self._create_temp_file(prefix=self.stepsfile_name,
            extension=".steps", contents=os.linesep.join(stepsfile3_contents))

        chain = Chain(stepsfile3)
        expected_types = [Text, Pattern, Image]
        self.assertEqual([type(s) for s in chain._steps], expected_types)

if __name__ == '__main__':
    unittest.main()
