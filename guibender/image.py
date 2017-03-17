# Copyright 2013 Intranet AG / Thomas Jarosch
#
# guibender is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# guibender is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with guibender.  If not, see <http://www.gnu.org/licenses/>.
#
import copy
import os
import PIL.Image
try:
    import configparser as config
except ImportError:
    import ConfigParser as config

from settings import GlobalSettings
from location import Location
from imagepath import ImagePath
from imagefinder import *


class Target(object):
    """
    Target used to obtain screen location for clicking, typing,
    validation of expected visual output, etc.
    """

    def __init__(self, match_settings=None):
        """
        Build a target object.

        :param match_settings: predefined configuration for the CV backend if any
        :type match_settings: :py:class:`imagefinder.ImageFinder` or None
        """
        self.match_settings = match_settings
        if self.match_settings != None:
            self.use_own_settings = True
        else:
            if GlobalSettings.find_image_backend == "autopy":
                self.match_settings = AutoPyMatcher()
            elif GlobalSettings.find_image_backend == "contour":
                self.match_settings = ContourMatcher()
            elif GlobalSettings.find_image_backend == "template":
                self.match_settings = TemplateMatcher()
            elif GlobalSettings.find_image_backend == "feature":
                self.match_settings = FeatureMatcher()
            elif GlobalSettings.find_image_backend == "cascade":
                self.match_settings = CascadeMatcher()
            elif GlobalSettings.find_image_backend == "text":
                self.match_settings = TextMatcher()
            elif GlobalSettings.find_image_backend == "hybrid":
                self.match_settings = HybridMatcher()
            elif GlobalSettings.find_image_backend == "deep":
                self.match_settings = DeepMatcher()
            self.use_own_settings = False

        self._center_offset = Location(0, 0)

    def __str__(self):
        """Provide a constant name 'target'."""
        return "target"

    def get_similarity(self):
        """
        Getter for readonly attribute.

        :returns: similarity required for the image to be matched
        :rtype: float
        """
        return self.match_settings.params["find"]["similarity"].value
    similarity = property(fget=get_similarity)

    def get_center_offset(self):
        """
        Getter for readonly attribute.

        :returns: offset with respect to the target center (used for clicking)
        :rtype: :py:class:`location.Location`

        This clicking location is set in the target in order to be customizable,
        it is then taken when matching to produce a clicking target for a match.
        """
        return self._center_offset
    center_offset = property(fget=get_center_offset)

    def load_configuration(self, filename_without_extention):
        """
        Read the configuration from a .match file with the given filename.

        :param str filename_without_extention: match filename for the configuration
        :returns: image finder with the parsed (and generated) settings
        :rtype: :py:class:`imagefinder.ImageFinder`
        :raises: :py:class:`IOError` if the respective match file couldn't be read
        """
        parser = config.RawConfigParser()
        # preserve case sensitivity
        parser.optionxform = str

        success = parser.read("%s.match" % filename_without_extention)
        # if no file is found throw an exception
        if len(success) == 0:
            raise IOError("Match file is corrupted and cannot be read")
        if not parser.has_section("find"):
            raise IOError("No image matching configuration can be found")
        try:
            backend_name = parser.get("find", 'backend')
        except config.NoOptionError:
            backend_name = GlobalSettings.find_image_backend

        if backend_name == "autopy":
            finder = AutoPyMatcher()
        elif backend_name == "template":
            finder = TemplateMatcher()
        elif backend_name == "feature":
            finder = FeatureMatcher()
        elif backend_name == "hybrid":
            finder = HybridMatcher()
        finder.from_match_file(filename_without_extention)
        return finder

    def save_configuration(self, filename_without_extention):
        """
        Write the configuration in a .match file with the given filename.

        :param str filename_without_extention: match filename for the configuration
        """
        if self.match_settings is None:
            raise IOError("No match settings available for saving at %s" % self)
        self.match_settings.to_match_file(filename_without_extention)

    def load(self, filename):
        """
        Load target from a file.

        :param str filename: name for the target file

        If no local file is found, we will perform search in the
        previously added paths.
        """
        if not os.path.exists(filename):
            filename = ImagePath().search(filename)
        filename_without_extesion = os.path.splitext(filename)[0]
        match_filename = filename_without_extesion + ".match"
        if os.path.exists(match_filename):
            self.match_settings = self.load_configuration(filename_without_extesion)
            self.use_own_settings = True

    def save(self, filename):
        """
        Save target to a file.

        :param str filename: name for the target file
        """
        filename_without_extesion = os.path.splitext(filename)[0]
        if self.use_own_settings:
            self.save_configuration(filename_without_extesion)


class Image(Target):
    """
    Container for image data supporting caching, clicking target,
    file operations, and preprocessing.
    """

    _cache = {}

    def __init__(self, image_filename=None,
                 pil_image=None, match_settings=None,
                 use_cache=True):
        """
        Build an image object.

        :param image_filename: name of the image file if any
        :type image_filename: str or None
        :param pil_image: image data - use cache or recreate if none
        :type pil_image: :py:class:`PIL.Image` or None
        :param match_settings: predefined configuration for the CV backend if any
        :type match_settings: :py:class:`imagefinder.ImageFinder` or None
        :param bool use_cache: whether to cache image data for better performance
        """
        super(Image, self).__init__(match_settings)
        self._filename = image_filename
        self._pil_image = None
        self._width = 0
        self._height = 0

        if self._filename is not None:
            self.load(self._filename, use_cache)
        # per instance pil image has the final word
        if pil_image is not None:
            self._pil_image = pil_image
        # per instance match settings have the final word
        if match_settings is not None:
            self.match_settings = match_settings
            self.use_own_settings = True

        if self._pil_image:
            self._width = self._pil_image.size[0]
            self._height = self._pil_image.size[1]

    def __str__(self):
        """Provide the image filename."""
        return "noname" if self._filename is None else os.path.splitext(os.path.basename(self._filename))[0]

    def get_filename(self):
        """
        Getter for readonly attribute.

        :returns: filename of the image
        :rtype: str
        """
        return self._filename
    filename = property(fget=get_filename)

    def get_width(self):
        """
        Getter for readonly attribute.

        :returns: width of the image
        :rtype: int
        """
        return self._width
    width = property(fget=get_width)

    def get_height(self):
        """
        Getter for readonly attribute.

        :returns: height of the image
        :rtype: int
        """
        return self._height
    height = property(fget=get_height)

    def get_pil_image(self):
        """
        Getter for readonly attribute.

        :returns: image data of the image
        :rtype: :py:class:`PIL.Image`
        """
        return self._pil_image
    pil_image = property(fget=get_pil_image)

    def copy(self):
        """
        Perform a copy of the image data and match settings.

        :returns: copy of the current image (with settings)
        :rtype: :py:class:`image.Image`
        """
        copy_settings = copy.deepcopy(self.match_settings)
        selfcopy = copy.copy(self)
        selfcopy.match_settings = copy_settings
        return selfcopy

    def with_target_offset(self, xpos, ypos):
        """
        Perform a copy of the image data without match settings
        and with a newly defined target offset.

        :param int xpos: new offset in the x direction
        :param int ypos: new offset in the y direction
        :returns: copy of the current image with new target offset
        :rtype: :py:class:`image.Image`
        """
        new_image = self.copy()

        new_image._center_offset = Location(xpos, ypos)
        return new_image

    def with_similarity(self, new_similarity):
        """
        Perform a copy of the image data without match settings
        and with a newly defined required similarity.

        :param float new_similarity: new required similarity
        :returns: copy of the current image with new similarity
        :rtype: :py:class:`image.Image`
        """
        new_image = self.copy()
        new_image.match_settings.params["find"]["similarity"].value = new_similarity
        return new_image

    def exact(self):
        """
        Perform a copy of the image data without match settings
        and with a maximum required similarity.

        :returns: copy of the current image with maximum similarity
        :rtype: :py:class:`image.Image`
        """
        return self.with_similarity(1.0)

    def load(self, filename, use_cache=True):
        """
        Load image from a file.

        :param str filename: name for the target file
        :param bool use_cache: whether to cache image data for better performance
        """
        super(Image, self).load(filename)
        if not os.path.exists(filename):
            filename = ImagePath().search(filename)

        # TODO: check if mtime of the file changed -> cache dirty?
        if use_cache and filename in self._cache:
            self._pil_image = self._cache[filename]
        else:
            # load and cache image
            self._pil_image = PIL.Image.open(filename).convert('RGB')
            if use_cache:
                self._cache[filename] = self._pil_image
        self._filename = filename

    def save(self, filename):
        """
        Save image to a file.

        :param str filename: name for the target file
        :returns: copy of the current image with the new filename
        :rtype: :py:class:`image.Image`

        The image is compressed upon saving with a PNG compression setting
        specified by :py:func:`settings.GlobalSettings.image_quality`.
        """
        super(Image, self).save(filename)
        filename += ".png" if os.path.splitext(filename)[1] != ".png" else ""
        self.pil_image.save(filename, compress_level=GlobalSettings.image_quality)

        new_image = self.copy()
        new_image._filename = filename

        return new_image


class ImageSet(Target):
    """
    Container for multiple images representing the same target.

    This is a simple step towards greater robustness where we can
    supply a set of images and match on just one of them.
    """

    def __init__(self, group_name, images=None, match_settings=None, use_cache=True):
        """
        Build an image set object.

        :param images: name of the image file if any
        :type images: [:py:class:`Image`] or None
        :param match_settings: predefined configuration for the CV backend if any
        :type match_settings: :py:class:`imagefinder.ImageFinder` or None
        :param bool use_cache: whether to cache image data for better performance
        """
        super(ImageSet, self).__init__(match_settings)
        if images is None:
            self._images = []
        else:
            self._images = images
        self.group_name = group_name

    def __str__(self):
        """Provide the group name."""
        return self.group_name

    def __iter__(self):
        """Provide an interator over the images."""
        return self._images.__iter__()

    def load(self, filenames, use_cache=True):
        """
        Load images from their files.

        :param filenames: names for the target files
        :type filenames: [str]
        :param bool use_cache: whether to cache image data for better performance
        """
        super(ImageSet, self).load(self.group_name)
        for filename in filenames:
            new_image = Image(image_filename=filename, use_cache=use_cache)
            self.images.append(new_image)

    def save(self, filenames):
        """
        Save images to their files.

        :param filenames: name for the target file
        :type filenames: [str]
        """
        super(ImageSet, self).save(self.group_name)
        assert len(self.images) == len(filenames), "Provided filenames must be as many as the contained images"
        for image, filename in zip(self.images, filenames):
            image.save(filename)


class Text(Target):
    """
    Container for text data which is visually identified
    using OCR or general text detection methods.
    """

    def __init__(self, value, match_settings=None):
        """
        Build a text object.

        :param str value: text value to search for
        :param match_settings: predefined configuration for the CV backend if any
        :type match_settings: :py:class:`imagefinder.ImageFinder` or None
        """
        super(Text, self).__init__(match_settings)
        self.value = value

        try:
            filename = ImagePath().search(str(self) + ".txt")
            self.load(filename)
        except FileNotFoundError:
            # text generated on the fly is also acceptable
            pass

    def __str__(self):
        """Provide a part of the text value."""
        return self.value[:10]

    def load(self, filename):
        """
        Load text from a file.

        :param str filename: name for the target file
        """
        super(Text, self).load(filename)
        if not os.path.exists(filename):
            filename = ImagePath().search(filename)
        with open(filename) as f:
            self.value = f.read()

    def save(self, filename):
        """
        Save text to a file.

        :param str filename: name for the target file
        """
        super(Text, self).save(filename)
        with open(filename, "w") as f:
            f.write(self.value)


class Pattern(Target):
    """
    Container for abstracted data which is obtained from
    training of a classifier in order to recognize a target.
    """

    def __init__(self, data_filename, match_settings=None):
        """
        Build a pattern object.

        :param str data_filename: name of the text file if any
        :param match_settings: predefined configuration for the CV backend if any
        :type match_settings: :py:class:`imagefinder.ImageFinder` or None
        """
        super(Pattern, self).__init__(match_settings)
        self.data_file = None
        self.load(data_filename)
        # per instance match settings have the final word
        if match_settings is not None:
            self.match_settings = match_settings
            self.use_own_settings = True

    def __str__(self):
        """Provide the data filename."""
        return os.path.splitext(os.path.basename(self.data_file))[0]

    def load(self, filename):
        """
        Load pattern from a file.

        :param str filename: name for the target file
        """
        super(Pattern, self).load(filename)
        if not os.path.exists(filename):
            filename = ImagePath().search(filename)
        self.data_file = filename

    def save(self, filename):
        """
        Save pattern to a file.

        :param str filename: name for the target file
        """
        super(Pattern, self).save(filename)
        with open(filename, "w") as fo:
            with open(self.data_file, "r") as fi:
                fo.write(fi.read())
