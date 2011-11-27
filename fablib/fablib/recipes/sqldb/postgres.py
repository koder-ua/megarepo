from fabric.api import run, sudo
from fablib.core import put_rf, get_tfile

def psql(cmd, user='postgres'):
    fname = get_tfile()
    put_rf(fname, cmd)
    
    try:
        sudo("""su - {0} -c "psql -f {1}" """.format(user, fname))
    finally:
        run('rm ' + fname)
