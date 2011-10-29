from fabric.api import env
from fablib.recipes.network import update_hosts
from fablib.core import curr_host

def find_vm_ips(vm_templ, conn_str="qemu:///session"):
    from little_cloud.libvirtex import open_libvirt
    conn = open_libvirt(conn_str)
    
    for vm in conn.allDomains(vm_templ):
        yield vm.name, [dev.ip for dev in vm.eths(with_ip=True)]

def vm2hosts(user, passwd):
    new_hosts = []
    
    env.ip2vm = {}

    for uri in ['qemu:///system', 'lxc://']:
        for vm_templ in env.hosts:
            for vm_name, ips in find_vm_ips(vm_templ, conn_str=uri):
                env.ip2vm[ips[0]] = vm_name
                new_hosts.append("{0}:{1}@{2}".format(user, passwd, ips[0]))
    
    return new_hosts

def update_network():
    from little_cloud.storage import get_all_vms
    
    vm2ip = {}
    
    for vm_name, iphw in get_all_vms("*"):
        vm2ip[vm_name] = iphw.values()[0]
    
    #print ip2vm
    #print curr_host()
    
    update_hosts(vm2ip)
        
       
