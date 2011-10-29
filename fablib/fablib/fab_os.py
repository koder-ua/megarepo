from fabric.api import sudo, env
from fabric.context_managers import *
from fabric.contrib.files import exists

from core import get_rf, put_rf

def users():
    fl = get_rf('/etc/passwd')
    for i in fl.split('\n'):
        yield i.split(':',1)

def disable_udev_eth_rename():
    fc = 'SUBSYSTEM=="net", ACTION=="add", DRIVERS=="?*", ' + \
         'ATTR{address}=="*", ATTR{dev_id}=="0x0", ATTR{type}=="1", ' + \
         'KERNEL=="eth*", NAME="eth0"\n'
    put_rf('/etc/udev/rules.d/70-persistent-net.rules', fc, use_sudo=True)

def allow_all_sudo_no_passwd():
    sudo('sudo cp /etc/sudoers /tmp/sudoers')
    sudo('chmod a+r /tmp/sudoers')
    fc = get_rf('/tmp/sudoers')
    sudo('rm /tmp/sudoers')

    ln = "ALL ALL=(ALL)NOPASSWD: ALL"
    if ln not in fc:
        put_rf('/tmp/sudoers', fc + '\n' + ln)
        
        sudo('chmod 0440 /tmp/sudoers')
        sudo('chown root.root /tmp/sudoers')
    
        sudo('mv /tmp/sudoers /etc/sudoers')

    
def add_apt_sources(auto_update=True, *sources):
    fc = get_rf('/etc/apt/sources.list')
    updated = False
    
    for source in sources:
        if source not in fc:
            if not fc.endswith('\n'):
                fc += '\n'
            fc += source + "\n"
            updated = True
    
    if updated:
        put_rf('/etc/apt/sources.list', fc, use_sudo=True)
        if auto_update:
            sudo('apt-get update')
    return updated

def set_apt_proxy(proxy_host, proxy_port=3142):
    fname = '/etc/apt/apt.conf.d/02proxy'
    proxy = 'Acquire::http {{ Proxy "http://{0}:{1}"; }};'
    proxy = proxy.format(proxy_host, proxy_port)
    
    if exists(fname):
        fd = get_rf(fname)
    else:
        fd = ''
        
    if fd != proxy:
        put_rf(fname, proxy, use_sudo=True)
            

def set_service_run_at(name, start_levels, stop_levels,
                          prior='80', upstart=False):
    if upstart:
        fname = '/etc/init/{0}.conf'.format(name)
        fl = get_rf(fname)
        nfl = []
        for i in fl.split('\n'):
            if i.startswith('start on runlevel'):
                nfl.append('start on runlevel [{}]'.format(start_levels))
            elif i.startswith('stop on runlevel'):
                nfl.append('stop on runlevel [{}]'.format(stop_levels))
            else:
                nfl.append(i)
        put_rf(fname, "\n".join(nfl), use_sudo=True)
    else:
        with settings(hide('warnings', 'stderr'), warn_only=True):
            
            rm_cmd = 'rm '
            for level in "0123456":
                rm_cmd += "/etc/rc{1}.d/*{0} ".format(name, level)
            sudo(rm_cmd)

            for level in start_levels:
                sudo('ln -s /etc/init.d/{0} /etc/rc.{1}/S{2}{0}'\
                        .format(name, level, prior))
        
            for level in start_levels:
                sudo('ln -s /etc/init.d/{0} /etc/rc.{1}/K{2}{0}'\
                        .format(name, level, prior))






