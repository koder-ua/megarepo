import os
import re
import mock
import warnings

from oktest import ok

from fabric.api import run, sudo
from fabric.contrib.files import exists

from fablib import core
from config import host

core.set_hosts([host])
ip = re.compile("inet addr:(?P<ip>[\d.]*?)\s")

def test_host_ok():
    ip_addr = run('ifconfig eth0 | grep "inet addr"')
    res = ip.match(str(ip_addr))
    ok(res) != None
    ok(res.group('ip')) == host.split('@')[1]
    ok(str(run('whoami'))) == host.split(':')[0]
    
    ok(core.curr_host()) == host.split('@')[1]
            
def test_other():
    ok(core.curr_os()) == 'ubuntu'
    
    with mock.patch('fablib.core.run', lambda x : 1 / 0):
        with mock.patch('fablib.core.sudo', lambda x : 1 / 0):
            # no system call should be made
            ok(core.curr_os()) == 'ubuntu'
    
def test_pkg():
    cmd_name = 'mp3blaster'
    pkg_name = 'mp3blaster'
    
    if core.check_pkg(pkg_name):
        core.uninstall(pkg_name)
        
    ok(core.pkg()) != None
    ok(core.check_pkg(pkg_name)) == False
    ok(core.check_cmd(cmd_name)) == False
    
    core.install(pkg_name)    
    ok(core.check_pkg(pkg_name)) == True
    ok(core.check_cmd(cmd_name)) == True
    
    core.uninstall(pkg_name)
    ok(core.check_pkg(pkg_name)) == False
    ok(core.check_cmd(cmd_name)) == False
    

def test_get_put():
    with warnings.catch_warnings():
        fname = os.tmpnam()
    
    t1 = 'some data'
    t2 = 'other text'
    
    core.put_rf(fname, t1)
    
    try:
        ok(core.get_rf(fname)) == t1
        
        sudo('chown root.root ' + fname)
        sudo('chmod o-w ' + fname)
        
        ok(lambda : core.put_rf(fname, t2)).raises(SystemExit)
        
        core.put_rf(fname, t2, use_sudo=True)
        ok(core.get_rf(fname)) == t2
        
        with core.remote_fl(fname, use_sudo=True) as fc:
            ok(fc.getvalue()) == t2
            fc.setvalue(t1)

        ok(core.get_rf(fname)) == t1
            
    finally:
        sudo('rm ' + fname)

def test_replace():
    with warnings.catch_warnings():
        fname = os.tmpnam()
    
    t1 = 'some data'
    t2 = 'other text'
    header = '-' * 50
    footer = '=' * 50
    
    mkfl = lambda x : header + '\n' + x + '\n' + footer
    
    core.put_rf(fname, mkfl(t1))
    try:
        ok(core.replace_in_file(fname, t2, t1)) == False
        ok(core.replace_in_file(fname, t1, t2)) == True
        ok(core.get_rf(fname)) == mkfl(t2)
        
        sudo('chown root.root ' + fname)
        sudo('chmod o-w ' + fname)
        
        ok(lambda : core.replace_in_file(fname, t2, t1)).raises(SystemExit)
        
        ok(core.replace_in_file(fname, t1, t2, use_sudo=True)) == False
        ok(core.replace_in_file(fname, t2, t1, use_sudo=True)) == True
        
        ok(core.get_rf(fname)) == mkfl(t1)
    finally:
        sudo('rm ' + fname)

def test_func_decorators():
    @core.provides('ls')
    def fake():
        raise RuntimeError()
    
    fake()
    
    @core.provides('some-unknown-command')
    def fake2():
        return True
    
    ok(fake2()) == True

    @core.provides_pkg('coreutils')
    def fake3():
        raise RuntimeError()
    
    fake3()
    
    @core.provides_pkg('some-unknown-pkg')
    def fake4():
        return True
    
    ok(fake4()) == True


    @core.ensure_pkg('coreutils')
    def fake5():
        pass

    with mock.patch('fablib.core.install', lambda x : 1 / 0):
        # no system call should be made
        fake5()
    
    pkg_name = 'mp3blaster'

    if core.check_pkg(pkg_name):
        core.uninstall(pkg_name)    

    @core.ensure_pkg(pkg_name)
    def fake5():
        ok(core.check_pkg(pkg_name)) == True
        core.uninstall(pkg_name)

    fake5()    
    
def test_which():
    path = core.which('ls')
    ok(exists(path)) == True

def test():
    to_call = {}
    
    for key, val in globals().items():
        if key.startswith('test_') and hasattr(val, "__call__"):
            to_call[key] = val
    
    for name, func in to_call.items():
        func()
    
