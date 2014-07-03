import random
import config
import re
import os

class Flag:
    """A compiler flag and its possible values"""
    
    def __init__ (self, name, possible_values=[True, False]):
        self.name = name
        self.possible_values = possible_values
        
    def random_value(self):
        idx = random.randint(0,len(self.possible_values)-1)
        return self.possible_values[idx]
        
    def __hash__(self):
        return self.name.__hash__()
    
    def __eq__(self, other):
        return self.name == other.name
    
    def __str__(self):
        return self.name
        
class SizesFlag(Flag):
    """Used in creating the PPCG --sizes flag"""
    
    TILE_SIZE  = 'tile_size'
    GRID_SIZE  = 'grid_size'
    BLOCK_SIZE = 'block_size'
    
    @staticmethod
    def parse_PPCG_dump_sizes(output):                
        kernel_sizes = {}
        for line in output.split(os.linesep):
            if re.match(r'^\{.*\}$', line):
                # Strip out whitespace and the braces {}  
                line = re.sub(r'\s+', '', line)
                line = line[1:-1]
                if not line:
                    return kernel_sizes
                # Rip out the kernel tile, block and grid sizes from PPCG's output
                for size_lexeme in line.split(';'):
                    values = size_lexeme.split('->')
                    assert len(values) == 2
                    kernel_number  = re.findall(r'\d+', values[0])
                    size_parameter = re.findall(r'[a-z]+', values[1])
                    sizes          = re.findall(r'\d+', values[1])
                    sizes          = map(int, sizes)
                    if sizes:
                        assert len(kernel_number) == 1
                        assert len(size_parameter) == 1
                        the_kernel = kernel_number[0]
                        the_param  = size_parameter[0]
                        if the_kernel not in kernel_sizes:
                            kernel_sizes[the_kernel] = {}
                        if the_param == 'tile':
                            kernel_sizes[the_kernel][SizesFlag.TILE_SIZE] = sizes
                        elif the_param == 'grid':
                            kernel_sizes[the_kernel][SizesFlag.GRID_SIZE] = sizes
                        elif the_param == 'block':
                            kernel_sizes[the_kernel][SizesFlag.BLOCK_SIZE] = sizes
                        else:
                            assert False, "Unknown sizes parameter %s for kernel %s" % (the_param, the_kernel)
        assert kernel_sizes, "Unable to find sizes information from PPCG output"
        return kernel_sizes    
    
    class Size():
        def __init__(self, dimensions, lower_bound, upper_bound):
            self.dimensions = dimensions
            # Create a tuple of the required dimension
            self.possible_values = ([x for x in range(lower_bound, upper_bound)],) * dimensions
            
        def random_value(self):
            value = ()
            for i in range(0,len(self.possible_values)):
                idx = random.randint(0,len(self.possible_values[i])-1)
                value += (self.possible_values[i][idx],)
            return value
        
        def permute(self, value):
            newValue = ()
            for i in range(0, len(value)):
                idx      = self.possible_values[i].index(value[i])
                distance = random.randint(0, 5) 
                if bool(random.getrandbits(1)):
                    newIdx = (idx + distance) % len(self.possible_values[i])
                else:
                    newIdx = (idx - distance) % len(self.possible_values[i])
                newValue += (self.possible_values[i][newIdx],)
            return newValue
               
    def __init__(self, kernel, tile_size, block_size, grid_size):
        Flag.__init__(self, '--sizes', None)
        self.kernel = kernel
        self.possible_values = {}
        self.possible_values[SizesFlag.TILE_SIZE]  = self.Size(len(tile_size), config.Arguments.tile_size[0], config.Arguments.tile_size[1]+1)
        self.possible_values[SizesFlag.BLOCK_SIZE] = self.Size(len(block_size), config.Arguments.block_size[0], config.Arguments.block_size[1]+1) 
        self.possible_values[SizesFlag.GRID_SIZE]  = self.Size(len(grid_size), config.Arguments.grid_size[0], config.Arguments.grid_size[1]+1)
        self.original_tile_size  = tile_size
        self.original_block_size = block_size
        self.original_grid_size  = grid_size
        
    def get_original_value(self):
        return {SizesFlag.TILE_SIZE:  tuple(self.original_tile_size), 
                SizesFlag.BLOCK_SIZE: tuple(self.original_block_size), 
                SizesFlag.GRID_SIZE:  tuple(self.original_grid_size)}
        
    def random_value(self):
        tile_size  = self.possible_values[SizesFlag.TILE_SIZE].random_value()
        block_size = self.possible_values[SizesFlag.BLOCK_SIZE].random_value()
        grid_size  =  self.possible_values[SizesFlag.GRID_SIZE].random_value()
        return {SizesFlag.TILE_SIZE:  tile_size, 
                SizesFlag.BLOCK_SIZE: block_size, 
                SizesFlag.GRID_SIZE:  grid_size}
        
    def permute(self, value):
        return {SizesFlag.TILE_SIZE:  self.possible_values[SizesFlag.TILE_SIZE].permute(value[SizesFlag.TILE_SIZE]), 
                SizesFlag.BLOCK_SIZE: self.possible_values[SizesFlag.BLOCK_SIZE].permute(value[SizesFlag.BLOCK_SIZE]),
                SizesFlag.GRID_SIZE:  self.possible_values[SizesFlag.GRID_SIZE].permute(value[SizesFlag.GRID_SIZE])}
        
    def __hash__(self):
        return self.name.__hash__() + self.kernel.__hash__()
    
    def __eq__(self, other):
        if not isinstance(other, SizesFlag):
            return False
        return (self.name, self.kernel) == (other.name, other.kernel)   
    
    def __str__(self):
        return self.name + self.kernel   
    
def get_optimisation_flag(optimisation_flags, name):
    for flag in optimisation_flags:
        if flag.name == name:
            return flag
    return None

class PPCG:    
    """All PPCG flags"""
    
    # The following flags can be passed to PPCG but they result in very slow performance
    isl_context                             = '--isl-context'
    isl_gbr                                 = '--isl-gbr'
    isl_closure                             = '--isl-closure'
    isl_gbr_only_first                      = '--isl-gbr-only-first'
    isl_bernstein_recurse                   = '--isl-bernstein-recurse'
    no_isl_bernstein_triangulate            = '--no-isl-bernstein-triangulate'
    no_isl_pip_symmetry                     = '--no-isl-pip-symmetry'
    isl_convex_hull                         = '--isl-convex-hull',
    no_isl_coalesce_bounded_wrapping        = '--no-isl-coalesce-bounded-wrapping'
    no_isl_schedule_parametric              = '--no-isl-schedule-parametric'
    no_isl_schedule_outer_coincidence       = '--no-isl-schedule-outer-coincidence'
    no_isl_schedule_maximize_band_depth     = '--no-isl-schedule-maximize-band-depth'
    no_isl_schedule_split_scaled            = '--no-isl-schedule-split-scaled'
    isl_schedule_algorithm                  = '--isl-schedule-algorithm'
    no_isl_tile_scale_tile_loops            = '--no-isl-tile-scale-tile-loops'
    no_isl_tile_shift_point_loops           = '--no-isl-tile-shift-point-loops'
    no_isl_ast_build_atomic_upper_bound     = '--no-isl-ast-build-atomic-upper-bound'
    no_isl_ast_build_prefer_pdiv            = '--no-isl-ast-build-prefer-pdiv'
    no_isl_ast_build_exploit_nested_bounds  = '--no-isl-ast-build-exploit-nested-bounds'
    isl_ast_build_group_coscheduled         = '--isl-ast-build-group-coscheduled'
    isl_ast_build_separation_bounds         = '--isl-ast-build-separation-bounds'
    no_isl_ast_build_scale_strides          = '--no-isl-ast-build-scale-strides'
    no_isl_ast_build_allow_else             = '--no-isl-ast-build-allow-else'
    no_isl_ast_build_allow_or               = '--no-isl-ast-build-allow-or'
    
    isl_flag_map = {}
    isl_flag_map[isl_context]                               = Flag(isl_context, ['gbr', 'lexmin'])
    isl_flag_map[isl_gbr]                                   = Flag(isl_gbr, ['never', 'once', 'always'])
    isl_flag_map[isl_closure]                               = Flag(isl_closure, ['isl', 'box'])
    isl_flag_map[isl_gbr_only_first]                        = Flag(isl_gbr_only_first)
    isl_flag_map[isl_bernstein_recurse]                     = Flag(isl_bernstein_recurse, ['none', 'factors', 'intervals', 'full'])
    isl_flag_map[no_isl_bernstein_triangulate]              = Flag(no_isl_bernstein_triangulate)
    isl_flag_map[no_isl_pip_symmetry]                       = Flag(no_isl_pip_symmetry)
    isl_flag_map[isl_convex_hull]                           = Flag(isl_convex_hull, ['wrap', 'fm'])
    isl_flag_map[no_isl_coalesce_bounded_wrapping]          = Flag(no_isl_coalesce_bounded_wrapping)
    isl_flag_map[no_isl_schedule_parametric]                = Flag(no_isl_schedule_parametric)
    isl_flag_map[no_isl_schedule_outer_coincidence]         = Flag(no_isl_schedule_outer_coincidence)
    isl_flag_map[no_isl_schedule_maximize_band_depth]       = Flag(no_isl_schedule_maximize_band_depth)
    isl_flag_map[no_isl_schedule_split_scaled]              = Flag(no_isl_schedule_split_scaled)
    isl_flag_map[isl_schedule_algorithm]                    = Flag(isl_schedule_algorithm, ['isl', 'feautrier'])
    isl_flag_map[no_isl_tile_scale_tile_loops]              = Flag(no_isl_tile_scale_tile_loops)
    isl_flag_map[no_isl_tile_shift_point_loops]             = Flag(no_isl_tile_shift_point_loops)
    isl_flag_map[no_isl_ast_build_atomic_upper_bound]       = Flag(no_isl_ast_build_atomic_upper_bound)
    isl_flag_map[no_isl_ast_build_prefer_pdiv]              = Flag(no_isl_ast_build_prefer_pdiv)
    isl_flag_map[no_isl_ast_build_exploit_nested_bounds]    = Flag(no_isl_ast_build_exploit_nested_bounds)
    isl_flag_map[isl_ast_build_group_coscheduled]           = Flag(isl_ast_build_group_coscheduled)
    isl_flag_map[isl_ast_build_separation_bounds]           = Flag(isl_ast_build_separation_bounds, ['explicit', 'implicit'])
    isl_flag_map[no_isl_ast_build_scale_strides]            = Flag(no_isl_ast_build_scale_strides)
    isl_flag_map[no_isl_ast_build_allow_else]               = Flag(no_isl_ast_build_allow_else)
    isl_flag_map[no_isl_ast_build_allow_or]                 = Flag(no_isl_ast_build_allow_or)
    
    isl_schedule_fuse                   = '--isl-schedule-fuse'
    no_isl_schedule_separate_components = '--no-isl-schedule-separate-components'
    no_wrap                             = '--no-wrap'
    no_scale_tile_loops                 = '--no-scale-tile-loops'
    no_shared_memory                    = '--no-shared-memory'
    no_private_memory                   = '--no-private-memory'
    no_live_range_reordering            = '--no-live-range-reordering'
    max_shared_memory                   = '--max-shared-memory'
    tile_size                           = '--tile-size'
    sizes                               = '--sizes'
    
    flag_map = {}
    flag_map[isl_schedule_fuse]                    = Flag(isl_schedule_fuse, ['max', 'min'])
    flag_map[no_isl_schedule_separate_components]  = Flag(no_isl_schedule_separate_components)
    flag_map[no_wrap]                              = Flag(no_wrap)
    flag_map[no_scale_tile_loops]                  = Flag(no_scale_tile_loops)
    flag_map[no_shared_memory]                     = Flag(no_shared_memory)
    flag_map[no_private_memory]                    = Flag(no_private_memory)
    flag_map[no_live_range_reordering]             = Flag(no_live_range_reordering)
    
    optimisation_flags = []
    
class CC:
    """All C compiler flags"""
    
    optimisation_flags = []
    
class CXX:
    """All C++ compiler flags"""
    
    optimisation_flags = []
    
class NVCC:
    """All CUDA compiler flags"""
    
    optimisation_flags = [Flag('--ftz'),
                          Flag('--prec-sqrt'),
                          Flag('--prec-div'),
                          Flag('--fmad'),
                          Flag('--maxrregcount', [x for x in range(16,128+1) if x % 4 == 0])]
    
class LLVM:
    """All optimisation flags for different versions of LLVM"""
        
    optimisation_flags_20 = [Flag('-adce'),
                             Flag('-argpromotion'),
                             Flag('-block-placement'),
                             Flag('-break-crit-edges'),
                             Flag('-cee'),
                             Flag('-condprop'),
                             Flag('-constmerge'),
                             Flag('-constprop'),
                             Flag('-dce'),
                             Flag('-deadargelim'),
                             Flag('-die'),
                             Flag('-dse'),
                             Flag('-gcse'),
                             Flag('-globaldce'),
                             Flag('-globalopt'),
                             Flag('-indmemrem'),
                             Flag('-indvars'),
                             Flag('-inline'),
                             Flag('-insert-block-profiling'),
                             Flag('-insert-edge-profiling'),
                             Flag('-insert-function-profiling'),
                             Flag('-insert-null-profiling-rs'),
                             Flag('-insert-rs-profiling-framework'),
                             Flag('-instcombine'),
                             Flag('-internalize'),
                             Flag('-ipconstprop'),
                             Flag('-ipsccp'),
                             Flag('-lcssa'),
                             Flag('-licm'),
                             Flag('-loop-extract'),
                             Flag('-loop-extract-single'),
                             Flag('-loop-reduce'),
                             Flag('-loop-unroll'),
                             Flag('-loop-unswitch'),
                             Flag('-loopsimplify'),
                             Flag('-lower-packed'),
                             Flag('-lowerallocs'),
                             Flag('-lowergc'),
                             Flag('-lowerinvoke'),
                             Flag('-lowerselect'),
                             Flag('-lowersetjmp'),
                             Flag('-lowerswitch'),
                             Flag('-mem2reg'),
                             Flag('-mergereturn'),
                             Flag('-predsimplify'),
                             Flag('-prune-eh'),
                             Flag('-raiseallocs'),
                             Flag('-reassociate'),
                             Flag('-reg2mem'),
                             Flag('-scalarrepl'),
                             Flag('-sccp'),
                             Flag('-simplify-libcalls'),
                             Flag('-simplifycfg'),
                             Flag('-strip'),
                             Flag('-tailcallelim'),
                             Flag('-tailduplicate')]
    
    optimisation_flags_21 = optimisation_flags_20[:]
    
    optimisation_flags_22 = optimisation_flags_21[:]
    optimisation_flags_22.append(Flag('-gvn'))
    optimisation_flags_22.append(Flag('-gvnpre'))
    optimisation_flags_22.append(Flag('-loop-index-split'))
    optimisation_flags_22.append(Flag('-loop-rotate'))
    
    optimisation_flags_23 = optimisation_flags_22[:]
    optimisation_flags_23.append(Flag('-jump-threading'))
    optimisation_flags_23.append(Flag('-loop-deletion'))
    optimisation_flags_23.append(Flag('-memcpyopt'))
    optimisation_flags_23.append(Flag('-strip-dead-prototypes'))
    optimisation_flags_23.append(Flag('-sretpromotion'))    
    
    optimisation_flags_24 = optimisation_flags_23[:]
    
    optimisation_flags_25 = optimisation_flags_23[:]
    
    optimisation_flags_26 = optimisation_flags_23[:]
    
    optimisation_flags_27 = optimisation_flags_23[:]
    optimisation_flags_27.remove(Flag('-gcse'))
    optimisation_flags_27.remove(Flag('-gvnpre'))
    optimisation_flags_27.remove(Flag('-predsimplify'))
    optimisation_flags_27.remove(Flag('-raiseallocs'))
    
    optimisation_flags_28 = optimisation_flags_27[:]
    optimisation_flags_28.append(Flag('-abcd'))
    optimisation_flags_28.append(Flag('-always-inline'))
    optimisation_flags_28.remove(Flag('-condprop'))
    optimisation_flags_28.append(Flag('-functionattrs'))
    optimisation_flags_28.remove(Flag('-indmemrem'))
    optimisation_flags_28.remove(Flag('-insert-block-profiling'))
    optimisation_flags_28.remove(Flag('-insert-function-profiling')) 
    optimisation_flags_28.remove(Flag('-insert-null-profiling-rs')) 
    optimisation_flags_28.remove(Flag('-insert-rs-profiling-framework')) 
    optimisation_flags_28.append(Flag('-insert-optimal-edge-profiling'))  
    optimisation_flags_28.append(Flag('-mergefunc'))
    optimisation_flags_28.append(Flag('-partial-inliner'))
    optimisation_flags_28.append(Flag('-partialspecialization'))
    optimisation_flags_28.append(Flag('-sink'))   
    optimisation_flags_28.append(Flag('-simplify-libcalls-halfpowr')) 
    optimisation_flags_28.append(Flag('-split-geps')) 
    optimisation_flags_28.append(Flag('-ssi')) 
    optimisation_flags_28.append(Flag('-ssi-everything'))
    optimisation_flags_28.append(Flag('-strip-dead-debug-info'))
    optimisation_flags_28.append(Flag('-strip-debug-declare'))
    optimisation_flags_28.append(Flag('-strip-nondebug'))
    
    optimisation_flags_29 = optimisation_flags_28[:]
    optimisation_flags_29.remove(Flag('-loopsimplify'))
    optimisation_flags_29.append(Flag('-loop-simplify'))
    
    optimisation_flags_30 = [Flag('-adce'),
                             Flag('-always-inline'),
                             Flag('-argpromotion'),
                             Flag('-block-placement'),
                             Flag('-break-crit-edges'),
                             Flag('-codegenprepare'),
                             Flag('-constmerge'),
                             Flag('-constprop'),
                             Flag('-dce'),
                             Flag('-deadargelim'),
                             Flag('-die'),
                             Flag('-dse'),
                             Flag('-functionattrs'),
                             Flag('-globaldce'),
                             Flag('-globalopt'),
                             Flag('-gvn'),
                             Flag('-indvars'),
                             Flag('-inline'),
                             Flag('-insert-edge-profiling'),
                             Flag('-insert-optimal-edge-profiling'),
                             Flag('-instcombine'),
                             Flag('-internalize'),
                             Flag('-ipconstprop'),
                             Flag('-ipsccp'),
                             Flag('-jump-threading'),
                             Flag('-lcssa'),
                             Flag('-licm'),
                             Flag('-loop-deletion'),
                             Flag('-loop-extract'),
                             Flag('-loop-extract-single'),
                             Flag('-loop-reduce'),
                             Flag('-loop-rotate'),
                             Flag('-loop-simplify'),
                             Flag('-loop-unroll'),
                             Flag('-loop-unswitch'),
                             Flag('-loweratomic'),
                             Flag('-lowerinvoke'),
                             Flag('-lowerswitch'),
                             Flag('-mem2reg'),
                             Flag('-memcpyopt'),
                             Flag('-mergefunc'),
                             Flag('-mergereturn'),
                             Flag('-partial-inliner'),
                             Flag('-prune-eh'),
                             Flag('-reassociate'),
                             Flag('-reg2mem'),
                             Flag('-scalarrepl'),
                             Flag('-sccp'),
                             Flag('-simplify-libcalls'),
                             Flag('-simplifycfg'),
                             Flag('-sink'),
                             Flag('-sretpromotion'),
                             Flag('-strip'),
                             Flag('-strip-dead-debug-info'),
                             Flag('-strip-dead-prototypes'),
                             Flag('-strip-debug-declare'),
                             Flag('-strip-nondebug'),
                             Flag('-tailcallelim'),
                             Flag('-tailduplicate')]
    
    optimisation_flags_31 = optimisation_flags_30[:]
    optimisation_flags_31.append(Flag('-bb-vectorize'))
    
    optimisation_flags_32 = optimisation_flags_31[:]
    optimisation_flags_32.remove(Flag('-tailduplicate'))
    
    optimisation_flags_33 = optimisation_flags_32[:]
    optimisation_flags_33.remove(Flag('-sretpromotion'))
    
    optimisation_flags_34 = optimisation_flags_33[:]

class GNU:
    """All optimisation flags for different versions of gcc/g++"""
    
    optimisation_flags_441 = [#O1 turns on the following flags
                              Flag('-fauto-inc-dec'),
                              Flag('-fcprop-registers'),
                              Flag('-fdce'),
                              Flag('-fdefer-pop'),
                              Flag('-fdelayed-branch'),
                              Flag('-fdse'),
                              Flag('-fguess-branch-probability'),
                              Flag('-fif-conversion2'),
                              Flag('-fif-conversion'),
                              Flag('-finline-small-functions'),
                              Flag('-fipa-pure-const'),
                              Flag('-fipa-reference'),
                              Flag('-fmerge-constants'),
                              Flag('-fsplit-wide-types'),
                              Flag('-ftree-builtin-call-dce'),
                              Flag('-ftree-ccp'),
                              Flag('-ftree-ch'),
                              Flag('-ftree-copyrename'),
                              Flag('-ftree-dce'),
                              Flag('-ftree-dominator-opts'),
                              Flag('-ftree-dse'),
                              Flag('-ftree-fre'),
                              Flag('-ftree-sra'),
                              Flag('-ftree-ter'),
                              Flag('-funit-at-a-time'),
                              Flag('-fomit-frame-pointer'),
                              #02 turns on the following flags
                         Flag('-fthread-jumps'),
                         Flag('-falign-functions'),
                         Flag('-falign-jumps'),
                         Flag('-falign-loops'),
                         Flag('-falign-labels'),
                         Flag('-fcaller-saves'),
                         Flag('-fcrossjumping'),
                         Flag('-fcse-follow-jumps'),
                         Flag('-fcse-skip-blocks'),
                         Flag('-fdelete-null-pointer-checks'),
                         Flag('-fexpensive-optimizations'),
                         Flag('-fgcse'),
                         Flag('-fgcse-lm'),
                         Flag('-findirect-inlining'),
                         Flag('-foptimize-sibling-calls'),
                         Flag('-fpeephole2'),
                         Flag('-fregmove'),
                         Flag('-freorder-blocks'),
                         Flag('-freorder-functions'),
                         Flag('-frerun-cse-after-loop'),
                         Flag('-fsched-interblock'),
                         Flag('-fsched-spec'),
                         Flag('-fschedule-insns'),
                         Flag('-fschedule-insns2'),
                         Flag('-fstrict-aliasing'),
                         Flag('-fstrict-overflow'),
                         Flag('-ftree-switch-conversion'),
                         Flag('-ftree-pre'),
                         Flag('-ftree-vrp'),
                         #03 turns on the following flags
                         Flag('-finline-functions'), 
                         Flag('-funswitch-loops'),
                         Flag('-fpredictive-commoning'),
                         Flag('-fgcse-after-reload'), 
                         Flag('-ftree-vectorize')]
    
    optimisation_flags_442 = optimisation_flags_441[:]
    
    optimisation_flags_443 = optimisation_flags_441[:]
    
    optimisation_flags_444 = optimisation_flags_441[:]
    
    optimisation_flags_445 = optimisation_flags_441[:]
    optimisation_flags_445.append(Flag('-fipa-cp-clone'))
    
    optimisation_flags_446 = optimisation_flags_445[:]
    
    optimisation_flags_447 = optimisation_flags_445[:]
    
    optimisation_flags_450 = [#01 turns on the following flags 
                         Flag('-fauto-inc-dec'),
                         Flag('-fcprop-registers'),
                         Flag('-fdce'),
                         Flag('-fdefer-pop'),
                         Flag('-fdelayed-branch'),
                         Flag('-fdse'),
                         Flag('-fguess-branch-probability'),
                         Flag('-fif-conversion2'),
                         Flag('-fif-conversion'),
                         Flag('-fipa-pure-const'),
                         Flag('-fipa-reference'),
                         Flag('-fmerge-constants'),
                         Flag('-fsplit-wide-types'),
                         Flag('-ftree-builtin-call-dce'),
                         Flag('-ftree-ccp'),
                         Flag('-ftree-ch'),
                         Flag('-ftree-copyrename'),
                         Flag('-ftree-dce'),
                         Flag('-ftree-dominator-opts'),
                         Flag('-ftree-dse'),
                         Flag('-ftree-forwprop'),
                         Flag('-ftree-fre'),
                         Flag('-ftree-phiprop'),
                         Flag('-ftree-sra'),
                         Flag('-ftree-pta'),
                         Flag('-ftree-ter'),
                         Flag('-funit-at-a-time'),
                         Flag('-fomit-frame-pointer'),
                         #02 turns on the following flags
                         Flag('-fthread-jumps'),
                         Flag('-falign-functions'),
                         Flag('-falign-jumps'),
                         Flag('-falign-loops'),
                         Flag('-falign-labels'),
                         Flag('-fcaller-saves'),
                         Flag('-fcrossjumping'),
                         Flag('-fcse-follow-jumps'),
                         Flag('-fcse-skip-blocks'),
                         Flag('-fdelete-null-pointer-checks'),
                         Flag('-fexpensive-optimizations'),
                         Flag('-fgcse'),
                         Flag('-fgcse-lm'),
                         Flag('-finline-small-functions'),
                         Flag('-findirect-inlining'),
                         Flag('-fipa-sra'),
                         Flag('-foptimize-sibling-calls'),
                         Flag('-fpeephole2'),
                         Flag('-fregmove'),
                         Flag('-freorder-blocks'),
                         Flag('-freorder-functions'),
                         Flag('-frerun-cse-after-loop'),
                         Flag('-fsched-interblock'),
                         Flag('-fsched-spec'),
                         Flag('-fschedule-insns'),
                         Flag('-fschedule-insns2'),
                         Flag('-fstrict-aliasing'),
                         Flag('-fstrict-overflow'),
                         Flag('-ftree-switch-conversion'),
                         Flag('-ftree-pre'),
                         Flag('-ftree-vrp'),
                         #03 turns on the following flags 
                         Flag('-finline-functions'), 
                         Flag('-funswitch-loops'),
                         Flag('-fpredictive-commoning'),
                         Flag('-fgcse-after-reload'), 
                         Flag('-ftree-vectorize')]
    
    optimisation_flags_451 = optimisation_flags_450[:]
    
    optimisation_flags_452 = optimisation_flags_451[:]
    optimisation_flags_452.append(Flag('-fipa-cp-clone'))
    
    optimisation_flags_453 = optimisation_flags_452[:]
    
    optimisation_flags_454 = optimisation_flags_452[:]
    
    optimisation_flags_460 = [#01 turns on the following flags
                         Flag('-fauto-inc-dec'),
                         Flag('-fcompare-elim'),
                         Flag('-fcprop-registers'),
                         Flag('-fdce'),
                         Flag('-fdefer-pop'),
                         Flag('-fdelayed-branch'),
                         Flag('-fdse'),
                         Flag('-fguess-branch-probability'),
                         Flag('-fif-conversion2'),
                         Flag('-fif-conversion'),
                         Flag('-fipa-pure-const'),
                         Flag('-fipa-profile'),
                         Flag('-fipa-reference'),
                         Flag('-fmerge-constants'),
                         Flag('-fsplit-wide-types'),
                         Flag('-ftree-bit-ccp'),
                         Flag('-ftree-builtin-call-dce'),
                         Flag('-ftree-ccp'),
                         Flag('-ftree-ch'),
                         Flag('-ftree-copyrename'),
                         Flag('-ftree-dce'),
                         Flag('-ftree-dominator-opts'),
                         Flag('-ftree-dse'),
                         Flag('-ftree-forwprop'),
                         Flag('-ftree-fre'),
                         Flag('-ftree-phiprop'),
                         Flag('-ftree-sra'),
                         Flag('-ftree-pta'),
                         Flag('-ftree-ter'),
                         Flag('-funit-at-a-time'),
                         Flag('-fomit-frame-pointer'),
                         #02 turns on the following flags 
                         Flag('-fthread-jumps'),
                         Flag('-falign-functions'),
                         Flag('-falign-jumps'),
                         Flag('-falign-loops'),
                         Flag('-falign-labels'),
                         Flag('-fcaller-saves'),
                         Flag('-fcrossjumping'),
                         Flag('-fcse-follow-jumps'),
                         Flag('-fcse-skip-blocks'),
                         Flag('-fdelete-null-pointer-checks'),
                         Flag('-fdevirtualize'),
                         Flag('-fexpensive-optimizations'),
                         Flag('-fgcse'),
                         Flag('-fgcse-lm'),
                         Flag('-finline-small-functions'),
                         Flag('-findirect-inlining'),
                         Flag('-fipa-sra'),
                         Flag('-foptimize-sibling-calls'),
                         Flag('-fpartial-inlining'),
                         Flag('-fpeephole2'),
                         Flag('-fregmove'),
                         Flag('-freorder-blocks'),
                         Flag('-freorder-functions'),
                         Flag('-frerun-cse-after-loop'),
                         Flag('-fsched-interblock'),
                         Flag('-fsched-spec'),
                         Flag('-fschedule-insns'),
                         Flag('-fschedule-insns2'),
                         Flag('-fstrict-aliasing'),
                         Flag('-fstrict-overflow'),
                         Flag('-ftree-switch-conversion'),
                         Flag('-ftree-pre'),
                         Flag('-ftree-vrp'),
                         #03 turns on the following flags
                         Flag('-finline-functions'), 
                         Flag('-funswitch-loops'),
                         Flag('-fpredictive-commoning'),
                         Flag('-fgcse-after-reload'), 
                         Flag('-ftree-vectorize'),
                         Flag('-fipa-cp-clone')]
    
    optimisation_flags_461 = optimisation_flags_460[:]
    
    optimisation_flags_462 = optimisation_flags_460[:]
    
    optimisation_flags_463 = optimisation_flags_460[:]
    
    optimisation_flags_464 = optimisation_flags_460[:]
    
    optimisation_flags_470 = [#01 turns on the following flags
                         Flag('-fauto-inc-dec'),
                         Flag('-fcompare-elim'),
                         Flag('-fcprop-registers'),
                         Flag('-fdce'),
                         Flag('-fdefer-pop'),
                         Flag('-fdelayed-branch'),
                         Flag('-fdse'),
                         Flag('-fguess-branch-probability'),
                         Flag('-fif-conversion2'),
                         Flag('-fif-conversion'),
                         Flag('-fipa-pure-const'),
                         Flag('-fipa-profile'),
                         Flag('-fipa-reference'),
                         Flag('-fmerge-constants'),
                         Flag('-fsplit-wide-types'),
                         Flag('-ftree-bit-ccp'),
                         Flag('-ftree-builtin-call-dce'),
                         Flag('-ftree-ccp'),
                         Flag('-ftree-ch'),
                         Flag('-ftree-copyrename'),
                         Flag('-ftree-dce'),
                         Flag('-ftree-dominator-opts'),
                         Flag('-ftree-dse'),
                         Flag('-ftree-forwprop'),
                         Flag('-ftree-fre'),
                         Flag('-ftree-phiprop'),
                         Flag('-ftree-sra'),
                         Flag('-ftree-pta'),
                         Flag('-ftree-ter'),
                         Flag('-funit-at-a-time'),
                         Flag('-fomit-frame-pointer'),
                         #02 turns on the following flags 
                         Flag('-fthread-jumps'),
                         Flag('-falign-functions'),
                         Flag('-falign-jumps'),
                         Flag('-falign-loops'),
                         Flag('-falign-labels'),
                         Flag('-fcaller-saves'),
                         Flag('-fcrossjumping'),
                         Flag('-fcse-follow-jumps'),
                         Flag('-fcse-skip-blocks'),
                         Flag('-fdelete-null-pointer-checks'),
                         Flag('-fdevirtualize'),
                         Flag('-fexpensive-optimizations'),
                         Flag('-fgcse'),
                         Flag('-fgcse-lm'),
                         Flag('-finline-small-functions'),
                         Flag('-findirect-inlining'),
                         Flag('-fipa-sra'),
                         Flag('-foptimize-sibling-calls'),
                         Flag('-fpartial-inlining'),
                         Flag('-fpeephole2'),
                         Flag('-fregmove'),
                         Flag('-freorder-blocks'),
                         Flag('-freorder-functions'),
                         Flag('-frerun-cse-after-loop'),
                         Flag('-fsched-interblock'),
                         Flag('-fsched-spec'),
                         Flag('-fschedule-insns'),
                         Flag('-fschedule-insns2'),
                         Flag('-fstrict-aliasing'),
                         Flag('-fstrict-overflow'),
                         Flag('-ftree-switch-conversion'),
                         Flag('-ftree-tail-merge'),
                         Flag('-ftree-pre'),
                         Flag('-ftree-vrp'),
                         #03 turns on the following flags 
                         Flag('-finline-functions'), 
                         Flag('-funswitch-loops'),
                         Flag('-fpredictive-commoning'),
                         Flag('-fgcse-after-reload'), 
                         Flag('-ftree-vectorize'),
                         Flag('-fipa-cp-clone')]
    
    optimisation_flags_471 = optimisation_flags_470[:]
    
    optimisation_flags_472 = optimisation_flags_470[:]
    
    optimisation_flags_473 = optimisation_flags_470[:]
    
    optimisation_flags_480 = [#01 turns on the following flags 
                         Flag('-fauto-inc-dec'),
                         Flag('-fcompare-elim'),
                         Flag('-fcprop-registers'),
                         Flag('-fdce'),
                         Flag('-fdefer-pop'),
                         Flag('-fdelayed-branch'),
                         Flag('-fdse'),
                         Flag('-fguess-branch-probability'),
                         Flag('-fif-conversion2'),
                         Flag('-fif-conversion'),
                         Flag('-fipa-pure-const'),
                         Flag('-fipa-profile'),
                         Flag('-fipa-reference'),
                         Flag('-fmerge-constants'),
                         Flag('-fsplit-wide-types'),
                         Flag('-ftree-bit-ccp'),
                         Flag('-ftree-builtin-call-dce'),
                         Flag('-ftree-ccp'),
                         Flag('-ftree-ch'),
                         Flag('-ftree-copyrename'),
                         Flag('-ftree-dce'),
                         Flag('-ftree-dominator-opts'),
                         Flag('-ftree-dse'),
                         Flag('-ftree-forwprop'),
                         Flag('-ftree-fre'),
                         Flag('-ftree-phiprop'),
                         Flag('-ftree-slsr'),
                         Flag('-ftree-sra'),
                         Flag('-ftree-pta'),
                         Flag('-ftree-ter'),
                         Flag('-funit-at-a-time'),
                         Flag('-fomit-frame-pointer'),
                         #02 turns on the following flags
                         Flag('-fthread-jumps'),
                         Flag('-falign-functions'),
                         Flag('-falign-jumps'),
                         Flag('-falign-loops'),
                         Flag('-falign-labels'),
                         Flag('-fcaller-saves'),
                         Flag('-fcrossjumping'),
                         Flag('-fcse-follow-jumps'),
                         Flag('-fcse-skip-blocks'),
                         Flag('-fdelete-null-pointer-checks'),
                         Flag('-fdevirtualize'),
                         Flag('-fexpensive-optimizations'),
                         Flag('-fgcse'),
                         Flag('-fgcse-lm'),
                         Flag('-finline-small-functions'),
                         Flag('-findirect-inlining'),
                         Flag('-fipa-sra'),
                         Flag('-foptimize-sibling-calls'),
                         Flag('-fpartial-inlining'),
                         Flag('-fpeephole2'),
                         Flag('-fregmove'),
                         Flag('-freorder-blocks'),
                         Flag('-freorder-functions'),
                         Flag('-frerun-cse-after-loop'),
                         Flag('-fsched-interblock'),
                         Flag('-fsched-spec'),
                         Flag('-fschedule-insns'),
                         Flag('-fschedule-insns2'),
                         Flag('-fstrict-aliasing'),
                         Flag('-fstrict-overflow'),
                         Flag('-ftree-switch-conversion'),
                         Flag('-ftree-tail-merge'),
                         Flag('-ftree-pre'),
                         Flag('-ftree-vrp'),
                         #03 turns on the following flags
                         Flag('-finline-functions'), 
                         Flag('-funswitch-loops'),
                         Flag('-fpredictive-commoning'),
                         Flag('-fgcse-after-reload'), 
                         Flag('-ftree-vectorize'),
                         Flag('-fvect-cost-model'),
                         Flag('-ftree-partial-pre'),
                         Flag('-fipa-cp-clone')]
    
    optimisation_flags_481 = optimisation_flags_480[:]
    
    optimisation_flags_482 = optimisation_flags_480[:]
    
