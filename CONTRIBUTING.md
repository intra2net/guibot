# Requirements

Before submitting a pull request, there are a few basic requirements that would be nice to see on the branch.

Any suggestions to further standardize the submission requirements are welcome.

## Major requirements:

- autopep8 should be run for all modules
- pylint should be run for all modules
- pydocstyle should be run for all modules

## File nomenclature:

- use of short descriptive names
- unit test files accompanying utilities must be prepended with "test\_"

## Module documentation:

- there should not be any warnings from sphinx when the documentation is rebuilt for the new branch
- parameters, return values, exceptions should be defined for any method i.e. using one-line or two-line (with type) ":param" declarations
    - such explicitness gives us some information in a static type language)
    - private methods are exempted from such requirements - unit tests are exempted from such documentation requirements
    - properties and simple getters are exempted from such documentation requirements
- parameter and return value types should follow "Standard ML"-like style, e.g. "(int, str, {int, \[str\]})" will denote the type of a 3-tuple consisting of an "int", a "str", and a "dict mapping integers to lists of string"
    - using "str", "int", "bool" is not only brief but also produces links
    - type specification like "list", "tuple", "dict" is unclear about the contained types and must always be expanded to the above form without limit of the recursion (explicitness is preferred, too much nesting in a parameter implies that the parameter needs class refactoring)
- docstrings should follow a specific format, namely they should use punctuation, starting with one main sentence and details in a next paragraph if they are more than one sentence
    - in this way we support consistency of both single sentence and multi-sentence docstrings (which are unavoidable if details are needed), i.e. docstring are easily expandable which is their usual evolution
    - they are also nearly identical to commit and logging messages
- usage of actual variable/class/module names within a docstrings should be minimized unless the target has to be referred (using reST linking)
- if additionally mentioned, the following formatting is used
    - references (:py...) for modules, classes, and functions
    - interpreted text (...) for variables
    - emphasis (\*...\*) for filenames and paths
    - inline literal (\`...\`) for expressions
- don't add code author to any test/utility
    - it is ambiguous in the case of line changes by other developers
    - git already keeps track of authorship in much more detail

## Git documentation:

- branch naming should use dash-es instead of underscores
- commit messages should be typed similarly to the docstrings and to git's default commit messages e.g. "Merge branch ...", i.e. they should follow imperative mode for more git compatibility
    - they should have a blank line after a single subject line if additional details about motivation of the commit is needed
    - usage of a prefix word to identify affected system is optional but discouraged since it repeats existing/possible functionality of the git log
- small letters can imply temporary/unfinished commits

## Miscellaneous:

- in case you are writing a unit test or a utility which can be a standalone script, add the following shebang "\#!/usr/bin/python" as a first line of the file and a condition for running the module (default for python scripts) in the end of the file
    - in this was it is easy to see if a module is callable
- in case you are using UTF8 encoding, add the editor-neutral and human readable comment "\# This Python file uses the following encoding: utf-8" to the top of the file (under a shebang if there is such)
