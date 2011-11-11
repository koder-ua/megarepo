import re
import time

from fablib.core import *
from fablib.recipes.sensor import sensor_provider

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

def iozone(path, mark,
               size=10, bsize=4, threads=1,
               remote_sensor=None,
               local_sensor=None,
               results=None):
    
    size = int(size)
    bsize = int(bsize)
    threads = int(threads)
    
    parsed_res = do_run_iozone(path, size, bsize, threads,
                               remote_sensor=remote_sensor,
                               local_sensor=local_sensor)
    
    parsed_res['bsize'] = bsize
    parsed_res['fsize'] = size
    parsed_res['time'] = int(time.time())
    parsed_res['host'] = env.host
    parsed_res['threads'] = threads
    parsed_res['mark'] = mark.split('/')

    if results is not None:
        results[curr_host()] = parsed_res
    
    return parsed_res

@sensor_provider
def do_run_iozone(path, size, bsize, threads,
                  sync=True,
                  seq_write=True,
                  random_write=False):
    
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
        
    if sync:
        sync = '-o'
    else:
        sync = ''
    
    tests = []
    
    if seq_write:
        tests.append("0")
    if random_write:
        tests.append("2")
    
    tests = " ".join("-i " + test for test in tests)
        
    cmd = '{iozone_exec} {sync} {tests} {th} -s {size} -r {bsize} {fpath}'.\
                    format(iozone_exec=iozone_exec, 
                           th=threads_opt,
                           size=size, 
                           bsize=bsize,
                           tests=tests,
                           fpath=path_opt,
                           sync=sync)
    
    yield
    res = run(cmd)
    yield

    parsed_res = IOZoneParser.parse_iozone_res(res, threads > 1)

    parsed_res['cmd'] = cmd
    parsed_res['fpath'] = parsed_res['cmd'].split()[-1]
    
    yield parsed_res
