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
import traceback
import logging
try:
    import configparser
except ImportError:
    import ConfigParser as configparser
import argparse

CONFIG_FILENAME = "guibender.cfg"
LOG_FILENAME = "guibender.log"

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

    def execute_script(self, filename):
        script_globals = {'__file__': filename, '__name__': '__main__', 'guibender' : self }

        my_dir = os.path.dirname(os.path.abspath(__file__))

        api_import = 'import sys\n'
        api_import += 'sys.path.insert(0, "' + my_dir + '")\n'
        api_import += 'from guibender_api import *\n'
        api_import += 'sys.path.pop(0)\n'
        api_import += 'init_guibender_api(guibender)\n'

        script_directory = os.path.dirname(os.path.abspath(filename))
        current_directory = os.getcwd()

        logging.info('Executing script: %s', filename)

        with open(filename, 'rb') as script:
            full_script = api_import + script.read()

            os.chdir(script_directory)
            try:
                exec(compile(full_script, filename, 'exec'), script_globals)
            except:
                print ('')
                print traceback.format_exc()
                logging.error('Script %s aborted by exception', filename)

            os.chdir(current_directory)

        logging.info('Script %s finished', filename)

    def api_callback(self):
        logging.info("Testing API call from script")

if __name__ == '__main__':
    guibender = GuiBender()

    logging.info("GuiBender instantiated")
    logging.info("Logging level - %s", guibender.config.get("basic_settings", 'console_log_level'))

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
    guibender.execute_script(args.testfile)

    # run all tests if test argument
    #testdir = os.path.join(os.path.dirname(__file__), "tests")
    #logging.info("Loading tests from directory %s", testdir)
    #for test_name in os.listdir(testdir):
    #    print "check " + test_name
    #    if re.match("test_\w+\.py", test_name) != None:
    #        logging.info("[Executing] %s" % test_name)
    #        execfile(os.path.join(testdir, test_name))
