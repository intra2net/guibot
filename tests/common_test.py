#!/usr/bin/python
import os
import sys

unittest_dir = os.path.dirname(os.path.abspath(__file__))
main_dir = os.path.join(unittest_dir, '..')
guibot_dir = os.path.join(main_dir, 'guibot')

# Add upper level 'guibot' directory to import path
# no matter from which directory we are called
sys.path.insert(0, guibot_dir)
