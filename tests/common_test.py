#!/usr/bin/python
import os, sys

unittest_dir = os.path.dirname(os.path.abspath(__file__))
main_dir = os.path.join(unittest_dir, '..')
guibender_dir = os.path.join(main_dir, 'guibender')

# Add upper level 'guibender' directory to import path
# no matter from which directory we are called
sys.path.insert(0, guibender_dir)
