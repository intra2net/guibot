#!/usr/bin/python
# Copyright 2013 Intranet AG / Thomas Jarosch and Plamen Dimitrov
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
import re, sys, os
import logging
try:
    import configparser
except ImportError:
    import ConfigParser as configparser
import argparse

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

if __name__ == '__main__':
    BENDER = GuiBender()
    logging.info("GuiBender instantiated")
    logging.info("Logging level - %s", BENDER.config.get("basic_settings", 'console_log_level'))

    # parse arguments
    parser = argparse.ArgumentParser(description="Tool for automatic GUI testing")
    parser.add_argument('-f', '--file', dest='testfile', action='store',
                        required=True, help='python script file to run')
    parser.add_argument('-c', '--code_snipplet', dest='snipplet', action='store',
                        default="", help='directory to run all test scripts from')
    parser.add_argument('-s', '--smooth', dest='smooth_mouse', action='store_true',
                        default=True, help="use smooth mouse motion to run the tests")
    args = parser.parse_args()

    if args.snipplet != "":
        logging.info("Running code snipplet %s from file %s", args.snipplet, args.testfile)
    else:
        logging.info("Running the file %s", args.testfile)
    if args.smooth_mouse:
        logging.info("Running the mouse in smooth mode")

    # TODO: correct relative paths in the unit tests
    # possibly make them usable from here using the code below
    execfile(args.testfile)


    # run all tests if test argument
    #testdir = os.path.join(os.path.dirname(__file__), "tests")
    #logging.info("Loading tests from directory %s", testdir)
    #for test_name in os.listdir(testdir):
    #    print "check " + test_name
    #    if re.match("test_\w+\.py", test_name) != None:
    #        logging.info("[Executing] %s" % test_name)
    #        execfile(os.path.join(testdir, test_name))
