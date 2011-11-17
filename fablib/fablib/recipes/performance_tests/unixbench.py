from fablib.core import *
from fablib.recipes.sensor import sensor_provider

set_hosts(env.hosts)

@ensure('make')
@ensure('gcc')
def istall_unixbench_src(ver='5.1.3'):
    "install unixbench from source"
    if not exists("/tmp/UnixBench/Run"):
        with cd('/tmp'):
            with settings(warn_only=True):
                run('rm -f UnixBench{0}.tgz'.format(ver))
                run('rm -rf UnixBench')
                run('wget ' + \
                    'http://byte-unixbench.googlecode.com/files/' + \
                    'UnixBench{0}.tgz'.format(ver))
                run('tar xfz UnixBench{0}.tgz'.format(ver))
            with cd('UnixBench'):
                run('make')
    return "/tmp/UnixBench"
        
proc_count_re = re.compile(r"\d+\s+CPUs?\s+in\s+system;\s+running\s+" + \
                           r"(?P<proc_count>\d+)" + \
                           r"\s+parallel\s+cop(?:y|ies)\s+of\s+tests\s*$")
start_line_re = re.compile(r"System\s+Benchmarks\s+Index" + \
                        r"\s+Values\s+BASELINE\s+RESULT\s+INDEX\s*$")
end_line_re = re.compile(r"\s+========")
data_line_re = re.compile(r"(?P<name>.*?)" + \
                       r"\s+(?P<BASELINE>\d+(?:\.\d+)?)" + \
                       r"\s+(?P<RESULT>\d+(?:\.\d+)?)" + \
                       r"\s+(?P<INDEX>\d+(?:\.\d+)?)\s*$")

def result_parser(res):
    in_data = False
    data_dict = {}
    proc_count = None
    
    for line in res.split('\n'):
        pcr = proc_count_re.match(line)
        
        if pcr:
            proc_count = int(pcr.group('proc_count'))
        elif start_line_re.match(line):
            if proc_count == None:
                raise RuntimeError("No proc count found before start of block")
            
            in_data = True
            data_dict[proc_count] = {}
        elif end_line_re.match(line):
            in_data = False
            proc_count = None
        elif in_data:
            line_res = data_line_re.match(line)
            
            if line_res is None:
                raise RuntimeError("Can't parse data line %r" % (line,))
                
            names = "BASELINE RESULT INDEX".split()
            data_dict[proc_count][line_res.group('name')] = \
                dict(
                    zip(names,
                        map(float,
                            map(line_res.group, names))))
    return data_dict

@sensor_provider
def unixbench(ver='5.1.3', results=None):
    unixbench_dir = istall_unixbench_src(ver)
    with cd(unixbench_dir):
        yield
        text_res = run("./Run")
        yield

    if results is not None:
        results[curr_host()] = parsed_res

    yield result_parser(text_res)
    
def main():
    from pprint import pprint
    pprint(
        result_parser(
            open('/home/koder/workspace/unixbench_out.txt').read()))

if __name__ == '__main__':
    main()
    