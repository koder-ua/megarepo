# wget functions for fabric
# use local cache for downloaded files
# first time file loaded to local share, using wget, and then to remote host
# next downloads requests file local cache and use put to transfer it to
# remote host

import os
import uuid

from fabric.contrib.files import exists
from fabric.api import local, put, sudo, run
from fablib.core import ensure, make_local_dir


def get_url_mapping(url, cfile):
    """
    look for that file from url in local cache
    return file name or None, if not founded
    should be executed under system-wide lock
    """
    try:
        map_file = open(cfile, 'r')
    except IOError:
        return None
    else:
        lines = map_file.readlines()
    
    try:
        return lines[lines.index(url) + 1]
    except:
        return None

def set_url_mapping(url, fname, cfile):
    "set mapping url->fname for local cache. \
        should be executed under system-wide lock"
    
    try:
        map_file = open(cfile, 'a+')
    except IOError:
        return None
    else:
        lines = map_file.readlines()
    
    try:
        pos = lines.index(url)
        if lines[pos + 1] != fname + "\n":
            lines[pos + 1] = fname + '\n'
        
        fd.seek(0, os.SEEK_SET)
        fd.write("".join(lines))
    except:
        fd.seek(0, os.SEEK_END)
        fd.write("{0}\n{1}\n".format(url, fname))

@ensure('wget')
def wget(url, opts="",
         use_sudo=False,
         file_cache='/tmp/wget_cache',
         cache_file='.cache_map'):
    
    if file_cache is not None:

        if not os.path.exists(file_cache):
            make_local_dir(file_cache)
            
        with open(os.path.join(file_cache, '.lock'),'w') as fd:
            # protect from race condition on cache access
            fcntl.lockf(fd, os.LOCK_EX)

            fname = url.split('/')[-1]
            if fname == '' or exists(os.path.join(file_cache, fname)):
                fname = url.replace('/', '_')
    
            cache_fname = os.path.join(file_cache, fname)
            if not os.path.exists(cache_fname):
    
                with lcd(file_cache):
                    local('wget -c ' + url)
                
            fcntl.lockf(fd, os.LOCK_UN)

            if os.path.exists(cache_fname):
                put(cache_fname, fname, use_sudo=use_sudo)
                return

    opts = opts.split(' ')
    
    (run if not use_sudo else sudo)(
            'wget -c {0} {1}'.format(' '.join(opts), url))





