import fabis 

mysql_expect_fl = r"""spawn mysql -u root --password={mysql_root_passwd}
expect "mysql>"
send "GRANT ALL PRIVILEGES ON {dbname}.* TO {dbuser}@\\"localhost\\" IDENTIFIED BY \\"{dbpasswd}\\";\\n"
expect "mysql>"
send "GRANT ALL PRIVILEGES ON {dbname}.* TO {dbuser}@\\"%\\" IDENTIFIED BY \\"{dbpasswd}\\";\\n"
expect "mysql>"
send "drop database {dbname};\\n"
expect "mysql>"
send "create database {dbname};\\n"
expect "mysql>"
send "exit\\n"
wait
"""

def create_mysql_db(dbname, user, passwd, mysql_root_passwd):
    mysql_expect_cmd = mysql_expect_fl.replace('\n',';')
    fabis.expect(mysql_expect_cmd.format(mysql_root_passwd = mysql_root_passwd,
                                   dbname = dbname,
                                   dbuser = user,
                                   dbpasswd = passwd))

def install_mysql(ver, mysql_passwd):
    with settings(hide('warnings', 'stderr'), warn_only=True):
        result = sudo('dpkg-query --show mysql-server')

    if result.failed is False:
        warn('MySQL is already installed')
        return
    
    sudo('echo "mysql-server-{} mysql-server/root_password password ' \
              '{}" | debconf-set-selections'.format(ver, mysql_passwd))
    sudo('echo "mysql-server-{} mysql-server/root_password_again password ' \
              '{}" | debconf-set-selections'.format(ver, mysql_passwd))

    install("mysql-server-{}".format(ver))
    install("mysql-client-{}".format(ver))
    install("libmysqlclient15off")
    
    with remote_fl('/etc/mysql/my.cnf') as fl:
        val = fl.read()
        val = "\n".join(re.sub('^bind-address','#bind-address',ln)  
                                for ln in val.split('\n'))
        fl.seek(0)
        fl.write(val)
    
    service.mysql.restart()
        
