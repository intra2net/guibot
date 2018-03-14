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

import copy
import os
import re
import PIL.Image

from config import GlobalConfig
from location import Location
from path import Path
from finder import *
from errors import *


class Target(object):
    """
    Target used to obtain screen location for clicking, typing,
    validation of expected visual output, etc.
    """

    @staticmethod
    def from_data_file(filename):
        """
        Read the target type from the extension of the target filename.

        :param str filename: data filename for the target
        :returns: target of type determined from its data filename extension
        :rtype: :py:class:`target.Target`
        :raises: :py:class:`errors.IncompatibleTargetFileError` if the data file if of unknown type
        """
        if not os.path.exists(filename):
            filename = Path().search(filename)
        basename = os.path.basename(filename)
        name, extension = os.path.splitext(basename)

        if extension in (".png", ".jpg"):
            target = Image(filename)
        elif extension == ".txt":
            target = Text(name)
        elif extension in (".xml", ".pth"):
            target = Pattern(filename)
        elif extension == ".steps":
            target = Chain(name)
        else:
            raise IncompatibleTargetFileError("The target file %s is not among any of the known types" % filename)

        return target

    @staticmethod
    def from_match_file(filename):
        """
        Read the target type and configuration from a match file with the given filename.

        :param str filename: match filename for the configuration
        :returns: target of type determined from its parsed (and generated) settings
        :rtype: :py:class:`target.Target`
        """
        if not os.path.exists(filename):
            filename = Path().search(filename)
        name = os.path.splitext(os.path.basename(filename))[0]
        match_filename = os.path.splitext(filename)[0] + ".match"
        finder = Finder.from_match_file(match_filename)

        if finder.params["find"]["backend"] in ("autopy", "contour", "template", "feature", "tempfeat"):
            target = Image(filename, match_settings=finder)
        elif finder.params["find"]["backend"] == "text":
            target = Text(name, match_settings=finder)
        elif finder.params["find"]["backend"] in ("cascade", "deep"):
            target = Pattern(filename, match_settings=finder)
        elif finder.params["find"]["backend"] == "hybrid":
            target = Chain(name, match_settings=finder)

        return target

    def __init__(self, match_settings=None):
        """
        Build a target object.

        :param match_settings: predefined configuration for the CV backend if any
        :type match_settings: :py:class:`finder.Finder` or None
        """
        self.match_settings = match_settings
        if self.match_settings != None:
            self.use_own_settings = True
        else:
            if GlobalConfig.find_backend == "autopy":
                self.match_settings = AutoPyFinder()
            elif GlobalConfig.find_backend == "contour":
                self.match_settings = ContourFinder()
            elif GlobalConfig.find_backend == "template":
                self.match_settings = TemplateFinder()
            elif GlobalConfig.find_backend == "feature":
                self.match_settings = FeatureFinder()
            elif GlobalConfig.find_backend == "cascade":
                self.match_settings = CascadeFinder()
            elif GlobalConfig.find_backend == "text":
                self.match_settings = TextFinder()
            elif GlobalConfig.find_backend == "tempfeat":
                self.match_settings = TemplateFeatureFinder()
            elif GlobalConfig.find_backend == "deep":
                self.match_settings = DeepFinder()
            elif GlobalConfig.find_backend == "hybrid":
                self.match_settings = HybridFinder()
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

    def load(self, filename):
        """
        Load target from a file.

        :param str filename: name for the target file

        If no local file is found, we will perform search in the
        previously added paths.
        """
        if not os.path.exists(filename):
            filename = Path().search(filename)
        match_filename = os.path.splitext(filename)[0] + ".match"
        if os.path.exists(match_filename):
            self.match_settings = Finder.from_match_file(match_filename)
            try:
                self.match_settings.synchronize()
            except UnsupportedBackendError:
                # some finders don't support synchronization
                pass
            self.use_own_settings = True

    def save(self, filename):
        """
        Save target to a file.

        :param str filename: name for the target file
        """
        match_filename = os.path.splitext(filename)[0] + ".match"
        if self.use_own_settings:
            Finder.to_match_file(self.match_settings, match_filename)

    def copy(self):
        """
        Perform a copy of the target data and match settings.

        :returns: copy of the current target (with settings)
        :rtype: :py:class:`target.Target`
        """
        selfcopy = copy.copy(self)
        copy_settings = self.match_settings.copy()
        selfcopy.match_settings = copy_settings
        return selfcopy

    def with_center_offset(self, xpos, ypos):
        """
        Perform a copy of the target data with new match settings
        and with a newly defined center offset.

        :param int xpos: new offset in the x direction
        :param int ypos: new offset in the y direction
        :returns: copy of the current target with new center offset
        :rtype: :py:class:`target.Target`
        """
        new_target = self.copy()
        new_target._center_offset = Location(xpos, ypos)
        return new_target

    def with_similarity(self, new_similarity):
        """
        Perform a copy of the target data with new match settings
        and with a newly defined required similarity.

        :param float new_similarity: new required similarity
        :returns: copy of the current target with new similarity
        :rtype: :py:class:`target.Target`
        """
        new_target = self.copy()
        new_target.match_settings.params["find"]["similarity"].value = new_similarity
        return new_target


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
        :type match_settings: :py:class:`finder.Finder` or None
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

    def load(self, filename, use_cache=True):
        """
        Load image from a file.

        :param str filename: name for the target file
        :param bool use_cache: whether to cache image data for better performance
        """
        super(Image, self).load(filename)
        if not os.path.exists(filename):
            filename = Path().search(filename)

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
        :rtype: :py:class:`target.Image`

        The image is compressed upon saving with a PNG compression setting
        specified by :py:func:`config.GlobalConfig.image_quality`.
        """
        super(Image, self).save(filename)
        filename += ".png" if os.path.splitext(filename)[1] != ".png" else ""
        self.pil_image.save(filename, compress_level=GlobalConfig.image_quality)

        new_image = self.copy()
        new_image._filename = filename

        return new_image


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
        :type match_settings: :py:class:`finder.Finder` or None
        """
        super(Text, self).__init__(match_settings)
        self.value = value
        self.text_file = None

        try:
            filename = Path().search(str(self) + ".txt")
            self.load(filename)
            self.text_file = filename
        except FileNotFoundError:
            # text generated on the fly is also acceptable
            pass

    def __str__(self):
        """Provide a part of the text value."""
        return self.value[:30]

    def load(self, filename):
        """
        Load text from a file.

        :param str filename: name for the target file
        """
        super(Text, self).load(filename)
        if not os.path.exists(filename):
            filename = Path().search(filename)
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

    def distance_to(self, str2):
        """
        Approximate Hungarian distance.

        :param str str2: string to compare to
        :returns: string distance value
        :rtype: float
        """
        str1 = self.value
        import numpy
        M = numpy.empty((len(str1) + 1, len(str2) + 1), numpy.int)

        for a in range(0, len(str1)+1):
            M[a,0] = a
        for b in range(0, len(str2)+1):
            M[0,b] = b

        for a in range(1, len(str1)+1):  #(size_t a = 1; a <= NA; ++a):
            for b in range(1, len(str2)+1):  #(size_t b = 1; b <= NB; ++b)
                z = M[a-1,b-1] + (0 if str1[a-1] == str2[b-1] else 1)
                M[a,b] = min(min(M[a-1,b] + 1, M[a,b-1] + 1), z)

        return M[len(str1),len(str2)]


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
        :type match_settings: :py:class:`finder.Finder` or None
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
            filename = Path().search(filename)
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


class Chain(Target):
    """
    Container for multiple configurations representing the same target.

    The simplest version of a chain is a sequence of the same match
    configuration steps performed on a sequence of images until one of them
    succeeds. Every next step in this chain is a fallback case if the previous
    step did not succeed.
    """

    def __init__(self, target_name, match_settings=None):
        """
        Build an chain object.

        :param str target_name: name of the target for all steps
        :param match_settings: predefined configuration for the CV backend if any
        :type match_settings: :py:class:`finder.Finder` or None
        """
        super(Chain, self).__init__(match_settings)
        self.target_name = target_name
        self._steps = []
        self.load(self.target_name+".steps")

    def __str__(self):
        """Provide the target name."""
        return self.target_name

    def __iter__(self):
        """Provide an interator over the steps."""
        return self._steps.__iter__()

    def load(self, steps_filename):
        """
        Load steps from a sequence definition file.

        :param str steps_filename: names for the sequence definition file
        :raises: :py:class:`errors.UnsupportedBackendError` if a chain step is of unknown type
        :raises: :py:class:`IOError` if an chain step line cannot be parsed
        """
        if not os.path.exists(steps_filename):
            steps_filename = Path().search(steps_filename)

        with open(steps_filename) as f:
            for step in f:
                dataconfig = re.split(r'\t+', step.rstrip('\t\n'))
                if len(dataconfig) != 2:
                    raise IOError("Invalid chain step line '%s'" % dataconfig[0])
                data, config = re.split(r'\t+', step.rstrip('\t\n'))

                super(Chain, self).load(config)
                self.use_own_settings = False

                step_backend = self.match_settings.params["find"]["backend"]
                if step_backend in ["autopy", "contour", "template", "feature", "tempfeat"]:
                    data_and_config = Image(data, match_settings=self.match_settings)
                elif step_backend in ["cascade", "deep"]:
                    data_and_config = Pattern(data, match_settings=self.match_settings)
                elif step_backend == "text":
                    data_and_config = Text(data, match_settings=self.match_settings)
                else:
                    # in particular, we cannot have a chain within the chain since it is not useful
                    raise UnsupportedBackendError("No target step type for '%s' backend" % step_backend)

                self._steps.append(data_and_config)

        # now define own match configuration
        super(Chain, self).load(steps_filename)

    def save(self, steps_filename):
        """
        Save steps to a sequence definition file.

        :param str steps_filename: names for the sequence definition file
        """
        super(Chain, self).save(self.target_name)
        save_lines = []
        for data_and_config in self._steps:
            config = data_and_config.match_settings
            data = data_and_config.match_settings

            step_backend = config.params["find"]["backend"]
            if step_backend in ["autopy", "contour", "template", "feature", "tempfeat"]:
                data = data_and_config.filename
            elif step_backend in ["cascade", "deep"]:
                data = data_and_config.data_file
            elif step_backend == "text":
                data = data_and_config.text_file
                if data is None:
                    raise ValueError("Target step text %s does not have a corresponding file"
                                     " - cannot save chain %s" % (data_and_config, self.target_name))
                data = Text(data, match_settings=self.match_settings)
            else:
                # in particular, we cannot have a chain within the chain since it is not useful
                raise UnsupportedBackendError("No target step type for '%s' backend" % step_backend)

            data_and_config.save(data)
            save_lines.append(data + " " + os.path.splitext(data)[0] + ".match")

        with open(steps_filename, "w") as f:
            f.writelines(save_lines)
