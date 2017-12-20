**MATCH CONFIGURATION HIERARCHY**

In a simple case of image matching you can only define the path to the
needle and it will be performed for you. Example code for matching an
image */path/to/image\_folder/existing-image* is:

```
guibot.add_path('/path/to/image_folder')
guibot.find('existing-image')
```

However, one main disadvantage of this is that this matching requires
high default similarity and can be really fragile even if the slightest
change in the GUI occurs. You can of course use the calibrator to find
the match configuration for highest possible similarity in the new case
but it would be much better if you understand a little bit more about
how the match settings work and how modifying them a tiny bit can help
you achieve large flexibility of the *GUI scripts* and robustness to
insignificant changes in the GUI. So let's get started.

Next to any data file *existing-image.format* (here we assume image for
simplicity and therefore simpler backends) you can have a file to
contain its match settings with the name *existing-image.match*. If this
file exists, the match settings from it are automatically extracted and
used during the matching process of the respective image. Of course
there might be some cases where you need more specific match settings
so the match settings can always be processed further in the GUI
scripts you develop. Overall, this file ensures that you have reliable
long term configuration for matching the specific image. The file
however is specific for just one image. For all files without such
specific match settings, the defaults from the `GlobalConfig` object
are used. So all in all, the hierarchy of match configuration scopes
and overriding is the following:

1. `GlobalConfig` class - default settings for all targets every time
2. *target.match* file - default settings for a specific target every time
3. `target.match_settings` attribute - settings for a specific image
object (loaded image)
4. `region.finder` attribute - settings for a specific region

This allows for a kind of inheritance of the match configuration from
the most general to the most specific match cases. It is really necessary
since in real applications every time a needle image is matched, this
could be done with respect to different haystack images where there
might be different "distractions" relative to the actual match.

So to provide more details about the way to create more durable match
settings or temporary such we need to know the relevant API of the
classes `GlobalConfig`, `Target`, `Region`, and `Finder`. Every time you
perform matching you have to create `Image`, `Text`, `Pattern` or other
type of `Target` object depending on your preferred backend of use
(provided you have added the path to the image directory containing it)
and use that object as a needle image during matching. Of course you can
use that `Image` object multiple times in which case its last and most
current match configuration will be reused. If no match file was provided
the match settings will be the ones used for any matching and extracted
from the `GlobalConfig` class. Let's say that you need better match
settings for that specific image. For example if you want to change the
similarity required during each matching of this loaded image to 0.5 you
should do the following:

```
# run the next line once to use template default finder
GlobalConfig.find_backend = "template"
image = Image('existing-image')
image.use_own_settings = True
image.match_settings.params["find"]["similarity"].value = 0.5
```

We will explain more about the structure of the match settings a bit
later, this is just an example in order to see how to use the
`match_settings` attribute of the loaded image object. The new match
settings will be used in every matching where this `Image` object is
provided. You can be even more specific and change the match settings
for a single matching of the `Image` object (using `Region` as a more
ephemeral object than `Image`) by doing:

```
region = Region()
region.cv_backend.params["find"]["similarity"].value = 0.5
match = region.find('existing-image')
```

Notice however that in the long term this becomes cumbersome since you
would have to adapt the match configuration each time you load the image
or define a region. The way to solve this is to give more generality and
durability to the performed changes by saving them as a match file. You
can do so with:

```
image = Image('existing-image')
image.match_settings.params["find"]["similarity"].value = 0.5
image.use_own_settings = True
returned_image = image.save('/path/to/image_folder/existing-image.format')
```

This will additionally save a match file with the match configuration of
the image which will then be detected every next time you load the image:

```
image = Image('existing-image')
print image.use_own_settings
# True
print image.match_settings.params["find"]["similarity"].value
# 0.5
```

Are we good? All you need now is to know a bit more about the structure
of the match configuration and you are good to go.


**MATCH CONFIGURATION STRUCTURE**

Both the match configuration and backend implementation are carried out
within a *Finder* object. Knowing that, we can play with it more and go
beyond the hierarchy explained above by using custom match configuration
for multiple images and more. To create a few *Image* objects with the
same match settings you can do:

```
finder = TemplateFinder()
finder.params["find"]["similarity"].value = 0.5
image = Image('existing-image', match_settings=finder)
image2 = Image('existing-image2', match_settings=finder)
```

The configuration parameters or settings are organized into categories
(e.g. "find") and are objects of type `CVParameter`. The selection of
categories and parameters within each category depend on the choice of
computer vision backend. You can check the categories for a given backend
(i.e. `Finder` subclass) and the subalgorithm types they represent using

```
print finder.categories.keys()
# ['type', 'find', 'template']
print finder.categories
# {'type': 'backend_types', 'find': 'find_methods', 'template': 'template_matchers'}
```

You can then check the available and currently selected subalgorithms by

```
for category in finder.categories.keys():
    print finder.algorithms[finder.categories[category]]
    print "->", finder.params[category]["backend"]
# ('cv', 'dc')
# -> cv
# ('autopy', 'contour', 'template', 'feature', 'cascade', 'text', ...)
# -> template
# ('sqdiff_normed', 'ccorr_normed', 'ccoeff_normed')
# -> ccoeff_normed
```

To define a set of backend algorithms that you would like to use in
matching cases do:

```
finder.configure_backend(backend="sqdiff_normed", category="template")
```

or simply

```
finder.configure_backend(backend="sqdiff_normed")
```

Notice that if you replace a backend algorithm all relevant parameters
will be also replaced and if you set the same backend algorithm again
all relevant parameters will be set to the default. You can use a `reset`
flag to also rest all base category parameters but this is better
described in the API documentation of each backend. Parameters in a
base type are also parameters in a base category and are therefore more
general. In our example, the *similarity* parameter is more general, not
template spacific, and can be accessed from the base category *find* as

```
print finder.params["find"]["similarity"].value
# 0.5
```

An example of a less general parameter is *ScaleFactor* of a feature
finder. To access the *ScaleFactor* parameter of the ORB feature detector:

```
finder = FeatureFinder()
# optional if ORB is not the default feature detector
# finder.configure_backend(backend="ORB", category="fdetect")
# finder.synchronize_backend(backend="ORB", category="fdetect")
print finder.params["fdetect"]["ScaleFactor"].value
# 1.20000004768
```

Lastly, each parameter is a bit more complex than just a value. The
relevant attributes of a parameter are visible in any match file (which
of course is completely readable config file):

```
print finder.params["fdetect"]["ScaleFactor"]
<value='1.20000004768' min='1.01' max='2.0' delta='1.0' tolerance='0.1' fixed='True'>
```

From *min* and *max* we construct *range* tuple for the parameter object
which looks like

```
finder.params["fdetect"]["ScaleFactor"].range = (min, max)
```

If you don't care about calibration you don't need to know anything
about the other parameters. The *delta*, *tolerance*, and *fixed*
attributes are used by the calibrator where fixed would make the
calibrator skip calibrating the parameter. The other two would define
how much guessing will be used and when will the parameter have an
acceptable value for the calibrator.

The complexity behind the match configuration is a trade-off for the
availability of a unified configuration for all computer vision backends.
You need to read more about the specific computer vision algorithm to
know more about the specific backend parameters - this tutorial is
just to show you how to modify them and use the best methods you have
found for one or all of your images.
