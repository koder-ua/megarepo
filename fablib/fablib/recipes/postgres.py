from fabric.api import *
from fabric.context_managers import *
from fabric.contrib.files import exists, append

from fablib.core import put_rf, get_tfile

def psql(cmd, user='postgres'):
    fname = get_tfile()
    put_rf(fname, cmd)
    
    try:
        sudo("""su - {0} -c "psql -f {1}" """.format(user, fname))
    finally:
        run('rm ' + fname)
