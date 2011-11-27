from fabric.api import sudo, env
from fabric.context_managers import *
from fabric.tasks import execute
from fablib.core import install, \
                        replace_in_file, \
                        check_cmd, \
                        check_pkg, \
                        curr_host, \
                        set_hosts

from fablib.fab_os import add_apt_sources

def install_mongo():
    if not check_pkg('mongodb-10gen'):
        add_apt_sources(False,
          'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart' + \
               ' dist 10gen')
        sudo('apt-key adv --keyserver keyserver.ubuntu.com --recv 7F0CEB10')
        sudo('apt-get update')
        install('mongodb-10gen')

cluster_config = {
    'shards' : [
        {'ip':'192.168.122.2', 'db':'/data/db'},
        #{'ip':'192.168.122.3', 'db':'/data/db'},
        #{'ip':'192.168.122.4', 'db':'/data/db'},
    ],
    'config' : {'ip':'192.168.122.5', 'db':'/data/db/config'},
    'mongos' : {'ip':'192.168.122.5'}
}

def start_cluster():
    for item in cluster_config['shards']:
        cfg = item.copy()
        ip = cfg.pop('ip')
        set_hosts(['ubuntu:ubuntu@' + ip], force=True)
        execute(start_shard, **cfg)
    
    cfg = cluster_config['config'].copy()
    ip = cfg.pop('ip')
    set_hosts(['ubuntu:ubuntu@' + ip], force=True)
    execute(start_config, **cfg)
        
    cfg = cluster_config['mongos'].copy()
    ip = cfg.pop('ip')
    set_hosts(['ubuntu:ubuntu@' + ip], force=True)
    execute(start_mongos, **cfg)

def start_shard(db):
    with settings(warn_only=True):
        sudo("mkdir -p " + db)
        sudo("/etc/init.d/mongodb stop")
        sudo("rm /tmp/shard.log")
        sudo(("nohup mongod --shardsvr --dbpath {0} " + \
             "--port 10000 > /tmp/shard.log & ls").format(db))

def start_config(db):
    print "Start config"
    return
    with settings(warn_only=True):
        sudo("mkdir -p " + db)
        sudo("/etc/init.d/mongodb stop")
        sudo("rm /tmp/shard_csrv.log")
        sudo(("nohup mongod --configsvr --dbpath {0} --port 20000" + \
             "> /tmp/shard_csrv.log & ls").format(db))

def start_mongos():
    print "Start mongos"
    return
    with settings(warn_only=True):
        sudo("/etc/init.d/mongodb stop")
        sudo("rm /tmp/mongos.log")
        sudo("nohup mongos --configdb localhost:20000 --chunkSize 1 > /tmp/mongos.log & ls")

if __name__ == "__main__":
    start_cluster()


    
