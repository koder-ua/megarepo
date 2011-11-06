"""
This module contains general routines for fabric tool
"""

import os
import re
import json
import uuid
import contextlib

from StringIO import StringIO

from fabric.api import *
from fabric.context_managers import *
from fabric.contrib.files import exists

class Requirement(object):
    """
    General requirement for package in form name--oper--version,
    like python==2.6
    """
    all_opers = '=>','==','<=','>','<'
    
    def __init__(self, package, version, oper):
        self.package = package
        self.version = version
        self.oper = oper
        
    def __str__(self):
        if self.oper is not None:
            return "{0}{1}{2}".format(self.package, self.oper, self.version)
        else:
            return self.package
        
    @classmethod
    def from_str(cls, data):
        ver = None
        
        package = data
        ver = None
        
        for oper in cls.all_opers:
            if oper in data:
                package, ver = data.split(oper)
                break
        
        if ver is None:
            oper = None
        
        return cls(package, ver, oper)

class PackageManager(object):
    """
    Abstract base class for package manager
    """
    @classmethod
    def check_package(cls, requirement):
        "check package installed"
        pass
    
    @classmethod
    def install_packages(cls, requirements):
        "install package, accept Requirement of string"
        ready_req = []
        
        for requirement in requirements:
            if isinstance(requirement, basestring):
                ready_req.append(Requirement.from_str(requirement))
            else:
                ready_req.append(requirement)
        
        return cls.do_install_packages(*ready_req)
    
    @classmethod
    def do_install_package(cls, requirement):
        "install selected package"
        pass
    
    @classmethod
    def uninstall_package(cls, name):
        "uninstall selected package"
        pass
    
    @classmethod
    def get_all_installed(cls):
        "get all packages with version"
        pass
    
    @classmethod
    def get_cmd_package(cls, cmd):
        "find which package provides this cmd"
        pass
    
    @classmethod
    def get_not_installed(cls, packages):
        all = set(name for name,_1,_2 in cls.get_all_installed())
        packages = set(packages)
        return packages - all

class ApgGetUbuntu(PackageManager):
    "ubuntu apt-get insterface for PackageManager"
    @classmethod
    def check_package(cls, name):
        with settings(hide('warnings'), warn_only=True):
            res = run('dpkg -l | grep ' + name)
        if res.failed:
            return False
        return str(res).split(' ')[0] == 'ii'
    
    @classmethod
    def do_install_packages(cls, *requirements):
        reqs = []
        
        for requirement in requirements:
            if requirement.oper == '==':
                reqs.append('{0}={1}'.format(requirement.package, 
                                            requirement.version))
            elif requirement.oper is None:
                reqs.append('{0}'.format(requirement.package))
            else:
                raise RuntimeError(
                    "apt-get can't handle {0} version operator".format(requirement.oper))
        
        sudo('apt-get -y --force-yes install ' + " ".join(reqs))
    
    @classmethod
    def uninstall_package(cls, name):
        sudo('apt-get -y remove ' + name)

    @classmethod
    def get_cmd_package(cls, cmd):
        return cmd
    
    @classmethod
    def get_all_installed(cls):
        with hide('stdout'):
            res = run('dpkg -l')
            
        for line in res.split('\n'):
            words = [word.strip() for word in line.split(' ') if word.strip()]
            if words[0] == 'ii':
                yield words[1], '==', words[2] 

class ApgGetDebian(ApgGetUbuntu):
    @classmethod
    def do_install_package(cls, requirement):
        if requirement.oper == '==':
            sudo('apt-get -y --force-yes install {0}{1}'.format(
                                               requirement.package, 
                                               requirement.version))
        else:
            super(ApgGetDebian, cls).do_install_package(requirement)

def set_hosts(hosts):
    "set fab hosts from user:passwd@host form"
    if not hasattr(env, 'hosts_parsed'):
        env.hosts = []
        for host in hosts:
            user_passwd, hostname = host.split('@',1)
            user,passwd = user_passwd.split(':')
            full_host = "{0}@{1}".format(user, hostname)
            env.hosts.append(full_host)
            env.passwords[full_host] = passwd
        env.hosts_parsed = True

def curr_host():
    "return current host name"
    return env.host_string.split('@')[1]    

def curr_os():
    "return current os(or linux distro) name"
    os_types = env.__dict__.setdefault('os_name', {})
    res = os_types.get(curr_host(), None)
    
    if res is None:
        uname = run('uname -v')
        
        if 'Ubuntu' in uname:
            res = 'ubuntu'
        else:
            res = 'unknown'
            
        os_types[curr_host()] = res
    
    return res

def pkg():
    "return package manager for current host"
    try:
        return env.package_manager
    except AttributeError:
        mng = None
        if 'ubuntu' == curr_os():
            mng = ApgGetUbuntu
            
        if mng is None:
            raise RuntimeError("No package manager available for %r os" % \
                            (curr_os(),))
        env.package_manager = mng
        return mng

def check_pkg(name):
    "check that package installed"
    return pkg().check_package(name)

def get_not_installed(packages):
    "get all packages from list, which not installed"
    return pkg().get_not_installed(packages)
    
def install(packages):
    "install package, if not installed already"
    install_me = get_not_installed(packages.split(','))
    if install_me:
        pkg().install_packages(install_me)

def uninstall(package):
    "uninstall package, if installed"
    if check_pkg(package):
        pkg().uninstall_package(package)
    
def provides(cmd):
    "execute only if 'cmd' not found"
    def closure1(func):
        def closure2(*dt, **mp):
            if not check_cmd(cmd):
                return func(*dt, **mp)
        return closure2
    return closure1

def provides_pkg(pkg):
    "execute only if pkg package not installed"
    def closure1(func):
        def closure2(*dt, **mp):
            if not check_pkg(pkg):
                return func(*dt, **mp)
        return closure2
    return closure1

def which(cmd, in_sudo='False'):
    "return path for selected command or None"
    with settings(hide('warnings'), warn_only=True):
        res = (sudo if in_sudo else run)('which {0}'.format(cmd))
    if res.failed:
        return None
    return str(res)

def check_cmd(cmd, in_sudo = False):
    "check, that cmd available"
    return which(cmd, in_sudo) is not None

def cmd_package(name):
    "return package for selected cmd"
    return pkg().get_cmd_package(name)
    
def ensure(cmd):
    "check, that cmd available and install it, if not"
    def closure(func):
        def cl2(*dt, **mp):
            if not check_cmd(cmd):
                install(cmd_package(cmd))
            return func(*dt, **mp)
        return cl2
    return closure
    
def ensure_pkg(pkg):
    "check, that pkg available and install it, if not"
    def closure(func):
        def cl2(*dt, **mp):
            if not check_pkg(pkg):
                install(pkg)
            return func(*dt, **mp)
        return cl2
    return closure

@ensure('expect')
def expect(expect_cmd, in_sudo = False):
    "execute expect commands"
    return (sudo if in_sudo else run)("expect -c '{0}'".format(expect_cmd))

class Service(object):
    def __init__(self, name):
        self.name = name
    
    def restart(self):
        self.do('restart')

    def stop(self):
        self.do('restart')

    def start(self):
        self.do('restart')

    def status(self):
        self.do('restart')
    
    def do(self, cmd):
        sudo('service {} {}'.format(self.name, cmd))
    
    def __getattr__(self, name):
        return Service(name)
        
service = Service(None)

class NotFoundCmd(RuntimeError):
    def __init__(self, cmd):
        super(NotFoundCmd, self).__init__("Command {0!r} not found".format(cmd))

def check(*cmds):
    def closure(func):
        def cl2(*dt, **mp):
            for cmd in cmds:
                if not check_cmd(cmd):
                    raise NotFoundCmd(cmd)
            return func(*dt, **mp)
        return cl2
    return closure

def get_tfile(path_templ="/tmp/%s"):
    return path_templ % (str(uuid.uuid1()),)

@contextlib.contextmanager
def remote_fl(path, use_sudo=False):
    fc = FLContent()

    if exists(path):
        get(path, fc)
        
    fc.seek(0)
    yield fc
    fc.seek(0)
    
    put(fc, path, use_sudo=use_sudo)

class FLContent(StringIO):
    def __str__(self):
        return self.getvalue()
    
    def setvalue(self, val):
        self.seek(0)
        self.write(val)
        self.truncate(len(val))
        
    def replace(self, frm, to):
        self.setvalue(re.sub(frm, to, self.getvalue()))
    
def get_rf(path):
    fc = StringIO()
    get(path, fc)
    return fc.getvalue()
    
def put_rf(path, val, use_sudo=False):
    put(StringIO(val), path, use_sudo=use_sudo)

def replace_in_file(fname, re1, re2, use_sudo=False):
    res = []
    rr = re.compile(re1)
    found = False
    
    for text1 in get_rf(fname).split('\n'): 
                    
        ntext = rr.sub(re2, text1)
        if ntext != text1:
            found = True
            
        res.append(ntext)

    if found:
        put_rf(fname, "\n".join(res), use_sudo=use_sudo)

    return found

def make_remote_dir(path, use_sudo=False):
    cmd = sudo if use_sudo else run
    return make_dir(path, exists, lambda dname : cmd('mkdir ' + dname))

def make_local_dir(path):
    return make_dir(path, os.path.exists, os.mkdir)
        
def make_dir(path, test_func, make_func):
    cpath = os.path.absname(path)
    parts = []
    
    while not test_func(cpath):
        parts.append(os.path.basename(cpath))
        cpath = os.path.dirname(cpath)

    parts = parts[::-1]
    while parts != []:
        cpath = os.path.join(cpath, parts.pop())
        make_func(cpath)
    
    