import os

from fabric.api import sudo, put

from fablib.core import install, check_cmd, get_rf, put_rf
from fablib.recipes.python import pip

supervisord_config = '/etc/supervisord.conf'

def install_supervisord():
    if not check_cmd('supervisorctl'):
        if not check_cmd('pip'):
            install('python-pip')
        
        pip('supervisor')
        sudo('echo_supervisord_conf > ' + supervisord_config)
        
        put(open(os.path.join(sensor_source, 'supervisor')),
            '/etc/init.d/supervisor',
            use_sudo=True)
        
        sudo('chmod a+x /etc/init.d/supervisor')
        
        sudo('ln -s /etc/init.d/supervisor /etc/rc2.d/S20supervisor')
        sudo('ln -s /etc/init.d/supervisor /etc/rc3.d/S20supervisor')
        sudo('ln -s /etc/init.d/supervisor /etc/rc4.d/S20supervisor')
        sudo('ln -s /etc/init.d/supervisor /etc/rc5.d/S20supervisor')
        sudo('ln -s /etc/init.d/supervisor /etc/rc6.d/K20supervisor')
        
        sudo('/etc/init.d/supervisor start')

def add_supervisor_prog(name, **params):
    scfg = get_rf(supervisord_config)
    prog_line = '[program:{0}]'.format(name)
    if prog_line not in scfg:

        lines = [prog_line]
        lines.extend("{0}={1}".format(*itm) for itm in params.items())

        scfg =  scfg.rstrip() + "\n" + "\n".join(lines) + "\n"
        
        put_rf(supervisord_config, scfg, use_sudo=True)
