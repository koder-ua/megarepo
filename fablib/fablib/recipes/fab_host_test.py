import re
import sys
import time
import json
import urllib2
from pprint import pprint
from StringIO import StringIO

import couchdb 

from fabric.api import *
from fabric.contrib.files import exists
from fabric.operations import put
from fablib.core import *
from fablib.executors import FabCmdExecutor
from little_cloud.fab_recipes.vm_fab import vm2hosts

set_hosts(vm2hosts('ubuntu', 'ubuntu'))
#set_hosts(["koder:koder@koder-laptop"])

class CouchDBStorage(object):
    def __init__(self, test_name, host='localhost', port=5984):
        self.conn = couchdb.Server("http://{0}:{1}/".format(host, port))
        db_name = 'virt_tests_{0}'.format(test_name)
        try:
            self.db = self.conn.create(db_name)
        except couchdb.PreconditionFailed:
            self.db = self.conn[db_name]

    def insert(self, doc):
        return self.db.save(doc)
    
    def find(self, **filters):
        
        fstrs = []
        for name, val in filters:
            fstrs.append("doc.{0} == {1!r}".format(name, val))
        filter = " and ".join(fstrs)
        
        if filter:
            emit = "if ( {0} ){{emit(doc._id, doc);}};\n".format(filter)
        else:
            emit = "emit(doc._id, doc);\n"
        
        for item in self.db.query("function(doc){{\n{0}\n}}".format(emit)):
            yield item.value


def install_iozone():
    if not exists('/tmp/iozone'):
        with cd('/tmp'):
            run('rm -f iozone3_397.tar')
            run('rm -rf iozone3_397')
            run('wget http://www.iozone.org/src/current/iozone3_397.tar')
            run('tar xf iozone3_397.tar')
            with cd('iozone3_397/src/current'):
                run('make linux-AMD64')
                run('cp iozone /tmp')
    return '/tmp/iozone'

start_tests = re.compile(r"^\s+KB\s+reclen\s+")
resuts = re.compile(r"[\s0-9]+")
mt_iozone_re = re.compile(r"\s+Children see throughput for\s+\d+\s+(?P<cmd>.*?)\s+=\s+(?P<perf>[\d.]+)\s+KB/sec")

cmap = {'initial writers' : 'write',
        'rewriters' : 'rewrite',
        'initial readers':'read',
        're-readers' : 'reread',
        'random readers' : 'random read',
        'random writers' : 'random write'
        }

def parse_iozone_res(res, mthreads = False):
    parsed_res = None
    
    sres = res.split('\n')
    
    if not mthreads:
        it = zip(sres[:-1], sres[1:])
        
        for ln1, ln2 in it:
            if start_tests.match(ln1) and resuts.match(ln2):
                add_k = [''] * 6 +  \
                        ['random', 'random', 'bkwd', 'record', 'stride'] + \
                        [''] * 4
                
                keys = [i for i in ln1.strip().split(' ') if i != '']
                
                keys = [('{0} {1}'.format(k1,k2) if k1 != '' else k2)
                        for k1,k2 in zip(add_k, keys)][:8]
                        
                vals = [int(i) for i in ln2.strip().split(' ') if i != '']
                parsed_res = dict(zip(keys, vals))
                            
    else:
        parsed_res = {}
        for line in sres:
            rr = mt_iozone_re.match(line)
            if rr is not None:
                cmd = rr.group('cmd')
                key = cmap.get(cmd, cmd)
                perf = int(float(rr.group('perf')))
                parsed_res[key] = perf
    return parsed_res
        
def format_xfs(dev, mpoint):
    
    if not exists(mpoint):
        run('mkdir {0}'.format(mpoint))
        
    run('mkfs.xfs -f {0}'.format(dev))
    run('mount -t xfs {0} {1}'.format(dev, mpoint))
    
def format_xfs_lvm(dev, lvname, mpoint = None, size = 50 * 1024):
    fab_c = FabCmdExecutor()
    from axcient.common_libs.lvm2_lib import LVM2VG  
    l = LVM2VG.create(fab_c, lvname, [dev])
    print "Volume mounted to:", l.valloc(size, mpoint)

def run_iozone(path, mark = "", size = 10, bsize = 4, threads = 1):
    iozone_exec = install_iozone()
    
    threads = int(threads)
    if 1 != threads:
        threads_opt = '-t {0}'.format(threads)
        path_opt = "-F " + " ".join(path % i for i in range(threads))
    else:
        threads_opt = ''
        if '%d' in path:
            path = path % (0,)
        path_opt = '-f {0}'.format(path)
        
    cmd = '{0} -o +d -i 0 -i 1 -i 2 {1} -s {2} -r {3} {4}'.format(
                                    iozone_exec, 
                                    threads_opt,
                                    size, 
                                    bsize, 
                                    path_opt)
    res = run(cmd)
    
    parsed_res = parse_iozone_res(res, ' -t ' in cmd)
    parsed_res['bsize'] = int(bsize)
    parsed_res['fsize'] = int(size)
    parsed_res['time'] = int(time.time())
    parsed_res['host'] = env.host
    parsed_res['threads'] = int(threads)
    parsed_res['cmd'] = cmd
    parsed_res['mark'] = mark.split('/')
    
    if 'KB' in parsed_res:
        del parsed_res['KB']
        
    parsed_res['fpath'] = parsed_res['cmd'].split()[-1]
    
    CouchDBStorage('iozone').insert(parsed_res)
    
    
def Fhourstones(mark = ""):
    cmd = './Fhourstones < inputs'
    with cd('/tmp'):
        if not exists('/tmp/Fhourstones'):
            run('rm -f Fhourstones.tar.gz')
            run('wget http://homepages.cwi.nl/~tromp/c4/Fhourstones.tar.gz')
            run('tar xfz Fhourstones.tar.gz')
            run('gcc -O3 -march=native -m64 SearchGame.c -o Fhourstones')
        res = run(cmd)
        rr = re.compile(r"= (?P<val>\d+\.\d+) Kpos/sec")
        vals = [float(val.group('val')) for val in rr.finditer(str(res))]
        res = {
            'mark':mark,
            'vals':vals,
            'host':env.host,
            'cmd':cmd
        }
        
        CouchDBStorage('fhourstones').insert(res)
        