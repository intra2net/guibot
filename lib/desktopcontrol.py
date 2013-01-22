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
import logging
import time

import autopy.screen
import autopy.mouse

import PIL.Image
from tempfile import NamedTemporaryFile

from image import Image
from location import Location

class DesktopControl:
    def __init__(self):
        screen_size = autopy.screen.get_size()

        self.width = screen_size[0]
        self.height = screen_size[1]

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def capture_screen(self, *args):
        if len(args) == 4:
            xpos = args[0]
            ypos = args[1]
            width = args[2]
            height = args[3]
        elif len(args) == 1:
            region = args[0]
            xpos = region.get_x()
            ypos = region.get_y()
            width = region.get_width()
            height = region.get_height()
        else:
            xpos = 0
            ypos =  0
            width = self.width
            height = self.height

        # clipping
        if xpos > self.width:
            xpos = self.width - 1
        if ypos > self.height:
            ypos = self.height - 1

        if xpos + width > self.width:
            width = self.width - xpos
        if ypos + height > self.height:
            height = self.height - ypos

        # TODO: Switch to in-memory conversion. toString()
        # is a base64 encoded, zlib compressed stream.
        # Ask autopy author about a get_raw() method.
        with NamedTemporaryFile(prefix='guibender', suffix='.png') as f:
            autopy_bmp = autopy.bitmap.capture_screen(((xpos, ypos), (width, height)))
            autopy_bmp.save(f.name)

            pil_image = PIL.Image.open(f.name).convert('RGB')
            return Image(None, Image.DEFAULT_SIMILARITY, pil_image)

    def mouse_move(self, location):
        # Note: Sometimes this is not pixel perfect.
        # Need to investigate the autopy source later on
        autopy.mouse.smooth_move(location.get_x(), location.get_y())

    def get_mouse_location(self):
        autopy_pos = autopy.mouse.get_pos()
        return Location(autopy_pos[0], autopy_pos[1])

    def mouse_click(self):
        autopy.mouse.click()

    def mouse_right_click(self):
        autopy.mouse.click(autopy.mouse.RIGHT_BUTTON)

    def mouse_double_click(self):
        autopy.mouse.click()
        # TODO: Make double click speed configurable
        time.sleep(0.1)
        autopy.mouse.click()

    def write(self, text):
        autopy.keyboard.key.type_string(text)
