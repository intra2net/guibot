Guibot
======

A tool for GUI automation using a variety of computer vision and desktop control backends.

.. note:: This is a complete guide on the concepts and usage of the Guibot python package and its interfaces. For a brief overview listing all backends and resources, see the project's README on Github. The resource links there are useful for information on installation, issue reporting, and advanced usage.

Main concepts
-------------

In order to do GUI automation you usually need to solve two problems: first, you need to have a way to control and interact with the interface and platform you are automating and second, you need to be able to locate the objects you are interested in on the screen. Guibot helps you do both.

To interact with GUIs, Guibot provides the `controller <https://guibot.readthedocs.io/en/latest/source/guibot.controller.html>`__ module which contains a common interface for different display backends, with methods to move the mouse, take screenshots, type characters and so on. The backend to use will depend on how your platform is accessible, with some backends running directly as native binaries or python scripts on Windows, macOS, and Linux while others connecting through remote VNC displays.

To locate an element on the screen, you will need an image representing the screen, a `target <https://guibot.readthedocs.io/en/latest/source/guibot.target.html>`__ representing the element (an image or a text in the simplest cases) and a `finder <https://guibot.readthedocs.io/en/latest/source/guibot.finder.html>`__ configured for the target. The finder looks for the target within the screenshot image and returns the coordinates to the region where that target appears. Finders, just like display controllers, are wrappers around different backends supported by Guibot that could vary from a simplest 1:1 pixel matching by controller backends, to template or feature matching mix by OpenCV, to OCR and ML solutions by Tesseract and AI frameworks.

Finally, to bridge the gap between controlling the GUI and finding target elements, the `region <https://guibot.readthedocs.io/en/latest/source/guibot.region.html>`__ module is provided. It represents a subregion of a screen and contains methods to locate targets in this region using a choice of finder and interact with the graphical interface using a choice of controller.

Main interfaces
---------------

There are three entry point interfaces that you can use to automate any GUI operations:

   * The guibot object from `guibot <https://guibot.readthedocs.io/en/latest/source/guibot.guibot.html>`__
   * The simple guibot module API from `guibot_simple <https://guibot.readthedocs.io/en/latest/source/guibot.guibot_simple.html>`__
   * The remote guibot API from `guibot_proxy <https://guibot.readthedocs.io/en/latest/source/guibot.guibot_proxy.html>`__

The recommended option for all standard use cases is the first one while the second is a simpler procedural form of it. The third interface can be used in more special circumstances where you are automating GUI operations on a remote machine and want to use less data intensive connection through PyRO serialization.

All three interfaces offer the same portfolio of functions: the functional capabilities of a region instance with a few added ones for file resolution. The function names must be self-explanatory so let's provide some examples:

::

    from guibot.guibot import GuiBot
    
    # initialize a starting region with default display controller and finder
    guibot = GuiBot()
    # add path to local ./images folder where we can find files needed for the target
    guibot.add_path('images')
    
    # this will look for ok_button.png within the added images folder, then look for
    # it on the screen and return true if it was found or false otherwise
    if guibot.exists('ok_button'):
        # find the button again and click on it
        guibot.click('ok_button')
    else:
        # type a text with our disappointment from the outcome
        guibot.type_text('Ok button does not exist')

This example code performs the simple actions of looking for a button using default CV and DC backends (listed and managed in the `config <https://guibot.readthedocs.io/en/latest/source/guibot.config.html>`__ module) and clicking on it if it was found or typing that it could not be found.

::

    from guibot.guibot import GuiBot
    
    guibot = GuiBot()
    guibot.add_path('account_images')
    
    # select account type on the screen as the second item from a drop down list
    # shifted 10 pixels below a text label that we provide an image of
    guibot.select_at("account-type", 2, 0, 10)
    # passively locate a big side panel region with 20s patience from animations
    menu_panel = guibot.find("account-options", timeout=20)
    # within the panel region click an option to show account credentials and
    # stay idle for an extra second until the credentials show up
    menu_panel.click("account-options-credentials").idle(1)
    # fill in the username "dumbledore" at a text box 100 pixels to the right of
    # a text label, pressing escape to avoid filled text suggestions
    guibot.fill_at("account-username", "dumbledore", 100, 0, esc_flag=True)
    # wait for a confirmation dialog to appear (more time tolerant)
    guibot.wait("account-name-confirmation")
    # pick the region to the topleft of the account login status
    topright_menu = guibot.find("account-login-status", timeout=20).left().above()
    # click on an exit button within the topleft region
    topright_menu.click("account-logout")

This example code performs a user login navigating through more complex controls and reusing previously matched regions. Since the guibot instance inherits these capabilities of a region instance and each one of these calls will return a resulting subregion, the region calls could be nested with each successive call operating on the result of the previous one. A more advance usage than this could simply import and directly initialize region instances with separate calls to a file resolver to add the necessary file paths instead of a single guibot instance.

::

    from guibot.region import Region
    from guibot.fileresolver import FileResolver
    from guibot.target import Image, Text
    from guibot.finder import TextFinder
    
    # add the paths to all target files through a more general file resolver
    file_resolver = FileResolver()
    file_resolver.add_path('target_data/')
    
    # define more general targets like image instance (default from string before)
    # and a text target to read out from the screen
    some_image = Image('shape_blue_circle')
    some_text = Text('Some text here')
    
    # define a region instead of the previous guibot object capable of the same
    # calls with the exception of path handling from the file resolver
    image_region = Region()
    # define a region with a different CV backend, namely a text finder with its
    # default OCR backends (also can be found in the config module)
    text_region = Region(cv=TextFinder())
    # click on the image instance using all default settings and wait for it to vanish
    image_region.click_vanish(some_image)
    # hover the mouse on top of the text that was read from the screen but
    # reusing the matched subregion
    read_text = text_region.hover(some_text)
    assert read_text.similarity == 1.0, "Text read completely accurately"

This final example makes the step of using a more general API based entirely on regions and does a simple change of a CV backend to read a text string from the screen. It also makes use of targets different than images and makes use of direct target instances rather than default strings (which are otherwise used to guess the target type). The text finder here is used for text detection and recognition (OCR) and offers further choice of backend implementations as well as specific parameters that can be used for fine-tuning (even calibrated) but this is the subject of more advanced tutorials.

Advanced tutorials
------------------

For more advanced usages feel free to explore our API here or visit some of the following tutorials:

   * A `tutorial <https://github.com/intra2net/guibot/wiki/Match-Settings-Tutorial>`__ on match settings explaining how to configure CV backends and fine tune CV parameters building on the last example above.
   * A `tutorial <https://github.com/intra2net/guibot/wiki/Image-Logging-Tutorial>`__ on image logging explaining how to debug GUI scripts written with Guibot.
   * A `tutorial <https://github.com/intra2net/guibot/wiki/Fallback-Chains-Tutorial>`__ on the most advanced types of targets and finders that rely on fallback chains and hybrid finder methods.
