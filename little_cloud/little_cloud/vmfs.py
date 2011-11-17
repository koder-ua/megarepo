import os

import ipaddr
import guestfs

from IPython import embed

from vm_utils.utils import parse_hosts

static_ip = """
auto lo
iface lo inet loopback

# The primary network interface
auto eth0
iface eth0 inet static
address {ip}
netmask {mask}
network {network}
broadcast {bcast}
gateway {gw}
"""

class LocalGuestFS(object):
    def __init__(self, root):
        self.root = root
    
    def write(self, fname, val):
        open(os.path.join(self.root, fname), 'w').write(val)
        
    def read_file(self, path):
        return open(os.path.join(self.root, fname), 'r').read()
        
    
def set_image_network(g,
                      vm_name,
                      ip,
                      net_size,
                      add_to_hosts={},
                      gw=None):
 
    #hostname
    g.write('/etc/hostname', vm_name)
    
    #disable udev eth rename
    fc = 'SUBSYSTEM=="net", ACTION=="add", DRIVERS=="?*", ' + \
         'ATTR{address}=="*", ATTR{dev_id}=="0x0", ATTR{type}=="1", ' + \
         'KERNEL=="eth*", NAME="eth0"\n'
    g.write('/etc/udev/rules.d/70-persistent-net.rules', fc)
    
    #put static ip in /etc/network/interfaces
    network = ipaddr.IPNetwork("{0}/{1}".format(ip, net_size))
    
    if gw is None:
        gw = str(network.network + 1)
    
    intf = static_ip.format(ip=ip, mask=str(network.netmask),
                            network=str(network.network), gw=gw,
                            bcast=str(network.broadcast))

    g.write('/etc/network/interfaces', intf)    

    #update /etc/hosts
    res = []
    not_founded_hosts = set(add_to_hosts.keys())
    all_add_hosts = not_founded_hosts.copy()
    
    radd_to_hosts = [(v, k) for k, v in add_to_hosts.items()]
    
    for is_ip, obj in parse_hosts(g.read_file('/etc/hosts')):
        if not is_ip:
            res.append(obj)
        else:
            ip, all_hosts = obj
            
            if ip in radd_to_hosts:
                all_hosts = [radd_to_hosts[ip]]
                
                if radd_to_hosts[ip] in not_founded_hosts:
                    not_founded_hosts.remove(radd_to_hosts[ip])
                
            elif ip == '127.0.1.1' and vm_name is not None:
                all_hosts = [vm_name]
                if vm_name in not_founded_hosts:
                    not_founded_hosts.remove(vm_name)
            else:
                all_hosts = list(set(all_hosts).difference(all_add_hosts))
            
            res.append(" ".join([ip] + all_hosts))
    
    for host in not_founded_hosts:
        res.append("{0} {1}".format(add_to_hosts[host], host))
    
    g.write('/etc/hosts', "\n".join(res))

def set_all(image, format='qcow2'):
    if format == 'lxc':
        g = LocalGuestFS(image)
    else: 
        g = guestfs.GuestFS()
        g.add_drive_opts(image, format=format)
        g.launch()
        #print g.list_partitions()
        #print g.list_filesystems()
        #return
        g.mount('/dev/nova/root', '/')

    #set_image_network(g,
    #                  'nova',
    #                  '192.168.122.225',
    #                  24)
    set_apt_cache_proxy(g, '192.168.122.1')    

def set_apt_cache_proxy(g, ip):
    fc = 'Acquire::http {{ Proxy "http://{0}:3142"; }};'.format(ip)
    g.write('/etc/apt/apt.conf.d/02proxy', fc)

def mkimg(num):
    backing_store = '/home/koder/vm_images/ubuntu-kvm.qcow2'
    image = '/home/koder/vm_images/ubuntu-kvm-diff{0}.qcow2'.format(num) 
    
    if os.path.exists(image):
        os.unlink(image)
    
    os.system('qemu-img create -f qcow2 -b {0} {1}'.format(backing_store, image))
    
    set_image_network(image,
                      'nosql-{0}'.format(num),
                      '192.168.122.' + str(2 + num),
                      24)
#map(mkimg, [0, 1, 2, 3])
set_all('/home/koder/vm_images/ubuntu-server-nova.qcow2')
