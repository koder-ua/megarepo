import sys
import urllib
import sqlite3

get_all_users_sql = 'select auth_user.id, account_profile.id, auth_user.username ' + \
                'from auth_user, account_profile ' + \
                'where auth_user.id=account_profile.user_id'

get_all_graphs_sql = 'select id, profile_id, name, url ' + \
                'from account_mygraph'

insert_new_graphs_sql = 'insert into account_mygraph(id, profile_id, name, url) values (?, ?, ?, ?)'

host_port = 'http://localhost:8011/render/'

def myrepr(obj):
    if isinstance(obj, basestring):
        return '"%s"' % obj
    return str(obj)

class Func(object):
    def __init__(self, name):
        self.name = name
        self.params = []
    
    def __call__(self, *dt):
        self.params.extend(dt)
        return self
    
    def __str__(self):
        return "{0}({1})".format(self.name, ",".join(map(str, self.params)))

class FuncFactory(object):
    def __getattr__(self, name):
        return Func(name)
        
f = FuncFactory()

cpu_average = f.alias(
                f.movingAverage(
                    f.sumSeries("{0}.cpu.user",
                                "{0}.cpu.sys"),
                    5),
                '"{0} CPU load"')

cpu_all_second = f.alias(
                    f.secondYAxis(
                        f.movingAverage(
                            f.sumSeries("{0}.cpu.user",
                                f.sumSeries("{0}.cpu.sys",
                                            "{0}.cpu.iowait"),
                                ),
                            5),
                    ),
                    '"{0} CPU load"')

iowait_average = f.alias(
                    f.movingAverage(
                        "{0}.cpu.iowait",
                        5),
                    '"{0} CPU iowait"')

io_average = f.alias(
                f.sumSeries(
                    "{0}.io.breadps",
                    "{0}.io.bwrtnps"),
                '"{0} IO (r+w)"')


url_templ = "{0}?width={1}&height={2}&{{0}}&from=-{3}&lineMode=connected&hideLegend=false".format(host_port, 1300, 600, '5minutes')

class User(object):
    def __init__(self, name, user_id, acc_id):
        self.name = name
        self.user_id = user_id
        self.acc_id = acc_id

class Graph(object):
    def __init__(self, id, user_acc_id, name, url):
        self.id = id
        self.user_acc_id = user_acc_id
        self.name = name
        self.url = url
    
    def insert_sql(self):
        return insert_new_graphs_sql, (self.id, self.user_acc_id,
                                   self.name, self.url)
    

def get_all_users(cr):
    cr.execute(get_all_users_sql)

    for user_id, acc_id, username in cr.fetchall():
        yield User(username, user_id, acc_id)

def get_all_graphs(cr):
    cr.execute(get_all_graphs_sql)
    for id, acc_id, name, url in cr.fetchall():
        yield Graph(id, acc_id, name, url)
    
def add_cpu_io_graphs(cr, name, vm_names):
    users = list(get_all_users(cr))
    graphs = list(get_all_graphs(cr))
    max_id = max((-1,) + tuple(graph.id for graph in graphs))
    
    graphs = []
    
    for name, grap_templ in {name + '_cpu'     : cpu_average,
                             name + '_io'      : io_average,
                             name + '_io_wait' : iowait_average}.items():
        gurl = url_templ.format(
                "&".join("target=" + urllib.quote(str(grap_templ).format(vm_name))
                                for vm_name in vm_names))
        
        graphs.append(Graph(max_id + 1, 2, name, gurl))
        max_id += 1
    
    t1 = "&".join("target=" + urllib.quote(str(io_average).format(vm_name))
                            for vm_name in vm_names)
    t2 = "&".join("target=" + urllib.quote(str(cpu_all_second).format(vm_name))
                            for vm_name in vm_names)
    
    gurl = url_templ.format(t1 + '&' + t2)
    graphs.append(Graph(max_id + 1, 2, name + '_cpu_and_io', gurl))
    max_id += 1
    
    for g in graphs:
        cr.execute('delete from account_mygraph where name=?',(g.name,))
        cr.execute(*g.insert_sql())

def clear_all_graphs(cr):
    cr.execute('delete from account_mygraph')
    
def main(argv = None):
    import storage
    import argparse

    argv = argv if argv is not None else sys.argv
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--action', choices=('create', 'clear'))
    parser.add_argument('--name', required=False)
    parser.add_argument('--vms', nargs='+', required=False)
    
    opts = parser.parse_args(argv[1:])

    conn = sqlite3.connect('///opt/graphite/storage/graphite.db')
    cr = conn.cursor()
    
    if opts.action == 'create':
        all_names = []
        for vm_name_templ in opts.vms:
            all_names.extend(name for name,_ in storage.get_all_vms(vm_name_templ))

        add_cpu_io_graphs(cr, opts.name, all_names)
    elif opts.action == 'clear':
        clear_all_graphs(cr)

    conn.commit()
    conn.close()
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))


