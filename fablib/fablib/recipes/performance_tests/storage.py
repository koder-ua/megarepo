import json
import pprint
import couchdb 

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


def get_storage(name, subname):
    if name == 'console':
        return lambda x : pprint.pprint(x)
    elif name == 'couchdb':
        return CouchDBStorage(subname).insert
    elif name == 'json':
        return lambda x : sys.stdout.write("RESULT : " + json.dumps(x))
    elif name in (None, 'None'):
        return lambda x : None
