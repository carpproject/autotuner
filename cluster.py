import re
import os
import time
import debug
from subprocess import Popen, PIPE

def get_execution_time(err):
    time = 0.0
    with open(err, 'r') as f:
        for line in f:
            if line.startswith("user") or line.startswith("sys"):
                lexemes = re.findall("\d+\.\d+|\d+", line)
                assert len(lexemes) == 2
                minutes = lexemes[0]
                seconds = lexemes[1]
                time += float(minutes) * 60
                time += float(seconds)
    return time

def wait_for_job_completion(out, err):
    while not os.path.exists(out) or not os.path.exists(err):
        time.sleep(1)

def run_on_CX1(binary):
    pbs = os.path.abspath(os.path.dirname(binary)) + os.sep + "run.pbs"
    out = pbs + ".out.txt"
    err = pbs + ".err.txt"
    if os.path.exists(out):
        os.remove(out)
    if os.path.exists(err):
        os.remove(err)
    with open(pbs, 'w') as f:
        f.write("#!/bin/bash\n")
        f.write("#PBS -l walltime=24:00:00\n")
        f.write("#PBS -l select=1:ngpus=1\n")
        f.write("#PBS -e %s\n" % err) 
        f.write("#PBS -o %s\n" % out)
        f.write("cd $PBS_O_WORKDIR\n")
        f.write("module load cuda\n")
        f.write("time ${PROG}\n")
    cmd = "qsub -q pqkelly -v PROG=%s %s" % (binary, pbs)
    debug.verboseMessage("Running '%s'" % cmd)
    proc = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)    
    if proc.wait():
        print "FAILED: '%s'" % cmd    
    wait_for_job_completion(out, err)
    return get_execution_time(err)

if __name__ == "__main__":
    pass