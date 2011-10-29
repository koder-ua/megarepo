import glob

class NetStorageMixIn(object):
    def allMacks(self):
        #this should be moved away from 
        return flatten(hwip.keys() for _, hwip in self.get_all())

    def allIPs(self):
        return flatten(hwip.values() for _, hwip in self.get_all())

    def findFreeMac(self):
        used_macs = self.allMacks()

        for mac in get_next_mac():
            if mac not in used_macs:
                return mac
            
try:
    import couchdb
        
    class CouchDBStorage(NetStorageMixIn):
        
        doc_tp = 'vm_name_to_iphw_map'
        
        vm_fun  = 'function(doc) {\n'
        vm_fun += '    if (doc.tp == "%s"){\n' % (doc_tp,)
        vm_fun += '        if ( doc.vm_name == "%s" ) {\n'
        vm_fun += '            emit(doc._id, doc);\n'
        vm_fun += '        }\n'
        vm_fun += '    }\n'
        vm_fun += '}\n'
        
        all_fun  = 'function(doc) {\n'
        all_fun += '    if (doc.tp == "%s"){\n' % (doc_tp,)
        all_fun += '        emit(doc._id, doc);\n'
        all_fun += '    }\n'
        all_fun += '}\n'
        
        def __init__(self, host='localhost', port=5984):
            self.conn = couchdb.Server("http://{0}:{1}/".format(host, port))
            try:
                self.db = self.conn.create('libvirtex')
            except couchdb.PreconditionFailed:
                self.db = self.conn['libvirtex']
            
        def set_vm(self, vm_name, hwip, uri="qemu:///system"):
            try:
                doc = self.get_doc(vm_name)
                doc['hwip'] = hwip
                doc['uri'] = uri
            except KeyError:
                doc = {'tp' : self.doc_tp,
                       'vm_name' : vm_name,
                       'hwip' : hwip,
                       'uri' : uri}
                
            return self.db.save(doc)
        
        def get_vm_uri(self, vm_name):
            doc = self.get_doc(vm_name)
            return doc.value.get('uri', 'qemu:///system')
            
        def get_all(self):
            for doc in self.db.query(self.all_fun):
                yield doc.value['vm_name'], doc.value['hwip']
        
        def get_doc(self, vm_name):
            res = list(self.db.query(self.vm_fun % (vm_name,)))
            
            if len(res) == 0:
                raise KeyError("No vm with name {0!r} in db".format(vm_name))
                
            if len(res) > 1:
                raise RuntimeError("More then one docs for vm %s :(" % \
                                    (vm_name,))
            
            return res[0].value
            
        def get_vm(self, vm_name):
            return self.get_doc(vm_name)['hwip']
            
except ImportError:
    CouchDBStorage = None
    
Storage = CouchDBStorage
if Storage is None:
    raise RuntimeError("No valid storage found")

def get_all_vms(template):
    s = Storage()
    for name, hwip in s.get_all():
        if glob.fnmatch.fnmatchcase(name, template):
            yield name, hwip

if __name__ == "__main__":
    s = Storage()
    for name, mapping in sorted(s.get_all()):
        print name, ':' , ", ".join("{} => {}".format(k,v) for k,v in mapping.items())
