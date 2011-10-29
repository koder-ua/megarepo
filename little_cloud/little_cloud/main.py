import time

import libvirt

from libvirtex import connection

VirtConnectionProxy = connection.VirtConnectionProxy

from storage import get_all_vms, Storage
from vm_sets import Sets
from vm_utils.utils import tmap
from vm_utils.network import is_host_alive
from vm_utils.cmd_executor import SSHCMDExecutor

expect_script = r'''
spawn ssh {0}@{1}
expect {{
    "password:" {{ send "{2}\n" }}
    "connecting (yes/no)?" {{ send "yes\n"; exp_continue}}
}}
interact
'''

def get_vm_ip(conn, vmname):
    vm = conn.lookupByName(vmname)
    update_net_from_storage(vm)
    return [eth.ip for eth in vm.eths(with_ip=True)]


def split_login(lline, user='ubuntu', passwd='ubuntu'):
    if '@' in lline:
        user_pass, host = lline.split('@')
        user, passwd = user_pass.split(':')
    else:
        host = lline
    return user, passwd, host

def update_net_from_storage(domain):
    try:
        hwip = Storage().get_vm(domain.name)
        
        hw2dev = dict((eth.hw, eth) for eth in domain.eths())
        
        hws = set(hwip.keys()).intersection(set(hw2dev.keys()))
        
        for hw in hws:
            hw2dev[hw].ip = hwip[hw]
        
    except KeyError:
        pass

if __name__ == "__main__":
    import sys
    import optparse
    import os
    
    parser = optparse.OptionParser()

    parser.add_option('--vm-ip', dest='get_ip', action='store_true',
                      default = False)
    parser.add_option('--conn', dest='conn_str',
                      default = "qemu:///session,lxc://")
    parser.add_option('--login', dest='login', action='store_true',
                      default = False)
    parser.add_option('--start-set', dest='start_set', action='store_true',
                      default = False)
    parser.add_option('--stop-set', dest='stop_set', action='store_true',
                      default = False)
    parser.add_option('--set-state', dest='set_state', action='store_true',
                      default = False)
    parser.add_option('--list-sets', dest='list_sets', action='store_true',
                      default = False)

    opts, files = parser.parse_args(sys.argv)
    
    uris = opts.conn_str.split(',')
    
    vconn = lambda : VirtConnectionProxy(*uris)
        
    if opts.get_ip:
        ips = get_vm_ip(vconn(), files[1])
        print ips[0]
    elif opts.login:
        
        user, passwd, vm_name = split_login(files[1])
        
        ip = None

        ip = get_vm_ip(vconn(), vm_name)[0]
        
        if ip is None:
            print "Can't found any sutable ip for domain {0}".format(vm_name)
        else:
            with open('/tmp/login.exp', 'w') as fd:
                fd.write(expect_script.format(user, ip, passwd))

            os.system("expect /tmp/login.exp")
    elif opts.list_sets:
        for name, tp in Sets.all():
            print "{0} {1}".format(tp, name)
    elif opts.start_set:
        if len(files) == 1:
            print >> sys.stderr, "Cluster name should be given"
        
        storage = Storage()
        for vm in Sets().start(files[1], vconn()):
            storage.set_vm(vm.name,
                       dict((eth.hw, eth.ip)
                            for eth in vm.eths(with_ip = True)))
            
            
    elif opts.set_state:
        if len(files) == 1:
            print >> sys.stderr, "vm name template should be given"
        
        conn = vconn()
        all_ips = {}
        is_alive = {}
        all_names = []

        for templ in files[1:]:
            if templ == 'ALL':
                templ = '*'
                
            for vm_name, ips in get_all_vms(templ):
                if len(ips) != 0:
                    ip = ips.values()[0]
                    all_names.append(vm_name)
                    try:
                        vm = conn.lookupByName(vm_name)
                        update_net_from_storage(vm)
                    except libvirt.libvirtError:
                        is_alive[vm_name] = False, None
                    else:
                        all_ips[ip] = vm_name
                else:
                    print vm_name.center(15), "No ip in database"
        
        for _, res_ip, res in tmap(is_host_alive, all_ips.keys()):
            is_alive[all_ips[res_ip]] = res, res_ip
        
        for vm_name in all_names:
            ok, ip = is_alive[vm_name]
            print vm_name.center(15),
            print "WORKS" if ok else "DOWN",
            print ip.center(15) if ip else ''
            
    elif opts.stop_set:
        if len(files) == 1:
            print >> sys.stderr, "vm name template should be given"
        
        conn = vconn()

        def shutdown_vm(val, max_time = 30):
            stime = time.time()
            conn, user, passwd, ip, name = val
            res = False

            if is_host_alive(ip):
                print "Power off {0}:{1}".format(name, ip)
                cmd = SSHCMDExecutor(ip, username, passwd)
                cmd.exec_simple(*('sudo poweroff'.split()))
            
            print "wait while {0}:{1} stop pinging".format(name, ip)
            
            while time.time() - stime < max_time:
                if not is_host_alive(ip):
                    res = True
                    break

            if time.time() - stime > max_time and not res:
                print "Timeouted {0}:{1}. Destory it".format(name, ip)
            else:
                print "{0}:{1} don't responce on ping anymore. Destory it".format(name, ip)

            try:
                vm = conn.lookupByName(name)
                update_net_from_storage(vm)
            except libvirt.libvirtError:
                pass
            else:
                vm.destroy()
                
            return True
            
        params = []
        
        for templ in files[1:]:
            username, passwd, vm_templ = split_login(templ)
            for vm_name, ips in get_all_vms(vm_templ):
                params.append([conn, username, passwd,
                               ips.values()[0], vm_name])
            
        for ok, param, res in tmap(shutdown_vm, params):
            print param[-1], res
    else:
        print "Unknown options!"
        

        






