# appengine_config.py
import pkg_resources
from google.appengine.ext import vendor

import os

PATH=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')

# Add any libraries install in the "lib" folder.
vendor.add(PATH)

# Add libraries to pkg_resources working set to find the distribution.
pkg_resources.working_set.add_entry(PATH)
