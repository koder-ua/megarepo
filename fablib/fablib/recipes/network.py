import ipaddr

from fabric.api import *
from fablib.core import remote_fl, put_rf, get_rf
from utils import parse_hosts

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

def set_static_ip(ip_and_sz, gw=None):
    network = ipaddr.IPNetwork(ip_and_sz)
    ip = ip_and_sz.split('/',1)[0]
    
    if gw is None:
        gw = str(network.network + 1)
    
    nnew = static_ip.format(ip=ip, mask=str(network.netmask), gw=gw,
                            bcast=str(network.broadcast))
    put_rf('/etc/network/interfaces', nnew, use_sudo=True)

def update_hosts(hostname2ip, update_hostname=True):

    ip2hostname = dict((v,k) for k,v in hostname2ip.items())
    all_host_names = set(hostname2ip.keys())
    
    curr_hostname = ip2hostname.get(env.host_string.split('@')[1], None)
    update_hostname = update_hostname and curr_hostname is not None

    if update_hostname:
        set_host_name(curr_hostname)
    
    res = []
    not_founded_hosts = set(all_host_names)
    
    with remote_fl('/etc/hosts', use_sudo=True) as hosts:
        for is_ip, obj in parse_hosts(hosts.getvalue()):
            if not is_ip:
                res.append(obj)
            else:
                ip, all_hosts = obj
                
                if ip in ip2hostname:
                    all_hosts = [ip2hostname[ip]]
                    
                    if ip2hostname[ip] in not_founded_hosts:
                        not_founded_hosts.remove(ip2hostname[ip])
                    
                elif ip == '127.0.1.1' and curr_hostname is not None:
                    all_hosts = [curr_hostname]
                    if curr_hostname in not_founded_hosts:
                        not_founded_hosts.remove(curr_hostname)
                else:
                    all_hosts = list(set(all_hosts).difference(all_host_names))
                
                res.append(" ".join([ip] + all_hosts))
        
        for host in not_founded_hosts:
            res.append("{0} {1}".format(hostname2ip[host], host))
        
        hosts.setvalue("\n".join(res))
            
    if update_hostname:
        sudo("/etc/init.d/hostname restart")
        
    sudo("/etc/init.d/networking restart")

def set_host_name(name):
    fc = get_rf('/etc/hostname')
    if name != fc.strip():
        put_rf('/etc/hostname', name, use_sudo=True)

def add_to_hosts(host, ip):
    cont = get_rf('/etc/hosts')

    for i in cont.split('\n'):
        i = i.strip()
        if i.startswith('#') or i == '' or ' ' not in i:
            continue
        
        fip, fhost = i.split(' ', 1)
        if fhost.strip() == host and fip.strip() == ip:
            return
    
    put_rf('/etc/hosts', cont + '\n{} {}'.format(ip,host))


