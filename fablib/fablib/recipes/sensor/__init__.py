import re
import os
import sys
import time
import contextlib

from fabric.api import *
from fabric.contrib.files import exists
from fabric.operations import put
from fablib.core import get_tfile, get_rf, curr_host

data_re = re.compile(r"(?P<opt>[-\w.]+)\s+(?P<val>\d+(?:\.\d+)?)\s*$")
def parse_sensor_file(fc):
    sensor_result = {}
    for line in fc.split('\n')[1:]:
        rr = data_re.match(line.strip())
        if rr:
            opt = rr.group('opt')
            val = float(rr.group('val'))
            sensor_result.setdefault(opt,[]).append(val)
    return sensor_result

def get_sensor_nohup_cmd(sensor_dir, opts):
    cmd_line = ["nohup","env",
                'PATH="{0}:$PATH"'.format(sensor_dir ),
                os.path.join(sensor_dir ,'sar')]
    
    opts = opts.split(',')
    
    if 'cpu' in opts:
        cmd_line.append('-u')
        
    if 'io' in opts:
        cmd_line.append('-b')
    
    if 'iodev' in opts:
        cmd_line.append('-d')
    
    sensor_output_file = get_tfile()
    
    cmd_line.append('1 2>&1 > {0} & ps'.format(sensor_output_file))
    
    return " ".join(cmd_line), sensor_output_file

def put_sensor(sensor_files_dst='/tmp/'):
    sensor_file_src = os.path.dirname(__file__)
    sensor_files = ['sar', 'sadc']

    for fname in sensor_files:
        dst = os.path.join(sensor_files_dst, fname)
        if not exists(dst):
            put(os.path.join(sensor_file_src, fname),
                dst)
            run('chmod a+x ' + dst)
    
def start_sensor(opts, run_func, sensor_files_dst='/tmp/', tout=True):
    
    cmd_line, sensor_output_file = get_sensor_nohup_cmd(sensor_files_dst, opts)
    run_func(cmd_line)
    
    if tout:
        time.sleep(0.1)
    
    return sensor_output_file 

def stop_sensor(run_func, sensor_output_file):
    with settings(hide('warnings', 'stderr'), warn_only=True):
        run_func('killall sar')
        run_func('rm -f ' + sensor_output_file)
        
@contextlib.contextmanager
def run_sensor(opts):
    put_sensor()
    sensor_output_file = start_sensor(opts, run)
    sensor_result = {}
    
    try:
        yield sensor_result
        sensor_result.update(parse_sensor_file(get_rf(sensor_output_file)))
    finally:
        stop_sensor(run, sensor_output_file)
    
get_lf = lambda fname : open(fname).read()

@contextlib.contextmanager
def run_local_sensor(opts):
    sensor_output_file = start_sensor(opts, local, os.path.dirname(__file__))
    sensor_result = {}
    
    try:
        yield sensor_result
        sensor_result.update(parse_sensor_file(open(sensor_output_file).read()))
    finally:
        stop_sensor(local, sensor_output_file)
    
    
def sensor_provider(func):
    def closure(*dt, **mp):
        local_sensor = mp.pop('local_sensor', None)
        remote_sensor = mp.pop('remote_sensor', None)
        
        it = func(*dt, **mp)
        it.next()
        
        local_sensor_result = None
        remote_sensor_result = None
        
        if local_sensor and remote_sensor:
            with run_sensor(remote_sensor) as remote_sensor_result:
                with run_local_sensor(local_sensor) as local_sensor_result:
                    it.next()
        elif remote_sensor:
            with run_sensor(remote_sensor) as remote_sensor_result:
                it.next()
        elif local_sensor:
            with run_local_sensor(local_sensor) as local_sensor_result:
                it.next()
        else:
            it.next()
        
        res = it.next()
        
        res['remote_sensor_res'] = remote_sensor_result
        res['local_sensor_res']  = local_sensor_result
        
        return res
    return closure
