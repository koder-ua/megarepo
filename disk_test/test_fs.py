import sys
import socket

import fabric.api
from fablib.core import set_hosts
from fablib.recipes.performance_tests import iozone
import fabric.network

import logging

from easy_opt import PyOptParser, StrOpt
from disk_image import make_image, libvirtex_dtype

logger = logging
logging.basicConfig(level=logging.ERROR)

def wait_ssh_ready(ip):
    while True:
        sock = socket.socket()
        sock.settimeout(1)
        try:
            sock.connect((ip, 22))
            break
        except (socket.timeout, socket.error):
            pass

tests = (
    #(1, 4, 100),
    (1, 4, 1000),
    #(1, 40, 10000),
    #(1, 400, 10000),
    #(1, 1000, 100000),
    #(10, 4, 100),
    #(10, 40, 1000),
    #(10, 400, 10000),
    #(10, 1000, 10000),
    #(25, 4, 100),
    #(25, 40, 1000)
)

def run_tests(storage_type, hosts, io_devs=None):
    for threads, bsz, sz in tests:
        if 1 == threads:
            fname = '/tmp/tt.bin'
        else:
            fname = '/tmp/tt_%s.bin'
        
        if 'host' == storage_type:
            loc_sensor = False
        else:
            loc_sensor = True
            
        set_hosts([hosts], force=True)
        results = {}
        data = fabric.api.execute(iozone,
                        fname,
                        storage_type,
                        size=sz,
                        bsize=bsz,
                        threads=threads,
                        local_sensor='io,iodev',
                        remote_sensor='io,iodev',
                        results=results)
        
        fabric.network.disconnect_all()
        data = results.values()[0]
        
        data['storage_type'] = storage_type
        data['image'] = fname
        
        yield data

def test_storage(image,
                 storages, 
                 tmp_files_dir, 
                 credentials, 
                 lvm_dev1, 
                 lvm_dev2, 
                 make_vm):
    for storage_type in storages.split(':'):
        if 'host' == storage_type:
            logger.info("Start host tests")
            for val in test_host():
                yield val
        else:
            logger.info("Create storage " + storage_type)
            with make_image(image, 
                            tmp_files_dir, 
                            storage_type, 
                            lvm_dev1=lvm_dev1, 
                            lvm_dev2=lvm_dev2) as fname:
                logger.info("Start vm on " + fname)
                vm = make_vm(libvirtex_dtype(fname, storage_type))
                try:
                    #do tests and collect results
                    logger.info("Run tests on vm")
                    for res in run_tests(storage_type, credentials):
                        yield res
                finally:
                    vm.destroy()

def test_host():
    for res in run_tests('host', "koder:koder@localhost"):
        yield res

def make_vm(hdd, ip, libvirt_url):
    from libvirtex.devices import ETHNetworkDevice
    from libvirtex.connection import open_libvirt, KVMDomain

    hw = '00:44:01:61:77:20'
    
    vm = KVMDomain.construct(open_libvirt(libvirt_url),
                               True,
                               'disk_test_vm',
                               1024 * 1024,
                               1,
                               hdd, 
                               ETHNetworkDevice(hw, "vnet7", ip=ip))

    wait_ssh_ready(ip)

    return vm


class Stats(object):
    def __init__(self):
        self.mean = '-'
        self.sum = '-'
        self.dev = '-'

def get_stats(arr):
    res = Stats()
    res.sum = sum(arr)
    res.mean = float(res.sum) / len(arr)
    res.dev = (sum((x - res.mean) ** 2 for x in arr) / len(arr))  ** 0.5

    res.sum = int(res.sum)
    res.mean = int(res.mean)
    res.dev = int(res.dev)

    return res

def main(argv):

    class Options(PyOptParser):
        vm_image = StrOpt()
        lv_dev1 = StrOpt()
        lv_dev2 = StrOpt()
        storage_types = StrOpt()
        ssh_creds = StrOpt(default='root:root@192.168.122.105')
        libvirt_url = StrOpt(default="qemu:///system")
        remote_dev = StrOpt(default="")
        local_dev = StrOpt(default="")

    opts = Options.parse_opts()
    
    all_storage_types = "raw:lvm:qcow:qcow2:qcow2_on_raw:qcow2_on_lvm:qcow2_on_qcow2"
    
        
    if 'all' == opts.storage_types:
        opts.storage_types = all_storage_types
    
    _, ip = opts.ssh_creds.rsplit('@', 1)

    it = test_storage(opts.vm_image,
                      opts.storage_types,
                      '/tmp',
                      credentials=opts.ssh_creds,
                      lvm_dev1=opts.lv_dev1,
                      lvm_dev2=opts.lv_dev2,
                      make_vm=lambda hdd : make_vm(hdd, ip, opts.libvirt_url))
    
    res_format = "{storage_type:>10}    bsize ={bsize:>4}    fsize ={fsize:>7} " + \
          "threads ={threads:>2}   write ={write:>6}    " + \
          "rewrite ={rewrite:>6} io = {wsum}/{rsum} " + \
          "host_io = {hwsum}/{hrsum} wdev = {wdevps}" 

    stats = {}

    remote = 'remote_sensor_res'
    local = 'local_sensor_res'

    if opts.local_dev != "":
        local_w = 'iodev.{0}.tps'.format(opts.local_dev)
        local_r = 'no_data'
    else:
        local_r = 'io.rtps'
        local_w = 'io.wtps'

    if opts.remote_dev != "":
        remote_w = 'iodev.{0}.tps'.format(opts.remote_dev)
        remote_r = 'no_data'
    else:
        remote_r = 'io.rtps'
        remote_w = 'io.wtps'

    for result in it:

        #print result
        
        for key_1 in (remote, local):
            
            if key_1 == remote:
                keys_2 = (remote_r, remote_w)
            else:
                keys_2 = (local_r, local_w)

            for key_2 in keys_2:
                try:
                    arr = result[key_1][key_2]
                except KeyError:
                    res = Stats()
                else:
                    res = get_stats(arr)
                stats.setdefault(key_1,{})[key_2] = res

        stats_w = stats[remote][remote_w]
        stats_r = stats[remote][remote_r]
        hstats_w = stats[local][local_w]
        hstats_r = stats[local][local_r]

        print res_format.format(wmeanps=stats_w.mean,
                         wsum=stats_w.sum,
                         rsum=stats_r.sum,
                         wdevps=stats_w.dev,
                         hwsum=hstats_w.sum,
                         hrsum=hstats_r.sum,
                         **result)
    
if __name__ == "__main__":
    main(sys.argv)
    
    
    
    
