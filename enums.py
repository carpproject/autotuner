class Targets:
    cuda   = "cuda"
    opencl = "opencl"
    
class Crossover:
    one_point = "one_point"
    two_point = "two_point"

class Compilers:
    gcc     = "gcc"
    gxx     = "g++"
    nvcc    = "nvcc"
    clang   = "clang"
    clangxx = "clang++"
    llvm    = "llvm"
    
class SearchStrategy:
    ga                  = "ga"
    random              = "random"
    simulated_annealing = "simulated-annealing"

class Status:
    passed = "passed"
    failed = "failed"
    