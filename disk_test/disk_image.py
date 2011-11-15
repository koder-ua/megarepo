import os
import subprocess
import contextlib

__author__ = 'koder'

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
