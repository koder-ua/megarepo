from fabric.api import sudo
from fablib.core import install, replace_in_file, check_cmd, check_pkg
from fablib.fab_os import add_apt_sources

def install_mongo():
    if not check_pkg('mongodb-10gen'):
        add_apt_sources(False,
          'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart' + \
               ' dist 10gen')
        sudo('apt-key adv --keyserver keyserver.ubuntu.com --recv 7F0CEB10')
        sudo('apt-get update')
        install('mongodb-10gen')
