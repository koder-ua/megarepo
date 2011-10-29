import os
import re
import mock
import uuid
import warnings

from oktest import ok

from fabric.contrib.files import exists

from fablib import wget, core

from config import host

core.set_hosts([host])

def test_no_cache():
    url = "http://docs.python.org/library/fcntl.html"
    fname = url.split('/')[-1]
    
    rdir = "/tmp/{0!s}/{0!s}/{0!s}".format(
        uuid.uuid1(), uuid.uuid1(), uuid.uuid1())
    
    ok(exists(rdir)) == False
    core.make_remote_dir(rdir)
    ok(exists(rdir)) == True
    
    ldir = "/tmp/{0!s}".format(
        uuid.uuid1(), uuid.uuid1(), uuid.uuid1())
    
    ok(os.path.isdir(ldir)) == False
    core.make_local_dir(ldir)    
    ok(os.path.isdir(ldir)) == True
        
        
    sudo('rm')
    wget.wget()