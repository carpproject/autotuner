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
import blas_function_testing

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
        self.ID         = Individual.get_ID()
        self.ppcg_flags = collections.OrderedDict()
        self.cc_flags   = collections.OrderedDict()
        self.cxx_flags  = collections.OrderedDict()
        self.nvcc_flags = collections.OrderedDict()
        self.status     = enums.Status.failed
        
    def all_flags(self):
        return self.ppcg_flags.keys() + self.cc_flags.keys() + self.cxx_flags.keys() + self.nvcc_flags.keys()
            
    def run(self):
        try:
            self.compile()
            if self.status == enums.Status.passed:
                # Fitness is inversely proportional to execution time
                self.fitness = 1/self.execution_time 
                debug.verbose_message("Individual %d: execution time = %f, fitness = %f" % (self.ID, self.execution_time, self.fitness), __name__) 
            else:
                self.fitness = 0
        except internal_exceptions.FailedCompilationException as e:
            debug.exit_message(e)
            
    def vobla_compilation(self):
        # The files that flow through the VOBLA compiler chain
        root            = os.path.splitext(config.Arguments.tuning_file)[0]
        ppcg_input_file = "%s.final.c" % root
        
        # Generate test cases for the VOBLA functions
        for test in range(1, config.Arguments.vobla_test_cases+1):
            debug.verbose_message("Creating test case %d" % test, __name__)
            self.binary = blas_function_testing.create_test_case(ppcg_input_file, self.other_files)
            self.run_binary()
            
    def compile(self):
        self.ppcg()
        self.build()
        self.binary()

    def ppcg(self):
        bool_flags  = [flag.name for flag, value in self.ppcg_flags.iteritems() if not isinstance(flag, compiler_flags.SizesFlag) and type(value) is bool]
        other_flags = [(flag.name, value) for flag, value in self.ppcg_flags.iteritems() if not isinstance(flag, compiler_flags.SizesFlag) and type(value) is not bool]
        sizes       = []
        for flag, value  in self.ppcg_flags.iteritems():
            if isinstance(flag, compiler_flags.SizesFlag):
                sizes.append('kernel[%s]->tile[%s];kernel[%s]->block[%s];kernel[%s]->grid[%s]' % (flag.kernel,
                                                                                                  ','.join(str(dim) for dim in value[compiler_flags.SizesFlag.TILE_SIZE]),
                                                                                                  flag.kernel,
                                                                                                  ','.join(str(dim) for dim in value[compiler_flags.SizesFlag.BLOCK_SIZE]),
                                                                                                  flag.kernel,
                                                                                                  ','.join(str(dim) for dim in value[compiler_flags.SizesFlag.GRID_SIZE])))
        sizes_flag = '%s="{%s}"' % (compiler_flags.PPCG.sizes, ';'.join(sizes))
        self.ppcg_cmd_line_flags = "%s %s %s" % (' '.join("%s %s" % tup for tup in other_flags),
                                                 ' '.join(bool_flags),
                                                 sizes_flag)
        
        os.environ["AUTOTUNER_PPCG_FLAGS"] = "--target=%s --dump-sizes %s" % (config.Arguments.target, self.ppcg_cmd_line_flags)
        
        debug.verbose_message("Running '%s'" % config.Arguments.ppcg, __name__)
        start  = timeit.default_timer()
        proc   = subprocess.Popen(config.Arguments.ppcg, shell=True, stderr=subprocess.PIPE)  
        stderr = proc.communicate()[1]
        end    = timeit.default_timer()
        config.time_PPCG += end - start
        if proc.returncode:
            raise internal_exceptions.FailedCompilationException("FAILED: '%s'" % config.Arguments.ppcg)         
        # Store the sizes used by PPCG
        self.size_data = compiler_flags.SizesFlag.parse_PPCG_dump_sizes(stderr)
        
    def build(self):
        debug.verbose_message("Running '%s'" % config.Arguments.build, __name__)
        start  = timeit.default_timer()
        proc   = subprocess.Popen(config.Arguments.build, shell=True)  
        stderr = proc.communicate()[1]     
        end    = timeit.default_timer()
        config.time_backend += end - start
        if proc.returncode:
            raise internal_exceptions.FailedCompilationException("FAILED: '%s'" % config.Arguments.build)
    
    def binary(self):
        time_regex = re.compile(r'\d*\.\d+|\d+')
        total_time = 0.0
        status     = enums.Status.passed
        for run in xrange(1,config.Arguments.runs+1):
            debug.verbose_message("Run #%d of '%s'" % (run, config.Arguments.run), __name__)
            start = timeit.default_timer()
            proc  = subprocess.Popen(config.Arguments.run, shell=True, stdout=subprocess.PIPE)    
            stdout, stderr = proc.communicate()
            end   = timeit.default_timer()
            if proc.returncode:
                status = enums.Status.failed
                debug.warning_message("FAILED '%s'" % config.Arguments.run)
                continue
            if config.Arguments.execution_time_from_binary:
                assert stdout, "Expected the binary to dump its execution time. Found nothing"
                for line in stdout.split(os.linesep):
                    line    = line.strip()
                    matches = time_regex.findall(line)
                    if matches:
                        try:
                            total_time += float(matches[0])
                        except:
                            raise
            else:
                total_time += end - start
        self.status = status
        config.time_binary += total_time
        self.execution_time = total_time/config.Arguments.runs
        
    def __str__(self):
        return "ID %d: fitness %f" % (self.ID, self.fitness)
    