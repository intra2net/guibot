#!/usr/bin/python
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
import time, sys
import logging
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

CONFIG_FILENAME = "guiblender.cfg"
LOG_FILENAME = "guiblender.log"

class GuiBender(object):
    def __init__(self):
        self.load_config()
        self.prepare_log()

    def load_config(self):
        self.config = configparser.RawConfigParser()
        success = self.config.read(CONFIG_FILENAME)

        # if no file is found create a default one
        if(len(success)==0):
            if(not self.config.has_section('basic_settings')):
                self.config.add_section('basic_settings')
            self.config.set('basic_settings', 'file_log_level', logging.INFO)
            self.config.set('basic_settings', 'console_log_level', logging.INFO)
            # TODO: optional disable smooth_mouse for speed
            self.config.set('basic_settings', 'string_setting', 'stringvalue')
            self.config.set('basic_settings', 'bool_setting', "True")
            self.save_config()

        try:
            self.config.get('basic_settings', 'file_log_level')
            self.config.get('basic_settings', 'console_log_level')
            self.config.get('basic_settings', 'string_setting')
            self.config.getboolean('basic_settings', 'bool_setting')
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError) as ex:
            print("Could not read config file '%s': %s." % (CONFIG_FILENAME, ex))
            print("Please change or remove the config file.")
            sys.exit()

    def save_config(self):
        with open(CONFIG_FILENAME, 'w') as configfile:
            self.config.write(configfile)
            configfile.write("# 0 NOTSET, 10 DEBUG, 20 INFO, 30 WARNING, 40 ERROR, 50 CRITICAL\n")
            configfile.write("# Add further custom sections below\n\n")

    def prepare_log(self):
        # reset the log
        with open(LOG_FILENAME, 'w'):
            pass

        # add basic configuration
        logging.basicConfig(filename=LOG_FILENAME,
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=self.config.getint('basic_settings', 'file_log_level'))

        # add a handler for a console output
        console = logging.StreamHandler()
        console.setLevel(self.config.getint('basic_settings', 'console_log_level'))
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)
        return

    def execute_scriptlet(self, filename):
        pass

    def double_click(self):
        pass

# TODO: cmdline argument parsing
if __name__ == '__main__':
    BENDER = GuiBender()
    print "GuiBender instantiated"
    print "Logging level - " + BENDER.config.get("basic_settings", 'console_log_level')
