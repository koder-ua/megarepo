import os

from fablib.recipes import sensor

from fabric.api import *
from fabric.context_managers import *
from fabric.contrib.files import exists, contains, append

from fablib.core import *
from fablib.recipes.python import pip
from fablib.recipes.general import install_supervisord, add_supervisor_prog

sensor_source = os.path.dirname(sensor.__file__)

sensor_dir = '/opt/graphite_sensor'

def install_graphite_sensor(carbone_url, reload=False):
    install_supervisord()
    
    if reload:
        sudo('rm -rf ' + sensor_dir)
        
    if not exists(sensor_dir):
        sudo('mkdir ' + sensor_dir)
    
    for fl in os.listdir(sensor_source):
        if fl != 'supervisor':
            dst = os.path.join(sensor_dir, fl)
            if not exists(dst):
                src = os.path.join(sensor_source, fl)
                dst = os.path.join(sensor_dir, fl)
                put(open(src), dst, use_sudo=True)
                if os.access(src, os.X_OK):
                    sudo('chmod a+x ' + dst )
                
    install_supervisord()
    curr_ip = curr_host()
    
    cmd = 'python {0}/sar2graphite.py {1} {2}'.format(sensor_dir,
                                                 carbone_url,
                                                 env.ip2vm.get(curr_ip,curr_ip))
    
    add_supervisor_prog('graphite_sensor',
                        command=cmd,
                        process_name='graphite_sensor',
                        autorestart='true',
                        directory=sensor_dir,
                        stderr_logfile='/var/log/gse.log',
                        stdout_logfile='/var/log/gs.log',
                        stopsignal='INT')
    
    sudo('supervisorctl reload')
    
    with settings(hide('warnings', 'stderr'), warn_only=True):
        sudo('supervisorctl start graphite_sensor')
        sudo('supervisorctl status graphite_sensor')
    





