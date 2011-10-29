from fabric.api import *
from fabric.context_managers import *

from fablib.core import install, set_hosts
from fablib.fab_os import set_apt_proxy, allow_all_sudo_no_passwd,\
                            set_service_run_at
from fablib.recipes import install_monitoring
from fablib.recipes.nosql import riak, cassandra, mongodb
from fablib.recipes.general import install_supervisord
from fablib.recipes.java import install_deb_java

from vm_fab import vm2hosts, update_network


set_hosts(vm2hosts('ubuntu', 'ubuntu'))

def crun(cmd):
    run(cmd.replace('+', ' '))

def csudo(cmd):
    sudo(cmd.replace('+', ' '))
    
def basic():
    set_apt_proxy('192.168.122.1', )
    install('gcc')
    install('python-pip')
    #install_supervisord()
    allow_all_sudo_no_passwd()
    
def sensor():
    install_monitoring.install_graphite_sensor('192.168.122.1:2003')
    
def allow_all_sudo():
    allow_all_sudo_no_passwd()
    
def riak():
    install_riak()
    prepare_node()

def riak_make_cluster():
    join_cluster()

def install_java():
    install_deb_java()

def install_cassandra():
    cassandra.install_deb()

def make_cassandra_cluster(*cluster):
    nosql.make_cassandra_cluster(*cluster)

def cassandra_cmd(cmd):
    nosql.cassandra(cmd)

def install_mongo():
    mongodb.install_mongo()
    
def remove_from_autoruns():
    set_service_run_at('mongodb',"","",upstart=True)
    set_service_run_at('cassandra',"","",upstart=False)

def network():
    update_network()
    
    