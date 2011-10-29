import re
from fabric.api import *
from fabis import *
import fabsql

#hosts = ['koder:koder@koder-vm-ubuntu64_1']#,'koder:koder@koder-vm-ubuntu64_2']

hosts = ['notroot:qverty1@debian']
set_hosts(hosts)

envs = '/tmp/test_env'
     

def deploy_rest():
    apache_cfg = """
<VirtualHost *:80>
    ServerAdmin webmaster@localhost
    DocumentRoot /var/www
 
    WSGIScriptAlias / /opt/axcient/hotsite.wsgi
 
    ErrorLog /var/log/apache2/error.log
 
    # Possible values include: debug, info, notice, warn, error, crit,
    # alert, emerg.
    LogLevel warn
 
    CustomLog /var/log/apache2/access.log combined
</VirtualHost>"""
    install("apache2")
    install("libapache2-mod-wsgi")

    with v_env(envs):
        pip("django>=1.0")
        pip("django-piston")
    
    with remote_fl('/etc/') as fl:
        fl.replace(apache_cfg)
        
    service.apache2.restart()

def deploy_db():    
    fabsql.install_mysql('5.1', 'qwerty')
    fabsql.create_mysql_db('test_axc', 'axc', 'axc', 'qwerty')
    
    
def deploy_common():
    python_venv_init('2.5', envs)
    
    with v_env(envs):
        #pip("mysql")
        pip("sqlalchemy==0.6.8")
        pip("paramiko")
        pip("sqlachemy-migrate")
        pip("ldap")
        pip("pexpect")
        pip("simplejson")
    
    #with cd('/tmp'):
    #    run('wget --no-check-certificate -O ncclient.tar.gz https://github.com/shikhar/ncclient/tarball/v0.3.1')
    #    run('tar -xzf ncclient.tar.gz')
    #    with cd('shikhar-ncclient-23d6985'):
    #        with v_env(envs):
    #            run('python setup.py install')

