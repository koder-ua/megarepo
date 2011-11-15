__doc__ = """
fabric recipe to install openstack
"""

import os

from fabric.api import *
from fabric.context_managers import *
from fabric.contrib.files import append

from fablib.core import install, \
                        put_rf, set_hosts, replace_in_file,\
                        get_tfile, upstart_restart

from fablib.recipes.sqldb.postgres import psql
    
nova_config = """
--dhcpbridge_flagfile=/etc/nova/nova.conf
--dhcpbridge=/usr/bin/nova-dhcpbridge
--logdir=/var/log/nova
--state_path=/var/lib/nova
--lock_path=/var/lock/nova
--state_path=/var/lib/nova
--verbose
--s3_host={0}
--rabbit_host={0}
--cc_host={0}
--ec2_url=http://{0}:8773/services/Cloud
--nova_url=http://{0}:8774/v1.1/
--fixed_range={1}
--network_size={2}
--FAKE_subdomain=ec2
--routing_source_ip={0}
--glance_api_servers={0}:9292
--image_service=nova.image.glance.GlanceImageService
--iscsi_ip_prefix={4}
--vlan_interface=eth0
--public_interface=eth0
--sql_connection=postgresql://novadbadmin:{3}@{0}/nova
"""

set_hosts(['ubuntu:ubuntu@nova'])

def install_nova(ip, net, net_prefix, lvm_dev,
                      ext_network, proj_name,
                      nova_adm='ubuntu',
                      dbpasswd='nova'):
    install('bridge-utils,postgresql,python-psycopg2')

    replace_in_file("/etc/postgresql/9.1/main/postgresql.conf",
            "#listen_addresses\s+=\s+'localhost'(.*)",
            r"listen_addresses = '*'\1", use_sudo=True)
        
    
    pg_hba = '/etc/postgresql/9.1/main/pg_hba.conf'
    add = "host    all         all             0.0.0.0/0       md5"
    
    sudo("chmod a+rw " + pg_hba)
    try:
        append(pg_hba, add)
    finally:
        sudo("chmod 640 " + pg_hba)
    
    
    sudo("/etc/init.d/postgresql restart")
    
    install('glance')
    cmd = "CREATE user glancedbadmin;\n" + \
          "ALTER user glancedbadmin with password '{0}';\n" + \
          'CREATE DATABASE glance;\n' + \
          'GRANT ALL PRIVILEGES ON database glance TO glancedbadmin;\n'
    
    psql(cmd.format(dbpasswd))
    
    glance_tempo_file = get_tfile()

    replace_in_file(glance_tempo_file,
            'sql_connection = .*?$',
            'sql_connection = postgresql://glancedbadmin:{0}@{1}/glance'\
                                .format(dbpasswd,ip),
            use_sudo=True)
    
    sudo('restart glance-registry')
    
    install('rabbitmq-server,nova-common,nova-doc,python-nova,nova-api,' + \
      'nova-network,nova-volume,nova-objectstore,nova-scheduler,' + \
      'nova-compute,euca2ools,unzip')
    
    cmd = 'CREATE user novadbadmin;\n' + \
          "ALTER user novadbadmin with password '{0}';\n" + \
          'CREATE DATABASE nova;\n' + \
          'GRANT ALL PRIVILEGES ON database nova TO novadbadmin;\n'
    
    psql(cmd.format(dbpasswd))

    cfg = nova_config.format(ip, net, '8', dbpasswd, net_prefix)
    put_rf('/etc/nova/nova.conf', cfg, use_sudo=True)

    install('iscsitarget,iscsitarget-dkms')

    sudo("sed -i 's/false/true/g' /etc/default/iscsitarget")
    sudo("service iscsitarget restart")
    sudo("pvcreate " + lvm_dev)
    sudo("vgcreate nova-volumes " + lvm_dev)
    sudo("chown -R root:nova /etc/nova")
    sudo("chmod 644 /etc/nova/nova.conf")
    
    all_nova_services = ('libvirt-bin,nova-network,nova-compute,nova-api,' + \
                'nova-objectstore,nova-scheduler,' + \
                'glance-api,glance-registry,nova-volume').split(',')
     
    for service in all_nova_services:
        upstart_restart(service)
    
    sudo('nova-manage db sync')

    sudo('nova-manage network create private {0} 1 255'.format(net))
    sudo('nova-manage floating create --ip_range=' + ext_network)
    sudo('nova-manage user admin novaadmin')
    sudo('nova-manage project create {0} novaadmin'.format(proj_name))

    for service in all_nova_services:
        upstart_restart(service)

    sudo('mkdir -p /home/{0}/creds'.format(nova_adm))
    
    sudo('nova-manage project zipfile proj novaadmin ' + \
         '/home/{0}/creds/novacreds.zip'.format(nova_adm))
    
    with cd('/home/{0}/creds'.format(nova_adm)):
        sudo('unzip novacreds.zip')
        sudo('chown {0}:{0} /home/{0}/creds -R'.format(nova_adm))

    res = sudo('nova-manage user exports novaadmin')
    
    EC2_ACCESS_KEY = None
    EC2_SECRET_KEY = None
    
    for string in str(res).split('\n'):
        string = string.strip()
        if string.startswith('export EC2_ACCESS_KEY='):
            EC2_ACCESS_KEY = string[len('export EC2_ACCESS_KEY='):]
        elif string.startswith('export EC2_SECRET_KEY='):
            EC2_SECRET_KEY = string[len('export EC2_SECRET_KEY='):]


    replace_in_file('/home/{0}/creds/novarc'.format(nova_adm),
            'export EC2_ACCESS_KEY="novaadmin:proj"'.format(proj_name),
            'export EC2_ACCESS_KEY="{0}:{1}"'.format(EC2_ACCESS_KEY, proj_name))

    replace_in_file('/home/{0}/creds/novarc'.format(nova_adm),
            'export NOVA_PROJECT_ID="proj"',
            'export NOVA_PROJECT_ID="{0}"'.format(proj_name))

    return

def install_swift():
    packages='swift,swift-proxy,memcached,swift-account,swift-container,' + \
             'swift-object,xfsprogs,curl'
    
    install(packages)

    
def main():
    install_nova(ip='192.168.122.225',
                 net='192.168.125.0/24',
                 net_prefix='192.168.125.',
                 lvm_dev='/dev/vdb',
                 ext_network='192.168.126.0/24',
                 proj_name='test')

