#!/usr/bin/python
# Only needed if not installed system wide
import sys
sys.path.insert(0, '..')
# end here

#
# Program start here
#
# Load images/all_shapes.png with a picture viewer
# and it will print "Shapes exist"
#
from guibender.guibender_simple import *

add_image_path('images')

if exists('all_shapes'):
    print('Shapes exist')
else:
    print('Shapes do not exist')
