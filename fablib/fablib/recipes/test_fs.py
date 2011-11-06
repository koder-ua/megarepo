import os
import sys
import json
import socket
import contextlib
import subprocess

import logging
logger = logging
logging.basicConfig(level=logging.ERROR)

def run(cmd):
    return subprocess.check_output(cmd, shell=True)

@contextlib.contextmanager
def make_image(image, storage_type, lvm_dev=None):
    fname = image
    
    if fname.endswith('.qcow2'):
        fname = fname[:-len('.qcow2')]
        
    rm_files = []
    
    if storage_type == 'qcow':
        fname += ".qcow"
        run("qemu-img convert -f qcow2 -O qcow {0} {1}".format(image, fname))
        rm_files.append(fname)
    elif storage_type == 'qcow2':
        fname = image
    elif storage_type == 'raw':
        fname += ".raw"
        run("qemu-img convert -f qcow2 -O raw {0} {1}".format(image, fname))
        rm_files.append(fname)
    elif storage_type == 'qcow2_on_qcow2':
        fname += "_t.qcow2"
        run("qemu-img create -f qcow2 -b {0} {1}".format(image, fname))
        rm_files.append(fname)
    elif storage_type == 'qcow2_on_raw':
        fname_b = fname + ".raw"
        run("qemu-img convert -f qcow2 -O raw {0} {1}".format(image, fname_b))
        fname += "_t.qcow2"
        run("qemu-img create -f qcow2 -o backing_fmt=raw -b {0} {1}".format(fname_b, fname))
        rm_files.append(fname_b)
        rm_files.append(fname)
    elif storage_type == 'lvm':
        run("qemu-img convert -f qcow2 -O host_device {0} {1}".format(image, lvm_dev))
        fname = lvm_dev
    elif storage_type == 'qcow2_on_lvm':
        fname += "_t.qcow2"
        run("qemu-img convert -f qcow2 -O host_device {0} {1}".format(image, lvm_dev))
        run("qemu-img create -f qcow2 -o backing_fmt=host_device -b {0} {1}".format(lvm_dev, fname))
        rm_files.append(fname)
    elif storage_type == 'qcow2_in_lvm':
        run("cp {0} {1}".format(image, lvm_dev))
        fname = lvm_dev
    elif storage_type == 'qcow2_in_lvm_on_qcow2':
        fname += "_t.qcow2"
        run("qemu-img create -f qcow2 -b {0} {1}".format(image, fname))
        run("cp {0} {1}".format(fname, lvm_dev))
        run("rm -rf " + fname)
        fname = lvm_dev
    else:
        raise RuntimeError("Unknown storage type %r" % (storage_type,))
        
    yield fname
    
    map(os.unlink, rm_files)
    
def libvirtex_dtype(fname, storage_type):
    from libvirtex.devices import HDDBlockDevice, HDDFileDevice
        
    if storage_type in ('qcow', 'qcow2', 'raw'):
        return HDDFileDevice(fname, type_=storage_type)
    elif storage_type in ('qcow2_on_qcow2', 'qcow2_on_raw', 'qcow2_on_lvm'):
        return HDDFileDevice(fname, type_='qcow2')
    elif storage_type in ('qcow2_in_lvm', 'qcow2_in_lvm_on_qcow2'):
        return HDDBlockDevice(fname, type_='qcow2')
    elif storage_type == 'lvm':
        return HDDBlockDevice(fname)
        
    raise RuntimeError("Unknown storage type %r" % (storage_type,))

fab_file = '/home/koder/workspace/fablib/recipes/fab_host_test.py'
cmd = "run_iozone:{file},{format},json,size={sz},bsize={bsz},threads={threads},with_sensor=True,with_local_sensor={loc_sensor}"
fab_cmd = 'fab --hosts={2} -f {0} {1}'
RES_STR = 'RESULT :'

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
            
        ncmd = cmd.format(file=fname, sz=sz, bsz=bsz, threads=threads,
                          format=storage_type,
                          loc_sensor=loc_sensor)
        
        res = subprocess.check_output(
                    fab_cmd.format(fab_file, ncmd, hosts),
                                  shell=True)
        data = None
        for line in res.split('\n'):
            if RES_STR in line:
                data = json.loads(line[line.index(RES_STR) + len(RES_STR):])
    
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

def host_time():
    res = run('python -c "import time; print int(time.time())"')
    return int(str(res).strip())

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
    while True:
        sock = socket.socket()
        sock.settimeout(1)
        try:
            sock.connect((ip, 22))
            break
        except (socket.timeout, socket.error):
            pass
        
    return vm

# python fablib/recipes/test_fs.py ~koder/vm_images/ubuntu-server.qcow2 /dev/vm_images/disk_image_test_rraw host

def mean_and_dev(lst):
    mean = sum(lst) / len(lst)
    dev = sum((x - mean) ** 2 for x in lst) ** 0.5 / len(lst)
    return mean, dev

def main(argv):
    vm_image = argv[1]
    lv_dev = argv[2]
    storage_types = argv[3]
    ip = '192.168.122.105'
    
    all_storage_types = "qcow2:qcow:raw:qcow2_on_qcow2:qcow2_on_raw:qcow2_on_lvm"
    all_storage_types += ":lvm:qcow2_in_lvm:qcow2_in_lvm_on_qcow2"
    
    if 'all' == storage_types:
        storage_types = all_storage_types
    
    it = test_storage(vm_image, storage_types,
                      lv_dev, lambda x : make_vm(x, ip))
    
    res = "{storage_type:>10}    bsize ={bsize:>4}    fsize ={fsize:>7} " + \
          "threads ={threads:>2}   write ={write:>6}    " + \
          "rewrite ={rewrite:>6} io = {wsum}+{rsum} " + \
          "host_io = {hwsum}+{hrsum} wdev = {wdevps}" 

    for result in it:
        if 'io.wtps' not in result['sensor_res']:
            print result['sensor_res']
            mean, dev, w_sum, r_sum = 0, 0, 0, 0
            hw_sum, hr_sum = 0, 0
        else:
            mean, dev = mean_and_dev(result['sensor_res']['io.wtps'])
            w_sum = sum(result['sensor_res']['io.wtps'])
            r_sum = sum(result['sensor_res']['io.rtps'])
            hw_sum = sum(result['local_sensor_res']['io.wtps'])
            hr_sum = sum(result['local_sensor_res']['io.rtps'])

        print res.format(wmeanps=int(mean),
                         wsum=int(w_sum),
                         rsum=int(r_sum),
                         hwsum=int(hw_sum),
                         hrsum=int(hr_sum),
                         wdevps=int(dev),
                         **result)
    
if __name__ == "__main__":
    main(sys.argv)
    
    
    
    
