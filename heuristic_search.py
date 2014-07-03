import abc
import random
import math
import copy
import config
import compiler_flags
import enums
import debug
import individual
import collections
import internal_exceptions

class SearchStrategy:
    """Abstract class for a search strategy"""
    
    @abc.abstractmethod
    def run(self):
        pass
    
    @abc.abstractmethod
    def summarise(self):
        pass
    
class GA(SearchStrategy):
    """Search using a genetic algorithm"""
    
    def set_child_flags(self, parent, child, flags, start, end):
        for flag in flags[start:end]:
            if flag in compiler_flags.PPCG.optimisation_flags:
                child.ppcg_flags[flag] = parent.ppcg_flags[flag]
            elif flag in compiler_flags.CC.optimisation_flags:
                child.cc_flags[flag] = parent.cc_flags[flag]
            elif flag in compiler_flags.CXX.optimisation_flags:
                child.cxx_flags[flag] = parent.cxx_flags[flag]
            elif flag in compiler_flags.NVCC.optimisation_flags:
                child.nvcc_flags[flag] = parent.nvcc_flags[flag]
            else:
                assert False, "Unknown flag %s" % flag        
    
    def one_point(self, mother, father, children):
        # This implements 1-point crossover
        assert len(mother.all_flags()) == len(father.all_flags())
        all_flags = mother.all_flags()
        # Compute the crossover indices            
        point1 = 0
        point2 = random.randint(point1, len(all_flags))
        point3 = len(all_flags)-1
        
        child1 = individual.Individual()
        self.set_child_flags(mother, child1, all_flags, point1, point2)
        self.set_child_flags(father, child1, all_flags, point2, point3)
        if children == 1:
            return [child1]
        child2 = individual.Individual()
        self.set_child_flags(father, child2, all_flags, point1, point2)
        self.set_child_flags(mother, child2, all_flags, point2, point3)
        return [child1, child2]
          
    def two_point(self, mother, father, children):
        assert len(mother.all_flags()) == len(father.all_flags())
        # This implements 2-point crossover
        all_flags = mother.all_flags()
        # Compute the crossover indices            
        point1 = 0
        point2 = random.randint(point1, len(all_flags))
        point3 = random.randint(point2, len(all_flags))
        point4 = len(all_flags)
        
        child1 = individual.Individual()
        self.set_child_flags(mother, child1, all_flags, point1, point2)
        self.set_child_flags(father, child1, all_flags, point2, point3)
        self.set_child_flags(mother, child1, all_flags, point3, point4)
        if children == 1:
            return [child1]
        child2 = individual.Individual()
        self.set_child_flags(father, child2, all_flags, point1, point2)
        self.set_child_flags(mother, child2, all_flags, point2, point3)
        self.set_child_flags(father, child2, all_flags, point3, point4)
        return [child1, child2]
    
    def select_parent(self, cumulative_fitnesses):
        # This implements roulette wheel selection
        for tup in cumulative_fitnesses:
            if tup[0] > random.uniform(0.0,1.0):
                return tup[1]
    
    def do_mutation(self, child):
        debug.verbose_message("Mutating child %d" % child.ID, __name__)
        for flag in child.ppcg_flags.keys():   
            if bool(random.getrandbits(1)):
                child.ppcg_flags[flag] = flag.random_value()
        for flag in child.cc_flags.keys():    
            if bool(random.getrandbits(1)):
                child.cc_flags[flag] = flag.random_value()
        for flag in child.cxx_flags.keys():    
            if bool(random.getrandbits(1)):
                child.cxx_flags[flag] = flag.random_value()
        for flag in child.nvcc_flags.keys():    
            if bool(random.getrandbits(1)):
                child.nvcc_flags[flag] = flag.random_value()
    
    def create_initial(self):
        tile_size_flag       = compiler_flags.get_optimisation_flag(compiler_flags.PPCG.optimisation_flags, compiler_flags.PPCG.tile_size)
        remaining_tile_sizes = tile_size_flag.possible_values[:]
        new_population       = []
        for i in range(0, config.Arguments.population):
            solution = individual.create_random()
            if not remaining_tile_sizes:
                remaining_tile_sizes = tile_size_flag.possible_values[:]
            # Overwrite the current tile size 
            idx           = random.randint(0, len(remaining_tile_sizes) - 1)
            new_tile_size = remaining_tile_sizes[idx]
            remaining_tile_sizes.remove(new_tile_size)
            debug.verbose_message("Overwriting random tile size %d with new tile size %d" % (solution.ppcg_flags[tile_size_flag], new_tile_size), __name__)
            solution.ppcg_flags[tile_size_flag] = new_tile_size
            new_population.append(solution)
        return new_population
    
    def normalise_fitnesses(self, old_population):
        total_fitness = 0.0
        for individual in old_population:
            total_fitness += individual.fitness
        for individual in old_population:
            individual.fitness /= total_fitness
        old_population.sort(key=lambda x: x.fitness, reverse=True)
    
    def basic_evolution(self, old_population):     
        # Normalise the fitness of each individual
        self.normalise_fitnesses(old_population)
        
        # Calculate a prefix sum of the fitnesses
        cumulative_fitnesses = []
        for idx, ind in enumerate(old_population):
            if idx == 0:
                cumulative_fitnesses.insert(idx, (ind.fitness, ind))
            else:
                cumulative_fitnesses.insert(idx, (ind.fitness + cumulative_fitnesses[idx-1][0], ind))
        
        # The new population     
        new_population = []
        
        # Add the elite candidate
        if config.Arguments.elitism:
            try:
                fittest  = individual.get_fittest(old_population)
                clone    = copy.deepcopy(fittest)
                clone.ID = individual.Individual.get_ID()
                new_population.append(clone)
            except internal_exceptions.NoFittestException:
                pass
        
        # Add children using crossover and mutation
        while len(new_population) < len(old_population):
            crossover = getattr(self, config.Arguments.crossover)
            mother    = self.select_parent(cumulative_fitnesses)
            father    = self.select_parent(cumulative_fitnesses)
            # Create as many children as needed
            if len(new_population) < len(old_population) - 2:
                if random.uniform(0.0, 1.0) < config.Arguments.crossover_rate:
                    childList = crossover(mother, father, 2)
                    self.total_crossovers += 1
                else:
                    childList = [mother, father]
            else:
                if random.uniform(0.0, 1.0) < config.Arguments.crossover_rate:
                    childList = crossover(mother, father, 1)
                    self.total_crossovers += 1
                else:
                    if bool(random.getrandbits(1)):
                        childList = [mother]
                    else:
                        childList = [father]
            # Mutate
            for child in childList:
                if random.uniform(0.0, 1.0) < config.Arguments.mutation_rate:
                    self.total_mutations += 1
                    self.do_mutation(child)    
            # Add the children to the new population
            new_population.extend(childList)
        
        assert len(new_population) == len(old_population)
        return new_population
    
    def sizes_evolution(self, fittest):
        # First remove the --tile-size flag
        tile_size_flag = compiler_flags.get_optimisation_flag(compiler_flags.PPCG.optimisation_flags, compiler_flags.PPCG.tile_size)
        del fittest.ppcg_flags[tile_size_flag]
        compiler_flags.PPCG.optimisation_flags.remove(tile_size_flag)
        # Allow a solution to tune on the sizes of each kernel
        for kernel, sizes in fittest.size_data.iteritems():
            new_flag = compiler_flags.SizesFlag(kernel, 
                                                sizes[compiler_flags.SizesFlag.TILE_SIZE],
                                                sizes[compiler_flags.SizesFlag.BLOCK_SIZE],
                                                sizes[compiler_flags.SizesFlag.GRID_SIZE])
            
            fittest.ppcg_flags[new_flag] = new_flag.get_original_value()
            compiler_flags.PPCG.optimisation_flags.append(new_flag)
        
        new_population = []
        for i in range(0, config.Arguments.population):
            clone    = copy.deepcopy(fittest)
            clone.ID = individual.Individual.get_ID()
            for flag in clone.ppcg_flags:
                if isinstance(flag, compiler_flags.SizesFlag):
                    clone.ppcg_flags[flag] = flag.permute(clone.ppcg_flags[flag])
            new_population.append(clone)
        return new_population       
    
    def run(self):        
        self.generations      = collections.OrderedDict()  
        self.total_mutations  = 0
        self.total_crossovers = 0
        
        state_random_population = "random_population"
        state_basic_evolution   = "basic_evolution"
        state_sizes_evolution   = "sizes_evolution"        
        current_state           = state_random_population
        legal_transitions       = set()
        legal_transitions.add((state_random_population, state_basic_evolution))
        legal_transitions.add((state_basic_evolution, state_sizes_evolution))
        legal_transitions.add((state_basic_evolution, state_basic_evolution))
        legal_transitions.add((state_sizes_evolution, state_basic_evolution))
        
        for generation in xrange(1, config.Arguments.generations+1):
            debug.verbose_message("%s Creating generation %d %s" % ('+' * 10, generation, '+' * 10), __name__)
            if current_state == state_random_population:
                self.generations[generation] = self.create_initial()
                next_state = state_basic_evolution
            elif current_state == state_basic_evolution:
                self.generations[generation] = self.basic_evolution(self.generations[generation-1])
                next_state = state_basic_evolution
            elif current_state == state_sizes_evolution:
                debug.verbose_message("Now tuning individual kernel sizes", __name__)
                self.generations[generation] = self.sizes_evolution(individual.get_fittest(self.generations[generation-1]))
                legal_transitions.remove((state_basic_evolution, state_sizes_evolution))
                next_state = state_basic_evolution
            else:
                assert False, "Unknown state reached"
            
            # Generation created, now calculate the fitness of each individual
            for solution in self.generations[generation]:
                solution.run()
                
            if current_state == state_basic_evolution:
                # Decide whether to start tuning on individual kernel sizes in the next state
                if not config.Arguments.no_tune_kernel_sizes and (state_basic_evolution, state_sizes_evolution) in legal_transitions:
                    try:
                        fittest_from_previous = individual.get_fittest(self.generations[generation-1])
                        fittest_from_current  = individual.get_fittest(self.generations[generation])
                        difference            = math.fabs(fittest_from_current.execution_time - fittest_from_previous.execution_time)
                        percentage            = difference/fittest_from_current.execution_time * 100 
                        if percentage < 10:
                            next_state = state_sizes_evolution
                    except internal_exceptions.NoFittestException:
                        pass
                    
            current_state = next_state
                    
    def summarise(self):
        print("%s Summary of %s %s" % ('*' * 30, __name__, '*' * 30))
        print("Total number of mutations:  %d" % (self.total_mutations))
        print("Total number of crossovers: %d" % (self.total_crossovers))
        print
        print("Per-generation summary")
        for generation, population in self.generations.iteritems():
            try:
                fittest = individual.get_fittest(population)
                debug.summary_message("The fittest individual from generation %d had execution time %f seconds" % (generation, fittest.execution_time)) 
                debug.summary_message("To replicate, pass the following to PPCG:")
                debug.summary_message(fittest.ppcg_cmd_line_flags, False)
            except internal_exceptions.NoFittestException:
                pass            

class Random(SearchStrategy):
    """Search using random sampling"""
    
    def run(self):
        self.individuals = []
        for i in xrange(1, config.Arguments.population+1):
            solution = individual.create_random()
            solution.run()
            self.individuals.append(solution)
    
    def summarise(self):
        print("%s Summary of %s %s" % ('*' * 30, __name__, '*' * 30))
        try:
            fittest = individual.get_fittest(self.individuals)
            debug.summary_message("The fittest individual had execution time %f seconds" % (fittest.execution_time)) 
            debug.summary_message("To replicate, pass the following to PPCG:")
            debug.summary_message(fittest.ppcg_cmd_line_flags, False)
        except internal_exceptions.NoFittestException:
            pass

class SimulatedAnnealing(SearchStrategy):
    """Search using simulated annealing"""
    
    def acceptance_probability(self, currentEnergy, newEnergy, temperature):
        if newEnergy < currentEnergy:
            return 1.0
        return math.exp((currentEnergy - newEnergy) / temperature)
    
    def mutate_backend_flags(self, clone_flags, solution_flags):
        for flag in solution_flags.keys():   
            if bool(random.getrandbits(1)):
                idx    = flag.possible_values.index(solution_flags[flag])
                newIdx = (idx + 1) % len(flag.possible_values)
                clone_flags[flag] = flag.possible_values[newIdx]
    
    def mutate(self, solution):
        clone    = copy.deepcopy(solution)
        clone.ID = individual.Individual.get_ID()
        for flag in solution.ppcg_flags.keys():   
            if bool(random.getrandbits(1)):
                if isinstance(flag.possible_values, list):
                    idx    = flag.possible_values.index(solution.ppcg_flags[flag])
                    newIdx = (idx + 1) % len(flag.possible_values)
                    clone.ppcg_flags[flag] = flag.possible_values[newIdx]
                else:
                    assert isinstance(flag.possible_values, dict)
                    clone.ppcg_flags[flag] = flag.permute(solution.ppcg_flags[flag])
                    
        self.mutate_backend_flags(clone.cc_flags, solution.cc_flags)
        self.mutate_backend_flags(clone.cxx_flags, solution.cxx_flags)
        self.mutate_backend_flags(clone.nvcc_flags, solution.nvcc_flags)
        return clone
    
    def run(self):        
        debug.verbose_message("Creating initial solution", __name__)
        current = individual.create_random()
        current.run()   
        self.fittest = current
        
        temperature = config.Arguments.initial_temperature
        for i in range(1, config.Arguments.cooling_steps+1):
            debug.verbose_message("Cooling step %d" % i, __name__)
            temperature *= config.Arguments.cooling
            for j in range(1, config.Arguments.temperature_steps+1):
                debug.verbose_message("Temperature step %d" % j, __name__)
                new = self.mutate(current)
                new.run()       
                if new.status == enums.Status.passed:     
                    if self.acceptance_probability(current.execution_time, new.execution_time, temperature):
                        current = new
                    if current.execution_time < self.fittest.execution_time:
                        self.fittest = current
    
    def summarise(self):
        debug.summary_message("The final individual had execution time %f seconds" % (self.fittest.execution_time)) 
        debug.summary_message("To replicate, pass the following to PPCG:")
        debug.summary_message(self.fittest.ppcg_cmd_line_flags, False)
        