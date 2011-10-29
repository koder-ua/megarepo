import os
import re
from fabric.api import *
from fabric.context_managers import *
from fabric.contrib.files import exists

from fabis import check_cmd, ensure, get_rf, put_rf, replace_in_file, \
                   wget, add_apt_sources, check_dpkg, install


    
    
