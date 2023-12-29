from guibot.region import Region
from guibot.fileresolver import FileResolver
from guibot.target import Image, Text
from guibot.finder import TextFinder

# add the paths to all target files through a more general file resolver
file_resolver = FileResolver()
file_resolver.add_path('D:\Work\Repositories\guibot\docs\examples\images')

# define more general targets like image instance (default from string before)
# and a text target to read out from the screen
some_image = Image('shape_blue_circle')
some_text = Text('Text')

# define a region instead of the previous guibot object capable of the same
# calls with the exception of path handling from the file resolver
image_region = Region()
# define a region with a different CV backend, namely a text finder with its
# default OCR backends (also can be found in the config module)
text_region = Region(cv=TextFinder())
# click on the image instance using all default settings and wait for it to vanish
image_region.double_click(some_image)
# hover the mouse on top of the text that was read from the screen but
# reusing the matched subregion
read_text = text_region.double_click(some_text)
assert read_text.similarity == 1.0, "Text read completely accurately"