import re
import sys
import time
import json
import urllib2
import contextlib
from pprint import pprint
from StringIO import StringIO

import couchdb 

from fabric.api import *
from fabric.contrib.files import exists
from fabric.operations import put
from fablib.core import *
from fablib.executors import FabCmdExecutor
from fablib.recipes import sensor

set_hosts(env.hosts)

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


@ensure('make')
@ensure('gcc')
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

class IOZoneParser(object):
    start_tests = re.compile(r"^\s+KB\s+reclen\s+")
    resuts = re.compile(r"[\s0-9]+")
    mt_iozone_re = re.compile(r"\s+Children see throughput " + \
                    "for\s+\d+\s+(?P<cmd>.*?)\s+=\s+(?P<perf>[\d.]+)\s+KB/sec")

    cmap = {'initial writers' : 'write',
        'rewriters' : 'rewrite',
        'initial readers':'read',
        're-readers' : 'reread',
        'random readers' : 'random read',
        'random writers' : 'random write'
        }


    string1 = "                                              random  random    " + \
          "bkwd   record   stride                                   "
    string2 = "KB  reclen   write rewrite    read    reread    read   write    " + \
          "read  rewrite     read   fwrite frewrite   fread  freread"

    @classmethod
    def apply_parts(cls, parts, string, sep=' \t\n'):
        add_offset = 0
        for part in parts:
            _, start, stop = part
            start += add_offset
            add_offset = 0
            
            while stop + add_offset < len(string) and \
                        string[stop + add_offset] not in sep:
                add_offset += 1
                
            yield part, string[start:stop + add_offset]

    @classmethod
    def make_positions(cls):
        items = [i for i in cls.string2.split() if i]
        
        pos = 0
        cls.positions = []
        
        for item in items:
            npos = cls.string2.index(item, 0 if pos == 0 else pos + 1)
            cls.positions.append([item, pos, npos + len(item)])
            pos = npos + len(item)
        
        for itm, val in cls.apply_parts(cls.positions, cls.string1):
            if val.strip():
                itm[0] = val.strip() + " " + itm[0]
        
    @classmethod
    def parse_iozone_res(cls, res, mthreads = False):
        parsed_res = None
        
        sres = res.split('\n')
        
        if not mthreads:
            for pos, line in enumerate(sres[1:]):
                if line.strip() == cls.string2 and \
                            sres[pos].strip() == cls.string1.strip():
                    add_pos = line.index(cls.string2)
                    parsed_res = {}
                    
                    npos = [(name, start + add_pos, stop + add_pos)
                                for name, start, stop in cls.positions]
                    
                    for itm, res in cls.apply_parts(npos, sres[pos + 2]):
                        if res.strip() != '':
                            parsed_res[itm[0]] = int(res.strip())
                    
                    del parsed_res['KB']
                    del parsed_res['reclen']
        else:
            parsed_res = {}
            for line in sres:
                rr = cls.mt_iozone_re.match(line)
                if rr is not None:
                    cmd = rr.group('cmd')
                    key = cls.cmap.get(cmd, cmd)
                    perf = int(float(rr.group('perf')))
                    parsed_res[key] = perf
        return parsed_res
    

IOZoneParser.make_positions()

#print IOZoneParser.parse_iozone_res(
#    open('/tmp/iozone3_397/src/current/iozone.res').read())

def get_storage(name, subname):
    if name == 'console':
        return lambda x : pprint(x)
    elif name == 'couchdb':
        return CouchDBStorage(subname).insert
    elif name == 'json':
        return lambda x : sys.stdout.write("RESULT : " + json.dumps(x))
    elif name in (None, 'None'):
        return lambda x : None
            
@ensure('gcc')
@ensure('make')
@ensure('git')
@ensure_pkg('autoconf')
@ensure_pkg('libpopt-dev')
def dbbehcn():
    with cd('/tmp'):
        run('git clone git://git.samba.org/sahlberg/dbench.git dbench')
        with cd('dbench'):
            run('./autoconf.sh')
            run('./configure')
            run('make')
            
            
def to_bool(val):
    if val == 'True':
        return True
    elif val == 'False':
        return False
    elif val not in (True, False):
        raise RuntimeError("Unacceptable bool option value %r" % \
                                (val,))
    return val
    
def run_iozone(path, mark, storage="console",
               size=10, bsize=4, threads=1,
               with_sensor=False,
               with_local_sensor=False):
    
    size = int(size)
    bsize = int(bsize)
    threads = int(threads)
    
    with_sensor = to_bool(with_sensor)
    with_local_sensor = to_bool(with_local_sensor)
    
    parsed_res = do_run_iozone(path, size, bsize, threads,
                               with_sensor=with_sensor,
                               with_local_sensor=with_local_sensor)
    
    parsed_res['bsize'] = bsize
    parsed_res['fsize'] = size
    parsed_res['time'] = int(time.time())
    parsed_res['host'] = env.host
    parsed_res['threads'] = threads
    parsed_res['mark'] = mark.split('/')

    get_storage(storage, 'iozone')(parsed_res)
    return parsed_res

def parse_sensor_file(fc):
    sensor_result = {}
    for line in fc.split('\n')[1:]:
        if line.strip():
            opt, val = line.split(' ')
            sensor_result.setdefault(opt,[]).append(float(val))
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
    
    sensor_output_file = get_tfile()
    
    cmd_line.append('1 2>&1 > {0} & ps'.format(sensor_output_file))
    
    return " ".join(cmd_line), sensor_output_file

@contextlib.contextmanager
def run_sensor(opts):
    
    sensor_files_dst = '/tmp/'
    sensor_file_src = os.path.dirname(sensor.__file__)
    sensor_files = ['sar', 'sadc']

    for fname in sensor_files:
        dst = os.path.join(sensor_files_dst, fname)
        if not exists(dst):
            put(os.path.join(sensor_file_src, fname),
                dst)
            run('chmod a+x ' + dst)
    
    cmd_line, sensor_output_file = get_sensor_nohup_cmd(sensor_files_dst, opts)

    run(cmd_line)
    time.sleep(0.1)
    sensor_result = {}
    
    try:
        yield sensor_result
        fc = get_rf(sensor_output_file)
    finally:
        with settings(hide('warnings', 'stderr'), warn_only=True):
            run('killall sar')
            run('rm -f ' + sensor_output_file)
    
    sensor_result.update(parse_sensor_file(fc))


@contextlib.contextmanager
def run_local_sensor(opts):
    
    cmd_line, sensor_output_file = \
            get_sensor_nohup_cmd(os.path.dirname(sensor.__file__),
                                opts)
    
    local(cmd_line)
    time.sleep(0.1)
    sensor_result = {}
    
    try:
        yield sensor_result
        fc = open(sensor_output_file).read()
    finally:
        with settings(hide('warnings', 'stderr'), warn_only=True):
            local('killall sar')
            os.unlink(sensor_output_file)

    sensor_result.update(parse_sensor_file(fc))
    

def do_run_iozone(path, size, bsize, threads, with_sensor=False,
                                              with_local_sensor=False):
    
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
        
    cmd = '{0} -o -i 0 {1} -s {2} -r {3} {4}'.format(
                                    iozone_exec, 
                                    threads_opt,
                                    size, 
                                    bsize, 
                                    path_opt)
    
    sensor_result = None
    local_sensor_result = None

    if with_sensor and with_local_sensor:
        with run_sensor("io") as sensor_result:
            with run_local_sensor("io") as local_sensor_result:
                res = run(cmd)
    elif with_sensor:
        with run_sensor("io") as sensor_result:
            res = run(cmd)
    elif with_local_sensor:
        with run_local_sensor("io") as local_sensor_result:
            res = run(cmd)
    else:
        res = run(cmd)

    parsed_res = IOZoneParser.parse_iozone_res(res, threads > 1)

    parsed_res['cmd'] = cmd
    parsed_res['fpath'] = parsed_res['cmd'].split()[-1]
    
    parsed_res['sensor_res'] = sensor_result
    parsed_res['local_sensor_res'] = local_sensor_result
        
    return parsed_res
    

def Fhourstones(mark, storage='console'):
    res = do_Fhourstones()
    res['mark'] = mark
    get_storage(storage, 'fhourstones')(parsed_res)


def do_Fhourstones():
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
            'vals':vals,
            'host':env.host,
            'cmd':cmd
        }
    return res 
        