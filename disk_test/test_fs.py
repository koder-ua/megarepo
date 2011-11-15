import sys
import socket

import fabric.api
from fablib.core import set_hosts
from fablib.recipes.performance_tests import iozone

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

def run_tests(storage_type, hosts):
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
                        local_sensor='io',
                        remote_sensor='io',
                        results=results)
        
        data = results.values()[0]
        
        data['storage_type'] = storage_type
        data['image'] = fname
        
        yield data

def test_storage(image, storages, lvm_dev, make_vm):
    for storage_type in storages.split(':'):
        if 'host' == storage_type:
            logger.info("Start host tests")
            for val in test_host():
                yield val
        else:
            logger.info("Create storage " + storage_type)
            with make_image(image, storage_type, lvm_dev) as fname:
                logger.info("Start vm on " + fname)
                vm = make_vm(libvirtex_dtype(fname, storage_type))
                try:
                    #do tests and collect results
                    logger.info("Run tests on vm")
                    for res in run_tests(storage_type,
                                         "ubuntu:ubuntu@192.168.122.105"):
                        yield res
                finally:
                    vm.destroy()

def test_host():
    for res in run_tests('host', "koder:koder@localhost"):
        yield res

def make_vm(hdd, ip):
    from libvirtex.devices import ETHNetworkDevice
    from libvirtex.connection import open_libvirt, KVMDomain

    hw = '00:44:01:61:77:20'
    
    vm = KVMDomain.construct(open_libvirt("qemu:///session"),
                               True,
                               'disk_test_vm',
                               1024 * 1024,
                               1,
                               hdd, 
                               ETHNetworkDevice(hw, "vnet7", ip=ip))

    wait_ssh_ready(ip)

    return vm


def mean_and_dev(lst):
    mean = float(sum(lst)) / len(lst)
    dev = (sum((x - mean) ** 2 for x in lst) / len(lst))  ** 0.5
    return mean, dev


def main(argv):

    class Options(PyOptParser):
        vm_image = StrOpt()
        lv_dev = StrOpt()
        storage_types = StrOpt()

    opts = Options.parse_opts()

    ip = '192.168.122.105'
    
    all_storage_types = "qcow2:qcow:raw:qcow2_on_qcow2:qcow2_on_raw:qcow2_on_lvm"
    all_storage_types += ":lvm:qcow2_in_lvm:qcow2_in_lvm_on_qcow2"
    
    if 'all' == opts.storage_types:
        opts.storage_types = all_storage_types
    
    it = test_storage(opts.vm_image,
                      opts.storage_types,
                      opts.lv_dev,
                      lambda x : make_vm(x, ip))
    
    res = "{storage_type:>10}    bsize ={bsize:>4}    fsize ={fsize:>7} " + \
          "threads ={threads:>2}   write ={write:>6}    " + \
          "rewrite ={rewrite:>6} io = {wsum}/{rsum} " + \
          "host_io = {hwsum}/{hrsum} wdev = {wdevps}" 

    for result in it:
        if result['remote_sensor_res'] is None:
            mean, dev, w_sum, r_sum = '-', '-', '-', '-'
        elif 'io.wtps' not in result['remote_sensor_res']:
            mean, dev, w_sum, r_sum = '-', '-', '-', '-'
        else:
            mean, dev = mean_and_dev(result['remote_sensor_res']['io.wtps'])
            w_sum = int(sum(result['remote_sensor_res']['io.wtps']))
            r_sum = int(sum(result['remote_sensor_res']['io.rtps']))
            mean = int(mean)
            dev = int(dev)

        if result['local_sensor_res'] is None:
            hw_sum, hr_sum = '-', '-'
        elif 'io.wtps' not in result['local_sensor_res']:
            hw_sum, hr_sum = '-', '-'
        else:
            hw_sum = int(sum(result['local_sensor_res']['io.wtps']))
            hr_sum = int(sum(result['local_sensor_res']['io.rtps']))

        print res.format(wmeanps=mean,
                         wsum=w_sum,
                         rsum=r_sum,
                         hwsum=hw_sum,
                         hrsum=hr_sum,
                         wdevps=dev,
                         **result)
    
if __name__ == "__main__":
    main(sys.argv)
    
    
    
    
