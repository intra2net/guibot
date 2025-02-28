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

"""
Classes and functionality related to sought targets on screen.

SUMMARY
------------------------------------------------------


INTERFACE
------------------------------------------------------

"""

import copy
import os
import re
import PIL.Image
from typing import Iterator

from .config import GlobalConfig
from .location import Location
from .fileresolver import FileResolver
from .finder import *
from .errors import *


__all__ = ["Target", "Image", "Text", "Pattern", "Chain"]


class Target(object):
    """Target used to obtain screen location for clicking, typing, validation of expected visual output, etc."""

    @staticmethod
    def from_data_file(filename: str) -> "Target":
        """
        Read the target type from the extension of the target filename.

        :param filename: data filename for the target
        :returns: target of type determined from its data filename extension
        :raises: :py:class:`errors.IncompatibleTargetFileError` if the data file if of unknown type
        """
        if not os.path.exists(filename):
            filename = FileResolver().search(filename)
        basename = os.path.basename(filename)
        name, extension = os.path.splitext(basename)

        if extension in (".png", ".jpg"):
            target = Image(filename)
        elif extension == ".txt":
            target = Text(name)
        elif extension in (".xml", ".csv"):
            target = Pattern(filename)
        elif extension == ".steps":
            target = Chain(name)
        else:
            raise IncompatibleTargetFileError(
                "The target file %s is not among any of the known types" % filename
            )

        return target

    @staticmethod
    def from_match_file(filename: str) -> "Target":
        """
        Read the target type and configuration from a match file with the given filename.

        :param filename: match filename for the configuration
        :returns: target of type determined from its parsed (and generated) settings
        """
        if not os.path.exists(filename):
            filename = FileResolver().search(filename)
        name = os.path.splitext(os.path.basename(filename))[0]
        match_filename = os.path.splitext(filename)[0] + ".match"
        finder = Finder.from_match_file(match_filename)

        if finder.params["find"]["backend"] in (
            "autopy",
            "contour",
            "template",
            "feature",
            "tempfeat",
        ):
            target = Image(filename, match_settings=finder)
        elif finder.params["find"]["backend"] == "text":
            target = Text(name, match_settings=finder)
        elif finder.params["find"]["backend"] in ("cascade", "deep"):
            target = Pattern(filename, match_settings=finder)
        elif finder.params["find"]["backend"] == "hybrid":
            target = Chain(name, match_settings=finder)
        else:
            raise RuntimeError("Could not detect the target type from the find backend")

        return target

    def __init__(self, match_settings: "Finder" = None) -> None:
        """
        Build a target object.

        :param match_settings: predefined configuration for the CV backend if any
        """
        self.match_settings = match_settings
        if self.match_settings is not None:
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

    def __str__(self) -> str:
        """Provide a constant name 'target'."""
        return "target"

    def get_similarity(self) -> float:
        """
        Getter for readonly attribute.

        :returns: similarity required for the image to be matched
        """
        return self.match_settings.params["find"]["similarity"].value

    similarity = property(fget=get_similarity)

    def get_center_offset(self) -> Location:
        """
        Getter for readonly attribute.

        :returns: offset with respect to the target center (used for clicking)

        This clicking location is set in the target in order to be customizable,
        it is then taken when matching to produce a clicking target for a match.
        """
        return self._center_offset

    center_offset = property(fget=get_center_offset)

    def load(self, filename: str, **kwargs: dict[str, type]) -> None:
        """
        Load target from a file.

        :param filename: name for the target file

        If no local file is found, we will perform search in the
        previously added paths.
        """
        if not os.path.exists(filename):
            filename = FileResolver().search(filename)
        match_filename = os.path.splitext(filename)[0] + ".match"
        if os.path.exists(match_filename):
            self.match_settings = Finder.from_match_file(match_filename)
            try:
                self.match_settings.synchronize()
            except UnsupportedBackendError:
                # some finders don't support synchronization
                pass
            self.use_own_settings = True

    def save(self, filename: str) -> None:
        """
        Save target to a file.

        :param filename: name for the target file
        """
        match_filename = os.path.splitext(filename)[0] + ".match"
        if self.use_own_settings:
            Finder.to_match_file(self.match_settings, match_filename)

    def copy(self) -> "Target":
        """
        Perform a copy of the target data and match settings.

        :returns: copy of the current target (with settings)
        """
        selfcopy = copy.copy(self)
        copy_settings = self.match_settings.copy()
        selfcopy.match_settings = copy_settings
        return selfcopy

    def with_center_offset(self, xpos: int, ypos: int) -> "Target":
        """
        Perform a copy of the target data with new match settings and with a newly defined center offset.

        :param xpos: new offset in the x direction
        :param ypos: new offset in the y direction
        :returns: copy of the current target with new center offset
        """
        new_target = self.copy()
        new_target._center_offset = Location(xpos, ypos)
        return new_target

    def with_similarity(self, new_similarity: float) -> "Target":
        """
        Perform a copy of the target data with new match settings and with a newly defined required similarity.

        :param new_similarity: new required similarity
        :returns: copy of the current target with new similarity
        """
        new_target = self.copy()
        new_target.match_settings.params["find"]["similarity"].value = new_similarity
        return new_target


class Image(Target):
    """Container for image data supporting caching, clicking target, file operations, and preprocessing."""

    _cache = {}

    def __init__(
        self,
        image_filename: str = "",
        pil_image: PIL.Image.Image = None,
        match_settings: "Finder" = None,
        use_cache: bool = True,
    ) -> None:
        """
        Build an image object.

        :param image_filename: name of the image file if any
        :param pil_image: image data - use cache or recreate if none
        :param match_settings: predefined configuration for the CV backend if any
        :param use_cache: whether to cache image data for better performance
        """
        super(Image, self).__init__(match_settings)
        self._filename = image_filename
        self._pil_image: PIL.Image.Image = None
        self._width = 0
        self._height = 0

        if self._filename != "":
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

    def __str__(self) -> str:
        """Provide the image filename."""
        return (
            "noname"
            if self._filename == ""
            else os.path.splitext(os.path.basename(self._filename))[0]
        )

    def get_filename(self) -> str:
        """
        Getter for readonly attribute.

        :returns: filename of the image
        """
        return self._filename

    filename = property(fget=get_filename)

    def get_width(self) -> int:
        """
        Getter for readonly attribute.

        :returns: width of the image
        """
        return self._width

    width = property(fget=get_width)

    def get_height(self) -> int:
        """
        Getter for readonly attribute.

        :returns: height of the image
        """
        return self._height

    height = property(fget=get_height)

    def get_pil_image(self) -> PIL.Image.Image:
        """
        Getter for readonly attribute.

        :returns: image data of the image
        """
        return self._pil_image

    pil_image = property(fget=get_pil_image)

    def load(
        self, filename: str, use_cache: bool = True, **kwargs: dict[str, type]
    ) -> None:
        """
        Load image from a file.

        :param filename: name for the target file
        :param use_cache: whether to cache image data for better performance
        """
        super(Image, self).load(filename)
        if not os.path.exists(filename):
            filename = FileResolver().search(filename)

        # TODO: check if mtime of the file changed -> cache dirty?
        if use_cache and filename in self._cache:
            self._pil_image = self._cache[filename]
        else:
            # load and cache image
            with PIL.Image.open(filename) as pil_image:
                self._pil_image = pil_image.convert("RGB")
            if use_cache:
                self._cache[filename] = self._pil_image
        self._filename = filename

    def save(self, filename: str) -> "Image":
        """
        Save image to a file.

        :param filename: name for the target file
        :returns: copy of the current image with the new filename

        The image is compressed upon saving with a PNG compression setting
        specified by :py:func:`config.GlobalConfig.image_quality`.
        """
        super(Image, self).save(filename)
        filename += ".png" if os.path.splitext(filename)[-1] != ".png" else ""
        self.pil_image.save(filename, compress_level=GlobalConfig.image_quality)

        new_image: Image = self.copy()
        new_image._filename = filename

        return new_image


class Text(Target):
    """Container for text data which is visually identified using OCR or general text detection methods."""

    def __init__(
        self,
        value: str = None,
        text_filename: str = None,
        match_settings: "Finder" = None,
    ) -> None:
        """
        Build a text object.

        :param value: text value to search for
        :param text_filename: custom filename to read the text from
        :param match_settings: predefined configuration for the CV backend if any
        """
        super(Text, self).__init__(match_settings)
        self.value: str = value
        self.filename = text_filename

        try:
            filename = self.filename if self.filename else str(self) + ".txt"
            self.load(filename)
            self.filename = filename
        except FileNotFoundError:
            # text generated on the fly is also acceptable
            pass

    def __str__(self) -> str:
        """Provide a part of the text value."""
        return self.value[:30].replace("/", "").replace("\\", "")

    def load(self, filename: str, **kwargs: dict[str, type]) -> None:
        """
        Load text from a file.

        :param filename: name for the target file
        """
        super(Text, self).load(filename)
        if not os.path.exists(filename):
            filename = FileResolver().search(filename)
        with open(filename) as f:
            self.value = f.read()

    def save(self, filename: str) -> None:
        """
        Save text to a file.

        :param filename: name for the target file
        """
        super(Text, self).save(filename)
        filename += ".txt" if os.path.splitext(filename)[-1] != ".txt" else ""
        with open(filename, "w") as f:
            f.write(self.value)

    def distance_to(self, str2: str) -> float:
        """
        Approximate Hungarian distance.

        :param str2: string to compare to
        :returns: string distance value
        """
        str1 = str(self.value)
        import numpy

        M = numpy.empty((len(str1) + 1, len(str2) + 1), int)

        for a in range(0, len(str1) + 1):
            M[a, 0] = a
        for b in range(0, len(str2) + 1):
            M[0, b] = b

        for a in range(1, len(str1) + 1):  # (size_t a = 1; a <= NA; ++a):
            for b in range(1, len(str2) + 1):  # (size_t b = 1; b <= NB; ++b)
                z = M[a - 1, b - 1] + (0 if str1[a - 1] == str2[b - 1] else 1)
                M[a, b] = min(min(M[a - 1, b] + 1, M[a, b - 1] + 1), z)

        return M[len(str1), len(str2)]


class Pattern(Target):
    """Container for abstracted data which is obtained from training of a classifier in order to recognize a target."""

    def __init__(self, id: str, match_settings: "Finder" = None) -> None:
        """
        Build a pattern object.

        :param id: alphanumeric id of logit or label for the given pattern
        :param match_settings: predefined configuration for the CV backend if any
        """
        super(Pattern, self).__init__(match_settings)
        self.id = id
        self.data_file = None

        try:
            # base file name can be used as an ID for some finders like cascade
            base_name = str(self.id) if "." in str(self.id) else str(self.id) + ".csv"
            filename = FileResolver().search(base_name)
            self.load(filename)
        except FileNotFoundError:
            # pattern as a label from a reusable model is also acceptable
            pass

        # per instance match settings have the final word
        if match_settings is not None:
            self.match_settings = match_settings
            self.use_own_settings = True

    def __str__(self) -> str:
        """Provide the data filename."""
        return self.id

    def load(self, filename: str, **kwargs: dict[str, type]) -> None:
        """
        Load pattern from a file.

        :param filename: name for the target file
        """
        super(Pattern, self).load(filename)
        if not os.path.exists(filename):
            filename = FileResolver().search(filename)
        # loading the actual data is backend specific so only register its path
        self.data_file = filename

    def save(self, filename: str) -> None:
        """
        Save pattern to a file.

        :param filename: name for the target file
        """
        super(Pattern, self).save(filename)
        filename += ".csv" if "." not in str(self.id) else ""
        with open(filename, "wb") as fo:
            if self.data_file is not None:
                with open(self.data_file, "rb") as fi:
                    fo.write(fi.read())


class Chain(Target):
    """
    Container for multiple configurations representing the same target.

    The simplest version of a chain is a sequence of the same match
    configuration steps performed on a sequence of images until one of them
    succeeds. Every next step in this chain is a fallback case if the previous
    step did not succeed.
    """

    def __init__(self, target_name: str, match_settings: "Finder" = None) -> None:
        """
        Build an chain object.

        :param target_name: name of the target for all steps
        :param match_settings: predefined configuration for the CV backend if any
        """
        super(Chain, self).__init__(match_settings)
        self.target_name = target_name
        self._steps = []
        self.load(self.target_name)

    def __str__(self) -> str:
        """Provide the target name."""
        return self.target_name

    def __iter__(self) -> Iterator["Target"]:
        """Provide an interator over the steps."""
        return self._steps.__iter__()

    def load(self, steps_filename: str, **kwargs: dict[str, type]) -> None:
        """
        Load steps from a sequence definition file.

        :param steps_filename: names for the sequence definition file
        :raises: :py:class:`errors.UnsupportedBackendError` if a chain step is of unknown type
        :raises: :py:class:`IOError` if an chain step line cannot be parsed
        """

        def resolve_stepsfile(filename: str) -> str:
            """
            Try to find a valid steps file from a given file name.

            :param filename: full or partial name of the file to find
            :returns: valid path to a steps file
            """
            if not filename.endswith(".steps"):
                filename += ".steps"

            if not os.path.exists(filename):
                filename = FileResolver().search(filename)

            return filename

        # make sure we have the correct file
        steps_filename = resolve_stepsfile(steps_filename)
        stepsfiles_seen = [steps_filename]

        with open(steps_filename) as f:
            lines = f.readlines()

        while lines:
            step = lines.pop(0)
            dataconfig = re.split(r"\t+", step.rstrip("\t\n"))

            # read a nested steps file and append to this chain
            if dataconfig[0].endswith(".steps"):
                nested_steps_filename = resolve_stepsfile(dataconfig[0])
                # avoid infinite loops
                if nested_steps_filename not in stepsfiles_seen:
                    stepsfiles_seen.append(nested_steps_filename)
                    with open(nested_steps_filename) as f:
                        lines = f.readlines() + lines
                continue

            if len(dataconfig) != 2:
                raise IOError("Invalid chain step line '%s'" % dataconfig[0])

            data, config = dataconfig
            super(Chain, self).load(config)
            self.use_own_settings = False

            step_backend = self.match_settings.params["find"]["backend"]
            if step_backend in ["autopy", "contour", "template", "feature", "tempfeat"]:
                data_and_config = Image(data, match_settings=self.match_settings)
            elif step_backend in ["cascade", "deep"]:
                data_and_config = Pattern(data, match_settings=self.match_settings)
            elif step_backend == "text":
                if data.endswith(".txt"):
                    data_and_config = Text(
                        text_filename=data, match_settings=self.match_settings
                    )
                else:
                    data_and_config = Text(
                        value=data, match_settings=self.match_settings
                    )
            else:
                # in particular, we cannot have a chain within the chain since it is not useful
                raise UnsupportedBackendError(
                    "No target step type for '%s' backend" % step_backend
                )

            self._steps.append(data_and_config)

        # now define own match configuration
        super(Chain, self).load(steps_filename)

    def save(self, steps_filename: str) -> None:
        """
        Save steps to a sequence definition file.

        :param steps_filename: names for the sequence definition file
        """
        super(Chain, self).save(self.target_name)
        save_lines = []
        for data_and_config in self._steps:
            config = data_and_config.match_settings

            step_backend = config.params["find"]["backend"]
            if step_backend in ["autopy", "contour", "template", "feature", "tempfeat"]:
                data = data_and_config.filename
            elif step_backend in ["cascade", "deep"]:
                # special case - dynamic pattern without a filename
                # save only the matchfile and add the corresponding line
                if not data_and_config.data_file:
                    matchfile = str(data_and_config) + ".match"
                    Target.save(data_and_config, matchfile)
                    save_lines.append(data_and_config.id + "\t" + matchfile + "\n")
                    continue
                data = data_and_config.data_file
            elif step_backend == "text":
                # special case - dynamic text without a filename
                # save only the matchfile and add the corresponding line
                if not data_and_config.filename:
                    matchfile = str(data_and_config) + ".match"
                    Target.save(data_and_config, matchfile)
                    save_lines.append(data_and_config.value + "\t" + matchfile + "\n")
                    continue
                data = data_and_config.filename
            else:
                # in particular, we cannot have a chain within the chain since it is not useful
                raise UnsupportedBackendError(
                    "No target step type for '%s' backend" % step_backend
                )

            data_and_config.save(data)
            save_lines.append(data + "\t" + os.path.splitext(data)[0] + ".match\n")

        with open(steps_filename, "w") as f:
            f.writelines(save_lines)
