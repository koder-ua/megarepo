import os
import uuid
import stat
import subprocess
import contextlib

__author__ = 'koder'

def run(cmd):
    return subprocess.check_output(cmd, shell=True)

@contextlib.contextmanager
def make_image(src_file,
               tempo_files_dir,
               dst_format,
               qcow2_compress=False, 
               qcow2_preallocate=False,
               lvm_dev1=None,
               lvm_dev2=None):
    
    bstore_raw = None
    is_bstore_dev = False

    if dst_format == 'qcow2_on_lvm':
        bstore_raw = lvm_dev2
        is_bstore_dev = True
        dst_fname = os.path.join(tempo_files_dir, str(uuid.uuid1()))
        dst_format = 'qcow2_on_raw'
        is_dst_dev = True
        rm_files = [dst_fname]
    elif dst_format == 'qcow2_on_raw':
        bstore_raw = os.path.join(tempo_files_dir, str(uuid.uuid1()))
        dst_fname = os.path.join(tempo_files_dir, str(uuid.uuid1()))
        dst_format = 'qcow2_on_raw'
        is_dst_dev = True
        rm_files = [dst_fname, bstore_raw]
    elif dst_format == 'lvm':
        dst_format = 'raw'
        dst_fname = lvm_dev1
        is_dst_dev = True
    else:
        dst_fname = os.path.join(tempo_files_dir, str(uuid.uuid1()))
        rm_files = [dst_fname]
        is_dst_dev = False

    convert = lambda cmd : \
                    run("qemu-img convert -f qcow2 -O {0} {1} {2}".format(\
                                cmd, src_file, dst_file))

    opts = ""

    if qcow2_preallocate:
        assert dst_format in ('qcow2', 'qcow2_on_raw', 'qcow2_on_qcow2')
        opts = " -o preallocation=metadata "

    if qcow2_compress:
        assert dst_format in ('qcow2', 'qcow2_on_raw', 'qcow2_on_qcow2')
        opts = opts + " -c " 
    
    if storage_type == 'qcow2':
        run('cp {0} {1}'.format(src_file, dst_file))
    elif storage_type == 'qcow':
        convert('qcow')
    elif storage_type == 'raw':
        if is_dst_dev:
            convert("host_device")
        else:
            convert("raw")
    elif storage_type == 'qcow2_on_qcow2':
        run("qemu-img create {0} -f qcow2 -b {1} {2}".format(opts, src_file, dst_file))
    elif storage_type == 'qcow2_on_raw':

        if is_bstore_dev:
            frmt = 'host_device'
        else:
            frmt = 'raw'
        
        convert("qemu-img convert -f qcow2 -O {0} {1} {2}".format(frmt, src_file, bstore_raw))
        run("qemu-img create {0} -f qcow2 -o backing_fmt=raw -b {1} {2}".format(
                            opts, bstore_raw, dst_file))

    else:
        raise RuntimeError("Unknown storage type %r" % (storage_type,))

    yield dst_file

    map(os.unlink, rm_files)


def libvirtex_dtype(fname, storage_type):
    from libvirtex.devices import HDDBlockDevice, HDDFileDevice
    is_dev = stat.S_ISBLK(os.stat(fname).st_mode)
    
    if is_dev:
        tp = HDDBlockDevice
    else:
        tp = HDDFileDevice

    if storage_type in ('qcow', 'qcow2', 'raw'):
        return tp(fname, type_=storage_type)
    elif storage_type in ('qcow2_on_qcow2', 'qcow2_on_raw'):
        return tp(fname, type_='qcow2')

    raise RuntimeError("Unknown storage type %r" % (storage_type,))
