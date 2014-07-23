#!/usr/bin/env python 

import re
import argparse
import config
import enums
import compiler_flags
import heuristic_search

def autotune():
    if config.Arguments.autotune_subcommand == enums.SearchStrategy.ga:
        search = heuristic_search.GA()
    elif config.Arguments.autotune_subcommand == enums.SearchStrategy.random:
        search = heuristic_search.Random()
    elif config.Arguments.autotune_subcommand == enums.SearchStrategy.simulated_annealing:
        search = heuristic_search.SimulatedAnnealing()
    else:
        assert False, "Unknown testing strategy %s" % config.Arguments.autotune_subcommand
    try:
        search.run()
    except KeyboardInterrupt:
        pass
    finally:
        config.summarise_timing()
        search.summarise()

def setup_PPCG_flags():
    # We have to add some of the PPCG optimisation flags on the fly as they
    # depend on command-line arguments
    compiler_flags.PPCG.flag_map[compiler_flags.PPCG.max_shared_memory] = compiler_flags.EnumerationFlag(compiler_flags.PPCG.max_shared_memory,
                                                                                                         config.Arguments.shared_memory)
    
    compiler_flags.PPCG.flag_map[compiler_flags.PPCG.sizes]             = compiler_flags.SizesFlag()
    
    # Add all the PPCG optimisation flags
    for flag_name in compiler_flags.PPCG.flag_map.keys():
        compiler_flags.PPCG.optimisation_flags.append(compiler_flags.PPCG.flag_map[flag_name])
    # Add PPCG flags as directed by the user
    if config.Arguments.whitelist:
        for flag_name in config.Arguments.whitelist:
            if flag_name in compiler_flags.PPCG.flag_map:
                the_flag = compiler_flags.PPCG.flag_map[flag_name]
                if the_flag.possible_values != [True, False]:
                    raise argparse.ArgumentTypeError("Only boolean flags may be provided on the white list. You gave '%s'" % flag_name)
                the_flag.tuneable = False
                if the_flag not in compiler_flags.PPCG.optimisation_flags:
                    compiler_flags.PPCG.optimisation_flags.append(the_flag)
            else:
                raise argparse.ArgumentTypeError("PPCG flag '%s' not recognised" % flag_name)
    # Remove PPCG flags as directed by the user
    if config.Arguments.blacklist:
        for flag_name in config.Arguments.blacklist:
            if flag_name in compiler_flags.PPCG.flag_map:
                compiler_flags.PPCG.optimisation_flags.remove(compiler_flags.PPCG.flag_map[flag_name])
            else:
                raise argparse.ArgumentTypeError("PPCG flag '%s' not recognised" % flag_name)
    
def the_command_line():    
    class ISLAction(argparse.Action):
        def __call__(self, parser, namespace, value, option_string=None):
            compiler_flags.PPCG.flag_map = dict(compiler_flags.PPCG.flag_map.items() + compiler_flags.PPCG.isl_flag_map.items())
            setattr(namespace, self.dest, value) 
                 
    def parse_int_range(string):
        match = re.match(r'(\d+)-(\d+)$', string)
        if not match:
            raise argparse.ArgumentTypeError("'%s' is not an integer range. Expected something like '0-5'" % string)
        try:
            start = int(match.group(1))
            end   = int(match.group(2)) 
            if end < start:
                raise argparse.ArgumentTypeError("The integer range '%s' is empty" % string)
        except ValueError:
            raise argparse.ArgumentTypeError("'%s' must be an integer range" % string)
        return (start, end+1)
    
    def int_csv(string):
        try:
            return map(int, string.split(','))
        except ValueError:
            raise argparse.ArgumentTypeError("'%s' must be a list of integers" % string)
        
    def string_csv(string):
        return string.split(',')
    
    # The command-line parser and its options
    parser = argparse.ArgumentParser(description="Auto-tuning framework for CARP", fromfile_prefix_chars='@')
    
    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        help="be verbose",
                        default=False)
    
    # Building the application options
    building_and_running_group = parser.add_argument_group("Arguments for how to compile application and run executable") 
    
    building_and_running_group.add_argument("--ppcg-cmd",
                                            metavar="<STRING>",
                                            help="how to call PPCG from the auto-tuner",
                                            required=True)
    
    building_and_running_group.add_argument("--build-cmd",
                                            metavar="<STRING>",
                                            help="how to build the application from the auto-tuner",
                                            required=True)
    
    building_and_running_group.add_argument("--run-cmd",
                                            metavar="<STRING>",
                                            help="how to run the generated binary from the auto-tuner",
                                            required=True)
    
    runs = 5
    building_and_running_group.add_argument("--runs",
                                            type=int,
                                            metavar="<int>",
                                            help="number of times to run the compiled executable for purposes of timing (default: %d)" % runs,
                                            default=runs)
    
    building_and_running_group.add_argument("--execution-time-from-binary",
                                            action="store_true",
                                            help="assume that the binary prints its execution time to standard output (rather than measuring the execution time through Python)",
                                            default=False)
    
    # PPCG options
    ppcg_group = parser.add_argument_group("PPCG arguments")
    
    ppcg_group.add_argument("--target",
                            choices=[enums.Targets.cuda, enums.Targets.opencl],
                            help="the target to generate code for",
                            default=enums.Targets.opencl)
    
    ppcg_group.add_argument("--blacklist",
                            type=string_csv,
                            metavar="<LIST>",
                            help="do not tune on these PPCG flags")
    
    ppcg_group.add_argument("--whitelist",
                            type=string_csv,
                            metavar="<LIST>",
                            help="always supply these flags to PPCG")
    
    shared_memory_possibilties = [128, 256, 512, 1024, 2048, 4096, 8192]
    ppcg_group.add_argument("--shared-memory",
                            type=int_csv,
                            metavar="<LIST>",
                            help="consider only these values when tuning the shared memory size (default: %s)" % (shared_memory_possibilties),
                            default=shared_memory_possibilties)
    
    tile_size_range = (2**0, 2**6)
    ppcg_group.add_argument("--tile-size",
                            type=parse_int_range,
                            metavar="<RANGE>",
                            help="consider only values in this range when tuning the tile size (default: %d-%d)" % (tile_size_range[0], tile_size_range[1]),
                            default=tile_size_range)
    
    tile_dimensions = 3
    ppcg_group.add_argument("--tile-dimensions",
                            type=int,
                            metavar="<int>",
                            help="consider only tile dimensions of this size (default: %d)" % tile_dimensions,
                            default=tile_dimensions)
    
    block_size_range = (2**0, 2**10)
    ppcg_group.add_argument("--block-size",
                            type=parse_int_range,
                            metavar="<RANGE>",
                            help="consider only values in this range when tuning the block size (default: %d-%d)" % (block_size_range[0], block_size_range[1]),
                            default=block_size_range)
    
    block_dimensions = 3
    ppcg_group.add_argument("--block-dimensions",
                            type=int,
                            metavar="<int>",
                            help="consider only block dimensions of this size (default: %d)" % block_dimensions,
                            default=block_dimensions)
    
    grid_size_range = (2**0, 2**15)
    ppcg_group.add_argument("--grid-size",
                            type=parse_int_range,
                            metavar="<RANGE>",
                            help="consider only values in this range when tuning the grid size (default: %d-%d)" % (grid_size_range[0], grid_size_range[1]),
                            default=grid_size_range)
    
    grid_dimensions = 3
    ppcg_group.add_argument("--grid-dimensions",
                            type=int,
                            metavar="<int>",
                            help="consider only grid dimensions of this size (default: %d)" % grid_dimensions,
                            default=grid_dimensions)
    
    ppcg_group.add_argument("--no-tune-kernel-sizes",
                            action="store_true",
                            help="do not tune kernel sizes individually, i.e. use a uniform tile size for all kernels and let PPCG decide on suitable block and grid sizes",
                            default=False)
    
    ppcg_group.add_argument("--all-isl-options",
                            action=ISLAction,
                            metavar="",
                            help="use all ISL options available. (Performance is likely to be very slow)")
    
    search_subparsers = parser.add_subparsers(dest="autotune_subcommand",
                                              description="test generation subcommands")
        
    # Create the parser for the sub-command 'ga' of 'autotune'
    generations    = 10
    population     = 10
    mutation_rate  = 0.015
    crossover_rate = 0.8
    
    parser_ga = search_subparsers.add_parser(enums.SearchStrategy.ga)
        
    parser_ga.add_argument("--generations",
                         type=int,
                         help="the number of generations (default: %d)" % generations,
                         metavar="<int>",
                         default=generations)
    
    parser_ga.add_argument("--population",
                         type=int,
                         metavar="<int>",
                         default=population,
                         help="the population size (default: %d)" % population)
    
    parser_ga.add_argument("--mutation-rate",
                         type=float,
                         metavar="<float>",
                         default=0.015,
                         help="the mutation rate (default: %.3f)" % mutation_rate)
    
    parser_ga.add_argument("--crossover-rate",
                         type=float,
                         metavar="<float>",
                         default=0.8,
                         help="the crossover rate (default: %.3f)" % crossover_rate)
    
    parser_ga.add_argument("--crossover",
                         choices=[enums.Crossover.one_point, enums.Crossover.two_point],
                         help="the crossover technique",
                         default=enums.Crossover.two_point)
    
    parser_ga.add_argument("--elitism",
                         action="store_true",
                         help="propagate the elite individual into the next generation",
                         default=True)
    
    # Create the parser for the sub-command 'annealing' of 'autotune'
    parser_annealing = search_subparsers.add_parser(enums.SearchStrategy.simulated_annealing)
    
    temperature = 1.0
    parser_annealing.add_argument("--initial-temperature",
                                  type=float,
                                  metavar="<float>",
                                  default=temperature,
                                  help="the initial temperature (default: %.1f)" % temperature)
    
    temperature_steps = 100
    parser_annealing.add_argument("--temperature-steps",
                                  type=int,
                                  metavar="<int>",
                                  default=temperature_steps,
                                  help="the number of steps at a fixed temperature (default: %d)" % temperature_steps)
    
    cooling = 0.8
    parser_annealing.add_argument("--cooling",
                                  type=float,
                                  metavar="<float>",
                                  default=cooling,
                                  help="the cooling fraction (default: %.1f)" % cooling)
    
    cooling_steps = 10
    parser_annealing.add_argument("--cooling-steps",
                                  type=int,
                                  metavar="<int>",
                                  default=cooling_steps,
                                  help="the number of cooling steps before termination (default: %d)" % cooling_steps)
                                  
    # Create the parser for the sub-command 'random' of 'autotune'
    parser_random = search_subparsers.add_parser(enums.SearchStrategy.random)
    
    randoms = generations * population
    parser_random.add_argument("--population",
                               type=int,
                               metavar="<int>",
                               default=randoms,
                               help="the number of random tests to generate (default: %d)" % randoms)
    
    parser.parse_args(namespace=config.Arguments)

if __name__ == "__main__":
    the_command_line()
    setup_PPCG_flags()
    autotune()    
        