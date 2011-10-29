import os
import re

from fabric.api import *
from fabric.context_managers import *
from fabric.contrib.files import exists

from fablib.core import ensure, replace_in_file, check_cmd, install
from fablib.wget import wget
from fablib.fab_os import add_apt_sources

def install_src(ver='0.8.7'):
    cas_install_root = '/opt/cassandra'
    if exists(os.path.join(cas_install_root,
                           'apache-cassandra-{0}/bin/cassandra'.format(ver))):
        return
    
    if not exists(cas_install_root):
        sudo('mkdir ' + cas_install_root)
        
    fname = "apache-cassandra-{0}-bin.tar.gz".format(ver)
    wget('http://apache.vc.ukrtel.net//cassandra/{0}/{1}'.format(ver, fname))
    sudo('mv {0} {1}'.format(fname, cas_install_root))
    with cd(cas_install_root):
        sudo('tar -zxvf ' + fname)
        sudo('rm ' + fname)
        with cd('apache-cassandra-{0}'.format(ver)):
            sudo('mkdir -p /var/log/cassandra')
            name = str(run('whoami'))
            sudo('chown -R {0} /var/log/cassandra'.format(name))
            sudo('mkdir -p /var/lib/cassandra')
            sudo('chown -R {0} /var/lib/cassandra'.format(name))
            sudo(('ln -s /opt/cassandra/apache-cassandra-{0} ' + \
                     '/opt/cassandra/curr').format(ver))

rpc_addr_re = re.compile('^rpc_address:.*$')
listen_addr_re = re.compile('^listen_address:.*$')
seeds_re = re.compile('^(?P<tabs>\s*)- seeds: .*$')

def make_cluster(*cluster_ips):
    cip = env.host_string.split('@')[1]
    
    cluster_ips = list(cluster_ips)
    if cip in cluster_ips:
        cluster_ips.remove(cip)
    
    if check_dpkg('cassandra'):
        cfg_fl = '/etc/cassandra/cassandra.yaml'
    else:    
        cfg_fl = '/opt/cassandra/curr/conf/cassandra.yaml'
    
    fc = get_rf(cfg_fl)
    nfc = []
    for i in fc.split('\n'):
        if rpc_addr_re.match(i):
            i = "rpc_address: " + cip
        elif listen_addr_re.match(i):
            i = "listen_address: " + cip
        elif seeds_re.match(i):
            i = seeds_re.match(i).group('tabs') + "- seeds: " + \
                        '"{0}"'.format(",".join(cluster_ips))
        nfc.append(i)
    put_rf(cfg_fl, "\n".join(nfc), use_sudo=True)

def install_deb():
    if not check_cmd('cassandra'):
        add_apt_sources(False,
            'deb http://www.apache.org/dist/cassandra/debian 08x main',
            'deb-src http://www.apache.org/dist/cassandra/debian 08x main')
        run('gpg --keyserver pgpkeys.mit.edu --recv-keys F758CE318D77295D')
        sudo('apt-key add ~/.gnupg/pubring.gpg')
        sudo('apt-get update')
        install('cassandra')

def cassandra(cmd):
    sudo('/etc/init.d/cassandra ' + cmd)

def balance_cassandra_cluster(*cluster):
    cip = env.host_string.split('@')[1]
    pos = cluster.index(cip)
    token = (2 ** 127 / len(cluster)) * pos
    sudo('nodetool -h {0} move {1}'.format(cip, token))
