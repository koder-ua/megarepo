import time

from oktest import ok

from fabric.api import env
from fabric.context_managers import hide, settings

import fablib
from fablib.recipes.performance_tests import iozone
from fablib.recipes.performance_tests import dbench
from fablib.recipes.performance_tests import fhourstones
from fablib.recipes.performance_tests import unixtest

fablib.core.set_hosts(env.hosts)

def test_iozone():
    fields = 'bsize fsize time host threads mark write rewrite'
    res = iozone('/tmp/tt.fl', 'x', 10, 4, 1)
    
    for name in fields.split():    
        ok(name).in_(res)
        
    ok(res['bsize']) == 4
    ok(res['fsize']) == 10
    ok(int(time.time()) - res['time']) <= 1
    ok(res['host']) == env.host
    ok(res['threads']) == 1
    ok(res['mark']) == ['x']
    ok(res['write']).is_a(int)
    ok(res['rewrite']).is_a(int)

def test_iozone_mt():
    fields = 'bsize fsize time host threads mark write rewrite'
    res = iozone('/tmp/tt_%s.fl', 'x', 10, 4, 10)
    
    for name in fields.split():    
        ok(name).in_(res)

    ok(res['bsize']) == 4
    ok(res['fsize']) == 10
    ok(int(time.time()) - res['time']) <= 1
    ok(res['host']) == env.host
    ok(res['threads']) == 10
    ok(res['mark']) == ['x']
    ok(res['write']).is_a(int)
    ok(res['rewrite']).is_a(int)
    
def test_iozone_ws():
    fields = 'bsize fsize time host threads mark ' + \
             'write rewrite remote_sensor_res local_sensor_res'
    res = iozone('/tmp/tt_%s.fl', 'x', 10, 4, 1,
                 remote_sensor='io',
                 local_sensor='cpu')
    
    for name in fields.split():    
        ok(name).in_(res)

    ok(res['bsize']) == 4
    ok(res['fsize']) == 10
    ok(int(time.time()) - res['time']) <= 1
    ok(res['host']) == env.host
    ok(res['threads']) == 1
    ok(res['mark']) == ['x']
    ok(res['write']).is_a(int)
    ok(res['rewrite']).is_a(int)
    ok(res['local_sensor_res']).is_a(dict)
    ok(res['remote_sensor_res']).is_a(dict)
    
    res = iozone('/tmp/tt_%s.fl', 'x', 100, 4, 1,
                 remote_sensor='io',
                 local_sensor='cpu')
    
    for name in fields.split():    
        ok(name).in_(res)

    ok(res['bsize']) == 4
    ok(res['fsize']) == 100
    ok(int(time.time()) - res['time']) <= 1
    ok(res['host']) == env.host
    ok(res['threads']) == 1
    ok(res['mark']) == ['x']
    ok(res['write']).is_a(int)
    ok(res['rewrite']).is_a(int)
    ok(res['local_sensor_res']).is_a(dict)
    ok(res['remote_sensor_res']).is_a(dict)

    cpu_sensor_fields = 'cpu.iowait cpu.steal cpu.guest cpu.sys cpu.user' + \
                        ' cpu.nice cpu.hardirq cpu.idle cpu.softirq'

    lsr = res['local_sensor_res']
    
    for name in cpu_sensor_fields.split():    
        ok(name).in_(lsr)
        ok(lsr[name]).is_a(list)
    
    io_sensor_fields = 'io.bwrtnps io.breadps io.wtps io.rtps io.tps'

    rsr = res['remote_sensor_res']
    
    for name in io_sensor_fields.split():    
        ok(name).in_(rsr)
        ok(rsr[name]).is_a(list)

def test_dbench():
    res = dbench('client.txt', 1, tlimit=10)

    for name in 'tps loadfile threads tlimit'.split():    
        ok(name).in_(res)
        
    ok(res['tps']).is_a(float)
    ok(res['loadfile']).matches(r'.*/client\.txt')
    ok(res['threads']) == 1
    ok(res['tlimit']) == 10
    
    res = dbench('client.txt', 10, tlimit=10)

    for name in 'tps loadfile threads tlimit'.split():    
        ok(name).in_(res)
        
    ok(res['tps']).is_a(float)
    ok(res['loadfile']).matches(r'.*/client\.txt')
    ok(res['threads']) == 10
    ok(res['tlimit']) == 10
    
def test_fhorestones():
    res = fhourstones('mark', None)
    
    for name in "cmd mark host vals remote_sensor_res local_sensor_res".split():
        ok(name).in_(res)
        
    ok(res['mark']) == 'mark'
    ok(res['cmd']).is_a(str)
    ok(res['host']) == env.host
    ok(res['vals']).is_a(list)
    ok(len(res['vals'])) == 4
    
    for i in range(4):
        ok(res['vals'][i]).is_a(float)


def test():
    to_call = {}
    
    for key, val in globals().items():
        if key.startswith('test_') and hasattr(val, "__call__"):
            to_call[key] = val
    
    for name, func in to_call.items():
        print "Run " + func.__name__
        func()
