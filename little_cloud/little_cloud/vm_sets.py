from libvirtex.connection import KVMDomain, LXCDomain
from libvirtex.devices import HDDFileDevice, ETHNetworkDevice, FileSystemDevice, \
                    HDDBlockDevice, ETHBridgedDevice

def provides(hv_type, set_name):
    def closure(func):
        func.provides_vm_set = set_name
        func.provides_hv_type = hv_type
        return func
    return closure

class Sets(object):
    @classmethod
    def all(cls):
        for func in cls.__dict__.values():
            if hasattr(func, 'provides_vm_set'):
                yield func.provides_vm_set, func.provides_hv_type

    @classmethod
    def start(cls, name, conn):
        found = False
        for func in cls.__dict__.values():
            if hasattr(func, 'provides_vm_set'):
                if func.provides_vm_set == name:
                    found = True
                    for vm in func(cls, conn):
                        yield vm
        
        if not found:
            raise RuntimeError("Set %r not found" % (name,))

    @provides('kvm','nosql-root')
    def mkvm_nosql_root(self, conn):
        hw = '00:44:01:61:76:fB'
        ip = '192.168.122.6'
    
        ubuntu_img_path = '/home/koder/vm_images/ubuntu-kvm-test.qcow2'
        vm = KVMDomain.construct(conn,
                                   True,
                                   'nosql-root',
                                   1024 * 1024,
                                   1,
                                   HDDFileDevice(ubuntu_img_path, 'qcow2'), 
                                   ETHNetworkDevice(hw, "vnet7", ip=ip))
        yield vm

    @provides('kvm', 'ubuntu_11_10')
    def mkvm_ubuntu(self, conn):
        hw = '00:44:01:61:76:fD'
        ip = '192.168.122.9'
    
        ubuntu_img_path = '/home/koder/vm_images/Ubuntu_11_10_x64.qcow2'
        vm = KVMDomain.construct(conn,
                                   True,
                                   'ubuntu_11_10',
                                   2 * 1024 * 1024,
                                   2,
                                   HDDFileDevice(ubuntu_img_path, 'qcow2'), 
                                   ETHNetworkDevice(hw, "vnet7", ip=ip))
        yield vm
    
    @provides('lxc', 'oneiric')
    def mkvm_oneiric(self, conn):
        hw = '4A:59:43:49:79:BF'
        ip = '192.168.122.10'
    
        vm = LXCDomain.construct(conn,
                                 True,
                                 'oneiric',
                                 1024 * 1024,
                                 2,
                                 FileSystemDevice(
                                    '/mnt/lxc/ubuntu_oneiric/rootfs'),
                                 ETHNetworkDevice(hw, "vnet7", ip=ip))
        yield vm
    
    @provides('lxc', 'oneiric-br')
    def mkvm_oneiric_br(self, conn):
        hw = '4A:59:43:49:79:C0'
        ip = '192.168.123.2'
    
        vm = LXCDomain.construct(conn,
                                 True,
                                 'oneiric-br',
                                 1024 * 1024,
                                 2,
                                 FileSystemDevice(
                                    '/mnt/lxc/ubuntu_oneiric_br/rootfs'),
                                 ETHBridgedDevice(hw, "vnet7", 'br0', ip=ip))
        yield vm
    
    @provides('kvm', 'testvm')
    def mkvm_testvm(self, conn):
        hw = '00:44:01:61:76:fC'
        ip = '192.168.122.7'
    
        ubuntu_img_path = '/home/koder/vm_images/ubuntu-kvm-diff4.qcow2'
        vm = KVMDomain.construct(conn,
                                   True,
                                   'testvm',
                                   1024 * 1024,
                                   1,
                                   HDDFileDevice(ubuntu_img_path, 'qcow2'), 
                                   ETHNetworkDevice(hw, "vnet7", ip=ip))
        yield vm

    @provides('kvm', 'nosql')
    def mkvm_nosql(self, conn):
        hw_list = ['00:44:01:61:76:f7',
                   '00:44:01:61:76:f8',
                   '00:44:01:61:76:f9',
                   '00:44:01:61:76:fA',
                   '00:44:01:61:77:00',
                   '00:44:01:61:77:01'
                   ]
        
        ip_list = ['192.168.122.2',
                   '192.168.122.3',
                   '192.168.122.4',
                   '192.168.122.5',
                   '192.168.122.11',
                   '192.168.122.12']
    
        for pos in range(len(ip_list)):    
    
            name = 'nosql-{0}'.format(pos)
            if pos == 5:
                dev = '/dev/vm_images/nosql-5'
                hdd = HDDBlockDevice(dev, 'raw')
            else:
                ubuntu_img_path = \
                        '/home/koder/vm_images/ubuntu-kvm-diff{0}.qcow2'\
                                        .format(pos)
                hdd = HDDFileDevice(ubuntu_img_path, 'qcow2')
            
            vm = KVMDomain.construct(conn,
                                       True,
                                       name,
                                       1024 * 1024,
                                       1,
                                       hdd, 
                                       ETHNetworkDevice(hw_list[pos], "vnet7",
                                                 ip = ip_list[pos]))
            yield vm
