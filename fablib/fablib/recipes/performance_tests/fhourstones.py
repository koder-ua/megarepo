import re

from fabric.api import run, env
from fabric.context_managers import cd
from fabric.contrib.files import exists

from fablib.recipes.sensor import sensor_provider
from storage import get_storage


def fhourstones(mark, storage='console', local_sensor=None, remote_sensor=None):
    res = do_fhourstones(local_sensor=local_sensor,
                         remote_sensor=remote_sensor)
    res['mark'] = mark
    get_storage(storage, 'fhourstones')(res)
    
    return res


fhourstones_re = re.compile(r"= (?P<val>\d+\.\d+) Kpos/sec")

@sensor_provider
def do_fhourstones():
    cmd = './Fhourstones < inputs'
    with cd('/tmp'):
        if not exists('/tmp/Fhourstones'):
            run('rm -f Fhourstones.tar.gz')
            run('wget http://homepages.cwi.nl/~tromp/c4/Fhourstones.tar.gz')
            run('tar xfz Fhourstones.tar.gz')
            run('gcc -O3 -march=native -m64 SearchGame.c -o Fhourstones')
        yield
        res = run(cmd)
        yield
        vals = [float(val.group('val'))
                for val in fhourstones_re.finditer(str(res))]
        
        res = {
            'vals':vals,
            'host':env.host,
            'cmd':cmd
        }
        
    yield res 