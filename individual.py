import timeit
import os
import re
import debug
import compiler_flags
import config
import enums
import collections
import subprocess
import internal_exceptions

def get_fittest(population):
    fittest = None
    for individual in population:
        if individual.status == enums.Status.passed:
            if fittest:
                if individual.fitness > fittest.fitness:
                    fittest = individual
            else:
                fittest = individual
    if not fittest:
        raise internal_exceptions.NoFittestException("None of the individuals among this population completed successfully, hence there is no fittest individual")
    return fittest

def create_random():
    individual = Individual()   
    for flag in compiler_flags.PPCG.optimisation_flags:
        individual.ppcg_flags[flag] = flag.random_value()
    for flag in compiler_flags.CC.optimisation_flags:
        individual.cc_flags[flag] = flag.random_value()
    for flag in compiler_flags.CXX.optimisation_flags:
        individual.cxx_flags[flag] = flag.random_value()
    for flag in compiler_flags.NVCC.optimisation_flags:
        individual.nvcc_flags[flag] = flag.random_value()
    return individual

class Individual:
    """An individual solution in a population"""
    
    ID = 0
    @staticmethod
    def get_ID():
        Individual.ID += 1
        return Individual.ID
    
    def __init__(self):
        self.ID               = Individual.get_ID()
        self.ppcg_flags       = collections.OrderedDict()
        self.cc_flags         = collections.OrderedDict()
        self.cxx_flags        = collections.OrderedDict()
        self.nvcc_flags       = collections.OrderedDict()
        self.status           = enums.Status.failed
        
    def all_flags(self):
        return self.ppcg_flags.keys() + self.cc_flags.keys() + self.cxx_flags.keys() + self.nvcc_flags.keys()
    
    def all_flag_values(self):
        return self.ppcg_flags.values() + self.cc_flags.values() + self.cxx_flags.values() + self.nvcc_flags.values()
            
    def run(self):
        try:
            self.compile()
            if self.status == enums.Status.passed:
                # Fitness is inversely proportional to execution time
                self.fitness = 1/self.execution_time 
                debug.verbose_message("Individual %d: execution time = %f, fitness = %f" \
                                      % (self.ID, self.execution_time, self.fitness), __name__) 
            else:
                self.fitness = 0
        except internal_exceptions.FailedCompilationException as e:
            debug.exit_message(e)
            
    def compile(self):
        self.ppcg()
        self.build()
        self.binary()

    def ppcg(self):
        self.ppcg_cmd_line_flags = "--target=%s --dump-sizes %s" % (config.Arguments.target, 
                                                                    ' '.join(flag.get_command_line_string(self.ppcg_flags[flag]) for flag in self.ppcg_flags.keys()))
        
        os.environ["AUTOTUNER_PPCG_FLAGS"] = self.ppcg_cmd_line_flags
        debug.verbose_message("Running '%s'" % config.Arguments.ppcg_cmd, __name__)
        start  = timeit.default_timer()
        proc   = subprocess.Popen(config.Arguments.ppcg_cmd, shell=True, stderr=subprocess.PIPE)  
        stderr = proc.communicate()[1]
        end    = timeit.default_timer()
        config.time_PPCG += end - start
        if proc.returncode:
            raise internal_exceptions.FailedCompilationException("FAILED: '%s'" % config.Arguments.ppcg_cmd)         
        # Store the sizes used by PPCG
        self.size_data = compiler_flags.SizesFlag.parse_PPCG_dump_sizes(stderr)
        
    def build(self):
        debug.verbose_message("Running '%s'" % config.Arguments.build_cmd, __name__)
        start  = timeit.default_timer()
        proc   = subprocess.Popen(config.Arguments.build_cmd, shell=True)  
        stderr = proc.communicate()[1]     
        end    = timeit.default_timer()
        config.time_backend += end - start
        if proc.returncode:
            raise internal_exceptions.FailedCompilationException("FAILED: '%s'" % config.Arguments.build_cmd)
    
    def binary(self):
        time_regex = re.compile(r'^(\d*\.\d+|\d+)$')
        total_time = 0.0
        status     = enums.Status.passed
        for run in xrange(1,config.Arguments.runs+1):
            debug.verbose_message("Run #%d of '%s'" % (run, config.Arguments.run_cmd), __name__)
            start = timeit.default_timer()
            proc  = subprocess.Popen(config.Arguments.run_cmd, shell=True, stdout=subprocess.PIPE)    
            stdout, stderr = proc.communicate()
            end   = timeit.default_timer()
            if proc.returncode:
                status = enums.Status.failed
                debug.warning_message("FAILED: '%s'" % config.Arguments.run_cmd)
                continue
            if config.Arguments.execution_time_from_binary:
                if not stdout:
                    raise internal_exceptions.BinaryRunException("Expected the binary to dump its execution time. Found nothing")
                for line in stdout.split(os.linesep):
                    line    = line.strip()
                    matches = time_regex.findall(line)
                    if matches:
                        try:
                            total_time += float(matches[0])
                        except:
                            raise internal_exceptions.BinaryRunException("Execution time '%s' is not in the required format" % matches[0])
            else:
                total_time += end - start
        self.status = status
        config.time_binary += total_time
        self.execution_time = total_time/config.Arguments.runs
        
    def __str__(self):
        return "ID %d: fitness %f" % (self.ID, self.fitness)
    