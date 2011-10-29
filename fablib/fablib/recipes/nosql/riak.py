from fabric.api import *
from fabric.context_managers import *
from fabric.contrib.files import exists

from fablib.core import ensure, replace_in_file, check_cmd

riak_url = "http://downloads.basho.com/riak/riak-1.0.0/riak_1.0.0-1_amd64.deb"

@ensure("wget")
def install_riak():
    if not check_cmd('riak'):
        with cd('/tmp'):
            if not exists('riak_1.0.0-1_amd64.deb'):
                run('wget ' + riak_url)
            sudo('dpkg -i riak_1.0.0-1_amd64.deb')

def start_riak():
    sudo("riak start")

def stop_riak():
    sudo("riak stop")

def prepare_node():
    with settings(hide('warnings', 'stderr'), warn_only=True):
        stop_riak()

    ip = env.host_string.split('@')[1]
    
    if replace_in_file('/etc/riak/vm.args',
                       '-name riak@127.0.0.1',
                       '-name riak@' + ip,
                       use_sudo=True):
        
        replace_in_file('/etc/riak/app.config',
                '{http, [ {"127.0.0.1", 8098 } ]}',
                '{{http, [ {{"{0}", 8098 }} ]}}'.format(ip),
                 use_sudo=True)

        with settings(hide('warnings', 'stderr'), warn_only=True):
            sudo("riak-admin reip riak@127.0.0.1 riak@{0}".format(
                 env.host_string.split('@')[1]))
    
def join_cluster():
    root = env.hosts[0]
    
    if not env.host_string == root:
        join_to = root.split('@')[1]
        sudo("riak-admin join riak@" + join_to)
