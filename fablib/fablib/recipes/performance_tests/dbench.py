import os
from fablib.core import *
from fablib.recipes.sensor import sensor_provider

@ensure('gcc')
@ensure('make')
@ensure('git')
@ensure_pkg('autoconf')
@ensure_pkg('libpopt-dev')
def install_dbench_from_source():
    with cd('/tmp'):
        prun('dbench',
             'git clone git://git.samba.org/sahlberg/dbench.git dbench')
        
        with cd('dbench'):
            if not exists('dbench'):
                prun('configure', './autogen.sh')
                prun('Makefile', './configure')
                run('make')
    return '/tmp/dbench/dbench', '/tmp/dbench/loadfiles'

def install_dbench():
    install('dbench')
    return which('dbench'), '/usr/share/dbench'
    
_dbench_re = re.compile(r"Throughput\s(?P<tps>[\d.]+)\sMB/sec")

@sensor_provider
def dbench(loadfile, procs, tlimit=180):
    dpath, lpath = install_dbench()
    loadfile = os.path.join(lpath, loadfile)
    yield 
    res = run('{0} -c {loadfile} -t {tlimit} {procs}'.format(
                                               dpath, loadfile=loadfile,
                                               tlimit=tlimit, procs=procs))
    yield
    result = {}
    for line in res.split('\n'):
        rr = _dbench_re.match(line)
        if rr:
            result['tps'] = float(rr.group('tps'))
            result['loadfile'] = loadfile
            result['threads'] = procs
            result['tlimit'] = tlimit
            break
    yield result
