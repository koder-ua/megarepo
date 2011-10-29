import os
import time

import libvirt

from fabric.api import * 

from little_cloud.libvirtex import open_libvirt
from little_cloud.network import is_ssh_ready

def run_vm(img_path='/home/koder/vm_images/ubuntu-kvm-diff4.qcow2',
          backing_store='/home/koder/vm_images/ubuntu-kvm.qcow2'):
    img_path = os.path.abspath(img_path)
    backing_store = os.path.abspath(backing_store)
    
    if not os.path.exists(img_path):
        local(
            'qemu-img create -f qcow2 -b {0}  {1}'.format(backing_store,
                                                          img_path))
    
    conn = open_libvirt('qemu:///session')
    
    try:
        dom = conn.lookupByName('testvm')
    except libvirt.libvirtError:
        local('python -m little_cloud.main --start-set testvm')
    
    dom = conn.lookupByName('testvm')
    
    while not is_ssh_ready(dom.eths(with_ip=True)[0].ip):
        time.sleep(1)
        
    

def populate_vm():
    ff = '/home/koder/workspace/little_cloud/fab_recipes/all.py'
    
    names =[
            #'basic',
            #'sensor',
            #'install_java',
            #'install_cassandra',
            #'install_mongo',
            #'remove_from_autoruns',
            'network'
           ]
    
    local('fab --hosts nosql-5 -f {0} {1}'.format(ff,
                                          " ".join(names)))

#run_vm()
populate_vm()
