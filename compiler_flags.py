import random
import config
import re
import os
import abc

class Flag:
    """A compiler flag"""
    
    __metaclass__ = abc.ABCMeta
        
    def __init__ (self, name):
        self.name = name
        
    def __hash__(self):
        return self.name.__hash__()
    
    def __eq__(self, other):
        return self.name == other.name
    
    def __str__(self):
        return self.name
    
    @abc.abstractmethod
    def get_command_line_string(self, value):
        pass
    
class EnumerationFlag(Flag):
    """Models compiler flags where it is easy to enumerate the values up front"""
    
    def __init__ (self, name, possible_values=[True, False]):
        Flag.__init__(self, name)
        self.possible_values = possible_values
    
    def random_value(self):
        idx = random.randint(0,len(self.possible_values)-1)
        return self.possible_values[idx]
    
    def get_command_line_string(self, value):
        if type(value) is bool:
            if value:
                return self.name
            else:
                return ""
        else:
            return "%s %s" % (self.name, value.__str__( ))
    
class Size():
    """Models a tile, block or grid size"""
    
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
        
class SizesFlag(Flag):
    """Models the PPCG --sizes flag"""
    
    TILE_SIZE            = 'tile_size'
    GRID_SIZE            = 'grid_size'
    BLOCK_SIZE           = 'block_size'
    ALL_KERNELS_SENTINEL = -1
    
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
               
    def __init__(self):
        Flag.__init__(self, '--sizes')
    
    def random_value(self):
        per_kernel_size_info = {}
        tile_dimensions      = random.randint(1,config.Arguments.tile_dimensions)
        block_dimensions     = random.randint(1,config.Arguments.block_dimensions)
        grid_dimensions      = random.randint(1,config.Arguments.grid_dimensions)
        tile_size            = Size(tile_dimensions, config.Arguments.tile_size[0], config.Arguments.tile_size[1]).random_value()
        block_size           = Size(block_dimensions, config.Arguments.block_size[0], config.Arguments.block_size[1]).random_value()
        grid_size            = Size(grid_dimensions, config.Arguments.grid_size[0], config.Arguments.grid_size[1]).random_value()
        per_kernel_size_info[SizesFlag.ALL_KERNELS_SENTINEL] = {SizesFlag.TILE_SIZE:  tile_size, 
                                                                SizesFlag.BLOCK_SIZE: block_size, 
                                                                SizesFlag.GRID_SIZE:  grid_size}
        return per_kernel_size_info
        
    def get_command_line_string(self, value):
        per_kernel_size_strings = []
        for kernel_number, size_info in value.iteritems():
            per_kernel_size_strings.append("kernel[%s]->tile[%s];kernel[%s]->block[%s];kernel[%s]->grid[%s]" \
                                           % (str(kernel_number) if kernel_number != SizesFlag.ALL_KERNELS_SENTINEL else "i",
                                              ','.join(str(val) for val in size_info[SizesFlag.TILE_SIZE]), 
                                              str(kernel_number) if kernel_number != SizesFlag.ALL_KERNELS_SENTINEL else "i",
                                              ','.join(str(val) for val in size_info[SizesFlag.BLOCK_SIZE]),
                                              str(kernel_number) if kernel_number != SizesFlag.ALL_KERNELS_SENTINEL else "i",
                                              ','.join(str(val) for val in size_info[SizesFlag.GRID_SIZE])))
        return '%s="{%s}"' % (self.name, ';'.join(per_kernel_size_strings))
    
    def not_sure_what_this_did(self, kernel, tile_size, block_size, grid_size):
        self.kernel = kernel
        self.possible_values = {}
        self.possible_values[SizesFlag.TILE_SIZE]  = Size(len(tile_size), config.Arguments.tile_size[0], config.Arguments.tile_size[1]+1)
        self.possible_values[SizesFlag.BLOCK_SIZE] = Size(len(block_size), config.Arguments.block_size[0], config.Arguments.block_size[1]+1) 
        self.possible_values[SizesFlag.GRID_SIZE]  = Size(len(grid_size), config.Arguments.grid_size[0], config.Arguments.grid_size[1]+1)
        self.original_tile_size  = tile_size
        self.original_block_size = block_size
        self.original_grid_size  = grid_size
        
    def get_original_value(self):
        return {SizesFlag.TILE_SIZE:  tuple(self.original_tile_size), 
                SizesFlag.BLOCK_SIZE: tuple(self.original_block_size), 
                SizesFlag.GRID_SIZE:  tuple(self.original_grid_size)}
        
    def permute(self, value):
        return {SizesFlag.TILE_SIZE:  self.possible_values[SizesFlag.TILE_SIZE].permute(value[SizesFlag.TILE_SIZE]), 
                SizesFlag.BLOCK_SIZE: self.possible_values[SizesFlag.BLOCK_SIZE].permute(value[SizesFlag.BLOCK_SIZE]),
                SizesFlag.GRID_SIZE:  self.possible_values[SizesFlag.GRID_SIZE].permute(value[SizesFlag.GRID_SIZE])}
    
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
    isl_flag_map[isl_context]                               = EnumerationFlag(isl_context, ['gbr', 'lexmin'])
    isl_flag_map[isl_gbr]                                   = EnumerationFlag(isl_gbr, ['never', 'once', 'always'])
    isl_flag_map[isl_closure]                               = EnumerationFlag(isl_closure, ['isl', 'box'])
    isl_flag_map[isl_gbr_only_first]                        = EnumerationFlag(isl_gbr_only_first)
    isl_flag_map[isl_bernstein_recurse]                     = EnumerationFlag(isl_bernstein_recurse, ['none', 'factors', 'intervals', 'full'])
    isl_flag_map[no_isl_bernstein_triangulate]              = EnumerationFlag(no_isl_bernstein_triangulate)
    isl_flag_map[no_isl_pip_symmetry]                       = EnumerationFlag(no_isl_pip_symmetry)
    isl_flag_map[isl_convex_hull]                           = EnumerationFlag(isl_convex_hull, ['wrap', 'fm'])
    isl_flag_map[no_isl_coalesce_bounded_wrapping]          = EnumerationFlag(no_isl_coalesce_bounded_wrapping)
    isl_flag_map[no_isl_schedule_parametric]                = EnumerationFlag(no_isl_schedule_parametric)
    isl_flag_map[no_isl_schedule_outer_coincidence]         = EnumerationFlag(no_isl_schedule_outer_coincidence)
    isl_flag_map[no_isl_schedule_maximize_band_depth]       = EnumerationFlag(no_isl_schedule_maximize_band_depth)
    isl_flag_map[no_isl_schedule_split_scaled]              = EnumerationFlag(no_isl_schedule_split_scaled)
    isl_flag_map[isl_schedule_algorithm]                    = EnumerationFlag(isl_schedule_algorithm, ['isl', 'feautrier'])
    isl_flag_map[no_isl_tile_scale_tile_loops]              = EnumerationFlag(no_isl_tile_scale_tile_loops)
    isl_flag_map[no_isl_tile_shift_point_loops]             = EnumerationFlag(no_isl_tile_shift_point_loops)
    isl_flag_map[no_isl_ast_build_atomic_upper_bound]       = EnumerationFlag(no_isl_ast_build_atomic_upper_bound)
    isl_flag_map[no_isl_ast_build_prefer_pdiv]              = EnumerationFlag(no_isl_ast_build_prefer_pdiv)
    isl_flag_map[no_isl_ast_build_exploit_nested_bounds]    = EnumerationFlag(no_isl_ast_build_exploit_nested_bounds)
    isl_flag_map[isl_ast_build_group_coscheduled]           = EnumerationFlag(isl_ast_build_group_coscheduled)
    isl_flag_map[isl_ast_build_separation_bounds]           = EnumerationFlag(isl_ast_build_separation_bounds, ['explicit', 'implicit'])
    isl_flag_map[no_isl_ast_build_scale_strides]            = EnumerationFlag(no_isl_ast_build_scale_strides)
    isl_flag_map[no_isl_ast_build_allow_else]               = EnumerationFlag(no_isl_ast_build_allow_else)
    isl_flag_map[no_isl_ast_build_allow_or]                 = EnumerationFlag(no_isl_ast_build_allow_or)
    
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
    flag_map[isl_schedule_fuse]                    = EnumerationFlag(isl_schedule_fuse, ['max', 'min'])
    flag_map[no_isl_schedule_separate_components]  = EnumerationFlag(no_isl_schedule_separate_components)
    flag_map[no_wrap]                              = EnumerationFlag(no_wrap)
    flag_map[no_scale_tile_loops]                  = EnumerationFlag(no_scale_tile_loops)
    flag_map[no_shared_memory]                     = EnumerationFlag(no_shared_memory)
    flag_map[no_private_memory]                    = EnumerationFlag(no_private_memory)
    flag_map[no_live_range_reordering]             = EnumerationFlag(no_live_range_reordering)
    flag_map[sizes]                                = SizesFlag()
    
    optimisation_flags = []
    
class CC:
    """All C compiler flags"""
    
    optimisation_flags = []
    
class CXX:
    """All C++ compiler flags"""
    
    optimisation_flags = []
    
class NVCC:
    """All CUDA compiler flags"""
    
    optimisation_flags = [EnumerationFlag('--ftz'),
                          EnumerationFlag('--prec-sqrt'),
                          EnumerationFlag('--prec-div'),
                          EnumerationFlag('--fmad'),
                          EnumerationFlag('--maxrregcount', [x for x in range(16,128+1) if x % 4 == 0])]
    
class LLVM:
    """All optimisation flags for different versions of LLVM"""
        
    optimisation_flags_20 = [EnumerationFlag('-adce'),
                             EnumerationFlag('-argpromotion'),
                             EnumerationFlag('-block-placement'),
                             EnumerationFlag('-break-crit-edges'),
                             EnumerationFlag('-cee'),
                             EnumerationFlag('-condprop'),
                             EnumerationFlag('-constmerge'),
                             EnumerationFlag('-constprop'),
                             EnumerationFlag('-dce'),
                             EnumerationFlag('-deadargelim'),
                             EnumerationFlag('-die'),
                             EnumerationFlag('-dse'),
                             EnumerationFlag('-gcse'),
                             EnumerationFlag('-globaldce'),
                             EnumerationFlag('-globalopt'),
                             EnumerationFlag('-indmemrem'),
                             EnumerationFlag('-indvars'),
                             EnumerationFlag('-inline'),
                             EnumerationFlag('-insert-block-profiling'),
                             EnumerationFlag('-insert-edge-profiling'),
                             EnumerationFlag('-insert-function-profiling'),
                             EnumerationFlag('-insert-null-profiling-rs'),
                             EnumerationFlag('-insert-rs-profiling-framework'),
                             EnumerationFlag('-instcombine'),
                             EnumerationFlag('-internalize'),
                             EnumerationFlag('-ipconstprop'),
                             EnumerationFlag('-ipsccp'),
                             EnumerationFlag('-lcssa'),
                             EnumerationFlag('-licm'),
                             EnumerationFlag('-loop-extract'),
                             EnumerationFlag('-loop-extract-single'),
                             EnumerationFlag('-loop-reduce'),
                             EnumerationFlag('-loop-unroll'),
                             EnumerationFlag('-loop-unswitch'),
                             EnumerationFlag('-loopsimplify'),
                             EnumerationFlag('-lower-packed'),
                             EnumerationFlag('-lowerallocs'),
                             EnumerationFlag('-lowergc'),
                             EnumerationFlag('-lowerinvoke'),
                             EnumerationFlag('-lowerselect'),
                             EnumerationFlag('-lowersetjmp'),
                             EnumerationFlag('-lowerswitch'),
                             EnumerationFlag('-mem2reg'),
                             EnumerationFlag('-mergereturn'),
                             EnumerationFlag('-predsimplify'),
                             EnumerationFlag('-prune-eh'),
                             EnumerationFlag('-raiseallocs'),
                             EnumerationFlag('-reassociate'),
                             EnumerationFlag('-reg2mem'),
                             EnumerationFlag('-scalarrepl'),
                             EnumerationFlag('-sccp'),
                             EnumerationFlag('-simplify-libcalls'),
                             EnumerationFlag('-simplifycfg'),
                             EnumerationFlag('-strip'),
                             EnumerationFlag('-tailcallelim'),
                             EnumerationFlag('-tailduplicate')]
    
    optimisation_flags_21 = optimisation_flags_20[:]
    
    optimisation_flags_22 = optimisation_flags_21[:]
    optimisation_flags_22.append(EnumerationFlag('-gvn'))
    optimisation_flags_22.append(EnumerationFlag('-gvnpre'))
    optimisation_flags_22.append(EnumerationFlag('-loop-index-split'))
    optimisation_flags_22.append(EnumerationFlag('-loop-rotate'))
    
    optimisation_flags_23 = optimisation_flags_22[:]
    optimisation_flags_23.append(EnumerationFlag('-jump-threading'))
    optimisation_flags_23.append(EnumerationFlag('-loop-deletion'))
    optimisation_flags_23.append(EnumerationFlag('-memcpyopt'))
    optimisation_flags_23.append(EnumerationFlag('-strip-dead-prototypes'))
    optimisation_flags_23.append(EnumerationFlag('-sretpromotion'))    
    
    optimisation_flags_24 = optimisation_flags_23[:]
    
    optimisation_flags_25 = optimisation_flags_23[:]
    
    optimisation_flags_26 = optimisation_flags_23[:]
    
    optimisation_flags_27 = optimisation_flags_23[:]
    optimisation_flags_27.remove(EnumerationFlag('-gcse'))
    optimisation_flags_27.remove(EnumerationFlag('-gvnpre'))
    optimisation_flags_27.remove(EnumerationFlag('-predsimplify'))
    optimisation_flags_27.remove(EnumerationFlag('-raiseallocs'))
    
    optimisation_flags_28 = optimisation_flags_27[:]
    optimisation_flags_28.append(EnumerationFlag('-abcd'))
    optimisation_flags_28.append(EnumerationFlag('-always-inline'))
    optimisation_flags_28.remove(EnumerationFlag('-condprop'))
    optimisation_flags_28.append(EnumerationFlag('-functionattrs'))
    optimisation_flags_28.remove(EnumerationFlag('-indmemrem'))
    optimisation_flags_28.remove(EnumerationFlag('-insert-block-profiling'))
    optimisation_flags_28.remove(EnumerationFlag('-insert-function-profiling')) 
    optimisation_flags_28.remove(EnumerationFlag('-insert-null-profiling-rs')) 
    optimisation_flags_28.remove(EnumerationFlag('-insert-rs-profiling-framework')) 
    optimisation_flags_28.append(EnumerationFlag('-insert-optimal-edge-profiling'))  
    optimisation_flags_28.append(EnumerationFlag('-mergefunc'))
    optimisation_flags_28.append(EnumerationFlag('-partial-inliner'))
    optimisation_flags_28.append(EnumerationFlag('-partialspecialization'))
    optimisation_flags_28.append(EnumerationFlag('-sink'))   
    optimisation_flags_28.append(EnumerationFlag('-simplify-libcalls-halfpowr')) 
    optimisation_flags_28.append(EnumerationFlag('-split-geps')) 
    optimisation_flags_28.append(EnumerationFlag('-ssi')) 
    optimisation_flags_28.append(EnumerationFlag('-ssi-everything'))
    optimisation_flags_28.append(EnumerationFlag('-strip-dead-debug-info'))
    optimisation_flags_28.append(EnumerationFlag('-strip-debug-declare'))
    optimisation_flags_28.append(EnumerationFlag('-strip-nondebug'))
    
    optimisation_flags_29 = optimisation_flags_28[:]
    optimisation_flags_29.remove(EnumerationFlag('-loopsimplify'))
    optimisation_flags_29.append(EnumerationFlag('-loop-simplify'))
    
    optimisation_flags_30 = [EnumerationFlag('-adce'),
                             EnumerationFlag('-always-inline'),
                             EnumerationFlag('-argpromotion'),
                             EnumerationFlag('-block-placement'),
                             EnumerationFlag('-break-crit-edges'),
                             EnumerationFlag('-codegenprepare'),
                             EnumerationFlag('-constmerge'),
                             EnumerationFlag('-constprop'),
                             EnumerationFlag('-dce'),
                             EnumerationFlag('-deadargelim'),
                             EnumerationFlag('-die'),
                             EnumerationFlag('-dse'),
                             EnumerationFlag('-functionattrs'),
                             EnumerationFlag('-globaldce'),
                             EnumerationFlag('-globalopt'),
                             EnumerationFlag('-gvn'),
                             EnumerationFlag('-indvars'),
                             EnumerationFlag('-inline'),
                             EnumerationFlag('-insert-edge-profiling'),
                             EnumerationFlag('-insert-optimal-edge-profiling'),
                             EnumerationFlag('-instcombine'),
                             EnumerationFlag('-internalize'),
                             EnumerationFlag('-ipconstprop'),
                             EnumerationFlag('-ipsccp'),
                             EnumerationFlag('-jump-threading'),
                             EnumerationFlag('-lcssa'),
                             EnumerationFlag('-licm'),
                             EnumerationFlag('-loop-deletion'),
                             EnumerationFlag('-loop-extract'),
                             EnumerationFlag('-loop-extract-single'),
                             EnumerationFlag('-loop-reduce'),
                             EnumerationFlag('-loop-rotate'),
                             EnumerationFlag('-loop-simplify'),
                             EnumerationFlag('-loop-unroll'),
                             EnumerationFlag('-loop-unswitch'),
                             EnumerationFlag('-loweratomic'),
                             EnumerationFlag('-lowerinvoke'),
                             EnumerationFlag('-lowerswitch'),
                             EnumerationFlag('-mem2reg'),
                             EnumerationFlag('-memcpyopt'),
                             EnumerationFlag('-mergefunc'),
                             EnumerationFlag('-mergereturn'),
                             EnumerationFlag('-partial-inliner'),
                             EnumerationFlag('-prune-eh'),
                             EnumerationFlag('-reassociate'),
                             EnumerationFlag('-reg2mem'),
                             EnumerationFlag('-scalarrepl'),
                             EnumerationFlag('-sccp'),
                             EnumerationFlag('-simplify-libcalls'),
                             EnumerationFlag('-simplifycfg'),
                             EnumerationFlag('-sink'),
                             EnumerationFlag('-sretpromotion'),
                             EnumerationFlag('-strip'),
                             EnumerationFlag('-strip-dead-debug-info'),
                             EnumerationFlag('-strip-dead-prototypes'),
                             EnumerationFlag('-strip-debug-declare'),
                             EnumerationFlag('-strip-nondebug'),
                             EnumerationFlag('-tailcallelim'),
                             EnumerationFlag('-tailduplicate')]
    
    optimisation_flags_31 = optimisation_flags_30[:]
    optimisation_flags_31.append(EnumerationFlag('-bb-vectorize'))
    
    optimisation_flags_32 = optimisation_flags_31[:]
    optimisation_flags_32.remove(EnumerationFlag('-tailduplicate'))
    
    optimisation_flags_33 = optimisation_flags_32[:]
    optimisation_flags_33.remove(EnumerationFlag('-sretpromotion'))
    
    optimisation_flags_34 = optimisation_flags_33[:]

class GNU:
    """All optimisation flags for different versions of gcc/g++"""
    
    optimisation_flags_441 = [#O1 turns on the following flags
                              EnumerationFlag('-fauto-inc-dec'),
                              EnumerationFlag('-fcprop-registers'),
                              EnumerationFlag('-fdce'),
                              EnumerationFlag('-fdefer-pop'),
                              EnumerationFlag('-fdelayed-branch'),
                              EnumerationFlag('-fdse'),
                              EnumerationFlag('-fguess-branch-probability'),
                              EnumerationFlag('-fif-conversion2'),
                              EnumerationFlag('-fif-conversion'),
                              EnumerationFlag('-finline-small-functions'),
                              EnumerationFlag('-fipa-pure-const'),
                              EnumerationFlag('-fipa-reference'),
                              EnumerationFlag('-fmerge-constants'),
                              EnumerationFlag('-fsplit-wide-types'),
                              EnumerationFlag('-ftree-builtin-call-dce'),
                              EnumerationFlag('-ftree-ccp'),
                              EnumerationFlag('-ftree-ch'),
                              EnumerationFlag('-ftree-copyrename'),
                              EnumerationFlag('-ftree-dce'),
                              EnumerationFlag('-ftree-dominator-opts'),
                              EnumerationFlag('-ftree-dse'),
                              EnumerationFlag('-ftree-fre'),
                              EnumerationFlag('-ftree-sra'),
                              EnumerationFlag('-ftree-ter'),
                              EnumerationFlag('-funit-at-a-time'),
                              EnumerationFlag('-fomit-frame-pointer'),
                              #02 turns on the following flags
                         EnumerationFlag('-fthread-jumps'),
                         EnumerationFlag('-falign-functions'),
                         EnumerationFlag('-falign-jumps'),
                         EnumerationFlag('-falign-loops'),
                         EnumerationFlag('-falign-labels'),
                         EnumerationFlag('-fcaller-saves'),
                         EnumerationFlag('-fcrossjumping'),
                         EnumerationFlag('-fcse-follow-jumps'),
                         EnumerationFlag('-fcse-skip-blocks'),
                         EnumerationFlag('-fdelete-null-pointer-checks'),
                         EnumerationFlag('-fexpensive-optimizations'),
                         EnumerationFlag('-fgcse'),
                         EnumerationFlag('-fgcse-lm'),
                         EnumerationFlag('-findirect-inlining'),
                         EnumerationFlag('-foptimize-sibling-calls'),
                         EnumerationFlag('-fpeephole2'),
                         EnumerationFlag('-fregmove'),
                         EnumerationFlag('-freorder-blocks'),
                         EnumerationFlag('-freorder-functions'),
                         EnumerationFlag('-frerun-cse-after-loop'),
                         EnumerationFlag('-fsched-interblock'),
                         EnumerationFlag('-fsched-spec'),
                         EnumerationFlag('-fschedule-insns'),
                         EnumerationFlag('-fschedule-insns2'),
                         EnumerationFlag('-fstrict-aliasing'),
                         EnumerationFlag('-fstrict-overflow'),
                         EnumerationFlag('-ftree-switch-conversion'),
                         EnumerationFlag('-ftree-pre'),
                         EnumerationFlag('-ftree-vrp'),
                         #03 turns on the following flags
                         EnumerationFlag('-finline-functions'), 
                         EnumerationFlag('-funswitch-loops'),
                         EnumerationFlag('-fpredictive-commoning'),
                         EnumerationFlag('-fgcse-after-reload'), 
                         EnumerationFlag('-ftree-vectorize')]
    
    optimisation_flags_442 = optimisation_flags_441[:]
    
    optimisation_flags_443 = optimisation_flags_441[:]
    
    optimisation_flags_444 = optimisation_flags_441[:]
    
    optimisation_flags_445 = optimisation_flags_441[:]
    optimisation_flags_445.append(EnumerationFlag('-fipa-cp-clone'))
    
    optimisation_flags_446 = optimisation_flags_445[:]
    
    optimisation_flags_447 = optimisation_flags_445[:]
    
    optimisation_flags_450 = [#01 turns on the following flags 
                         EnumerationFlag('-fauto-inc-dec'),
                         EnumerationFlag('-fcprop-registers'),
                         EnumerationFlag('-fdce'),
                         EnumerationFlag('-fdefer-pop'),
                         EnumerationFlag('-fdelayed-branch'),
                         EnumerationFlag('-fdse'),
                         EnumerationFlag('-fguess-branch-probability'),
                         EnumerationFlag('-fif-conversion2'),
                         EnumerationFlag('-fif-conversion'),
                         EnumerationFlag('-fipa-pure-const'),
                         EnumerationFlag('-fipa-reference'),
                         EnumerationFlag('-fmerge-constants'),
                         EnumerationFlag('-fsplit-wide-types'),
                         EnumerationFlag('-ftree-builtin-call-dce'),
                         EnumerationFlag('-ftree-ccp'),
                         EnumerationFlag('-ftree-ch'),
                         EnumerationFlag('-ftree-copyrename'),
                         EnumerationFlag('-ftree-dce'),
                         EnumerationFlag('-ftree-dominator-opts'),
                         EnumerationFlag('-ftree-dse'),
                         EnumerationFlag('-ftree-forwprop'),
                         EnumerationFlag('-ftree-fre'),
                         EnumerationFlag('-ftree-phiprop'),
                         EnumerationFlag('-ftree-sra'),
                         EnumerationFlag('-ftree-pta'),
                         EnumerationFlag('-ftree-ter'),
                         EnumerationFlag('-funit-at-a-time'),
                         EnumerationFlag('-fomit-frame-pointer'),
                         #02 turns on the following flags
                         EnumerationFlag('-fthread-jumps'),
                         EnumerationFlag('-falign-functions'),
                         EnumerationFlag('-falign-jumps'),
                         EnumerationFlag('-falign-loops'),
                         EnumerationFlag('-falign-labels'),
                         EnumerationFlag('-fcaller-saves'),
                         EnumerationFlag('-fcrossjumping'),
                         EnumerationFlag('-fcse-follow-jumps'),
                         EnumerationFlag('-fcse-skip-blocks'),
                         EnumerationFlag('-fdelete-null-pointer-checks'),
                         EnumerationFlag('-fexpensive-optimizations'),
                         EnumerationFlag('-fgcse'),
                         EnumerationFlag('-fgcse-lm'),
                         EnumerationFlag('-finline-small-functions'),
                         EnumerationFlag('-findirect-inlining'),
                         EnumerationFlag('-fipa-sra'),
                         EnumerationFlag('-foptimize-sibling-calls'),
                         EnumerationFlag('-fpeephole2'),
                         EnumerationFlag('-fregmove'),
                         EnumerationFlag('-freorder-blocks'),
                         EnumerationFlag('-freorder-functions'),
                         EnumerationFlag('-frerun-cse-after-loop'),
                         EnumerationFlag('-fsched-interblock'),
                         EnumerationFlag('-fsched-spec'),
                         EnumerationFlag('-fschedule-insns'),
                         EnumerationFlag('-fschedule-insns2'),
                         EnumerationFlag('-fstrict-aliasing'),
                         EnumerationFlag('-fstrict-overflow'),
                         EnumerationFlag('-ftree-switch-conversion'),
                         EnumerationFlag('-ftree-pre'),
                         EnumerationFlag('-ftree-vrp'),
                         #03 turns on the following flags 
                         EnumerationFlag('-finline-functions'), 
                         EnumerationFlag('-funswitch-loops'),
                         EnumerationFlag('-fpredictive-commoning'),
                         EnumerationFlag('-fgcse-after-reload'), 
                         EnumerationFlag('-ftree-vectorize')]
    
    optimisation_flags_451 = optimisation_flags_450[:]
    
    optimisation_flags_452 = optimisation_flags_451[:]
    optimisation_flags_452.append(EnumerationFlag('-fipa-cp-clone'))
    
    optimisation_flags_453 = optimisation_flags_452[:]
    
    optimisation_flags_454 = optimisation_flags_452[:]
    
    optimisation_flags_460 = [#01 turns on the following flags
                         EnumerationFlag('-fauto-inc-dec'),
                         EnumerationFlag('-fcompare-elim'),
                         EnumerationFlag('-fcprop-registers'),
                         EnumerationFlag('-fdce'),
                         EnumerationFlag('-fdefer-pop'),
                         EnumerationFlag('-fdelayed-branch'),
                         EnumerationFlag('-fdse'),
                         EnumerationFlag('-fguess-branch-probability'),
                         EnumerationFlag('-fif-conversion2'),
                         EnumerationFlag('-fif-conversion'),
                         EnumerationFlag('-fipa-pure-const'),
                         EnumerationFlag('-fipa-profile'),
                         EnumerationFlag('-fipa-reference'),
                         EnumerationFlag('-fmerge-constants'),
                         EnumerationFlag('-fsplit-wide-types'),
                         EnumerationFlag('-ftree-bit-ccp'),
                         EnumerationFlag('-ftree-builtin-call-dce'),
                         EnumerationFlag('-ftree-ccp'),
                         EnumerationFlag('-ftree-ch'),
                         EnumerationFlag('-ftree-copyrename'),
                         EnumerationFlag('-ftree-dce'),
                         EnumerationFlag('-ftree-dominator-opts'),
                         EnumerationFlag('-ftree-dse'),
                         EnumerationFlag('-ftree-forwprop'),
                         EnumerationFlag('-ftree-fre'),
                         EnumerationFlag('-ftree-phiprop'),
                         EnumerationFlag('-ftree-sra'),
                         EnumerationFlag('-ftree-pta'),
                         EnumerationFlag('-ftree-ter'),
                         EnumerationFlag('-funit-at-a-time'),
                         EnumerationFlag('-fomit-frame-pointer'),
                         #02 turns on the following flags 
                         EnumerationFlag('-fthread-jumps'),
                         EnumerationFlag('-falign-functions'),
                         EnumerationFlag('-falign-jumps'),
                         EnumerationFlag('-falign-loops'),
                         EnumerationFlag('-falign-labels'),
                         EnumerationFlag('-fcaller-saves'),
                         EnumerationFlag('-fcrossjumping'),
                         EnumerationFlag('-fcse-follow-jumps'),
                         EnumerationFlag('-fcse-skip-blocks'),
                         EnumerationFlag('-fdelete-null-pointer-checks'),
                         EnumerationFlag('-fdevirtualize'),
                         EnumerationFlag('-fexpensive-optimizations'),
                         EnumerationFlag('-fgcse'),
                         EnumerationFlag('-fgcse-lm'),
                         EnumerationFlag('-finline-small-functions'),
                         EnumerationFlag('-findirect-inlining'),
                         EnumerationFlag('-fipa-sra'),
                         EnumerationFlag('-foptimize-sibling-calls'),
                         EnumerationFlag('-fpartial-inlining'),
                         EnumerationFlag('-fpeephole2'),
                         EnumerationFlag('-fregmove'),
                         EnumerationFlag('-freorder-blocks'),
                         EnumerationFlag('-freorder-functions'),
                         EnumerationFlag('-frerun-cse-after-loop'),
                         EnumerationFlag('-fsched-interblock'),
                         EnumerationFlag('-fsched-spec'),
                         EnumerationFlag('-fschedule-insns'),
                         EnumerationFlag('-fschedule-insns2'),
                         EnumerationFlag('-fstrict-aliasing'),
                         EnumerationFlag('-fstrict-overflow'),
                         EnumerationFlag('-ftree-switch-conversion'),
                         EnumerationFlag('-ftree-pre'),
                         EnumerationFlag('-ftree-vrp'),
                         #03 turns on the following flags
                         EnumerationFlag('-finline-functions'), 
                         EnumerationFlag('-funswitch-loops'),
                         EnumerationFlag('-fpredictive-commoning'),
                         EnumerationFlag('-fgcse-after-reload'), 
                         EnumerationFlag('-ftree-vectorize'),
                         EnumerationFlag('-fipa-cp-clone')]
    
    optimisation_flags_461 = optimisation_flags_460[:]
    
    optimisation_flags_462 = optimisation_flags_460[:]
    
    optimisation_flags_463 = optimisation_flags_460[:]
    
    optimisation_flags_464 = optimisation_flags_460[:]
    
    optimisation_flags_470 = [#01 turns on the following flags
                         EnumerationFlag('-fauto-inc-dec'),
                         EnumerationFlag('-fcompare-elim'),
                         EnumerationFlag('-fcprop-registers'),
                         EnumerationFlag('-fdce'),
                         EnumerationFlag('-fdefer-pop'),
                         EnumerationFlag('-fdelayed-branch'),
                         EnumerationFlag('-fdse'),
                         EnumerationFlag('-fguess-branch-probability'),
                         EnumerationFlag('-fif-conversion2'),
                         EnumerationFlag('-fif-conversion'),
                         EnumerationFlag('-fipa-pure-const'),
                         EnumerationFlag('-fipa-profile'),
                         EnumerationFlag('-fipa-reference'),
                         EnumerationFlag('-fmerge-constants'),
                         EnumerationFlag('-fsplit-wide-types'),
                         EnumerationFlag('-ftree-bit-ccp'),
                         EnumerationFlag('-ftree-builtin-call-dce'),
                         EnumerationFlag('-ftree-ccp'),
                         EnumerationFlag('-ftree-ch'),
                         EnumerationFlag('-ftree-copyrename'),
                         EnumerationFlag('-ftree-dce'),
                         EnumerationFlag('-ftree-dominator-opts'),
                         EnumerationFlag('-ftree-dse'),
                         EnumerationFlag('-ftree-forwprop'),
                         EnumerationFlag('-ftree-fre'),
                         EnumerationFlag('-ftree-phiprop'),
                         EnumerationFlag('-ftree-sra'),
                         EnumerationFlag('-ftree-pta'),
                         EnumerationFlag('-ftree-ter'),
                         EnumerationFlag('-funit-at-a-time'),
                         EnumerationFlag('-fomit-frame-pointer'),
                         #02 turns on the following flags 
                         EnumerationFlag('-fthread-jumps'),
                         EnumerationFlag('-falign-functions'),
                         EnumerationFlag('-falign-jumps'),
                         EnumerationFlag('-falign-loops'),
                         EnumerationFlag('-falign-labels'),
                         EnumerationFlag('-fcaller-saves'),
                         EnumerationFlag('-fcrossjumping'),
                         EnumerationFlag('-fcse-follow-jumps'),
                         EnumerationFlag('-fcse-skip-blocks'),
                         EnumerationFlag('-fdelete-null-pointer-checks'),
                         EnumerationFlag('-fdevirtualize'),
                         EnumerationFlag('-fexpensive-optimizations'),
                         EnumerationFlag('-fgcse'),
                         EnumerationFlag('-fgcse-lm'),
                         EnumerationFlag('-finline-small-functions'),
                         EnumerationFlag('-findirect-inlining'),
                         EnumerationFlag('-fipa-sra'),
                         EnumerationFlag('-foptimize-sibling-calls'),
                         EnumerationFlag('-fpartial-inlining'),
                         EnumerationFlag('-fpeephole2'),
                         EnumerationFlag('-fregmove'),
                         EnumerationFlag('-freorder-blocks'),
                         EnumerationFlag('-freorder-functions'),
                         EnumerationFlag('-frerun-cse-after-loop'),
                         EnumerationFlag('-fsched-interblock'),
                         EnumerationFlag('-fsched-spec'),
                         EnumerationFlag('-fschedule-insns'),
                         EnumerationFlag('-fschedule-insns2'),
                         EnumerationFlag('-fstrict-aliasing'),
                         EnumerationFlag('-fstrict-overflow'),
                         EnumerationFlag('-ftree-switch-conversion'),
                         EnumerationFlag('-ftree-tail-merge'),
                         EnumerationFlag('-ftree-pre'),
                         EnumerationFlag('-ftree-vrp'),
                         #03 turns on the following flags 
                         EnumerationFlag('-finline-functions'), 
                         EnumerationFlag('-funswitch-loops'),
                         EnumerationFlag('-fpredictive-commoning'),
                         EnumerationFlag('-fgcse-after-reload'), 
                         EnumerationFlag('-ftree-vectorize'),
                         EnumerationFlag('-fipa-cp-clone')]
    
    optimisation_flags_471 = optimisation_flags_470[:]
    
    optimisation_flags_472 = optimisation_flags_470[:]
    
    optimisation_flags_473 = optimisation_flags_470[:]
    
    optimisation_flags_480 = [#01 turns on the following flags 
                         EnumerationFlag('-fauto-inc-dec'),
                         EnumerationFlag('-fcompare-elim'),
                         EnumerationFlag('-fcprop-registers'),
                         EnumerationFlag('-fdce'),
                         EnumerationFlag('-fdefer-pop'),
                         EnumerationFlag('-fdelayed-branch'),
                         EnumerationFlag('-fdse'),
                         EnumerationFlag('-fguess-branch-probability'),
                         EnumerationFlag('-fif-conversion2'),
                         EnumerationFlag('-fif-conversion'),
                         EnumerationFlag('-fipa-pure-const'),
                         EnumerationFlag('-fipa-profile'),
                         EnumerationFlag('-fipa-reference'),
                         EnumerationFlag('-fmerge-constants'),
                         EnumerationFlag('-fsplit-wide-types'),
                         EnumerationFlag('-ftree-bit-ccp'),
                         EnumerationFlag('-ftree-builtin-call-dce'),
                         EnumerationFlag('-ftree-ccp'),
                         EnumerationFlag('-ftree-ch'),
                         EnumerationFlag('-ftree-copyrename'),
                         EnumerationFlag('-ftree-dce'),
                         EnumerationFlag('-ftree-dominator-opts'),
                         EnumerationFlag('-ftree-dse'),
                         EnumerationFlag('-ftree-forwprop'),
                         EnumerationFlag('-ftree-fre'),
                         EnumerationFlag('-ftree-phiprop'),
                         EnumerationFlag('-ftree-slsr'),
                         EnumerationFlag('-ftree-sra'),
                         EnumerationFlag('-ftree-pta'),
                         EnumerationFlag('-ftree-ter'),
                         EnumerationFlag('-funit-at-a-time'),
                         EnumerationFlag('-fomit-frame-pointer'),
                         #02 turns on the following flags
                         EnumerationFlag('-fthread-jumps'),
                         EnumerationFlag('-falign-functions'),
                         EnumerationFlag('-falign-jumps'),
                         EnumerationFlag('-falign-loops'),
                         EnumerationFlag('-falign-labels'),
                         EnumerationFlag('-fcaller-saves'),
                         EnumerationFlag('-fcrossjumping'),
                         EnumerationFlag('-fcse-follow-jumps'),
                         EnumerationFlag('-fcse-skip-blocks'),
                         EnumerationFlag('-fdelete-null-pointer-checks'),
                         EnumerationFlag('-fdevirtualize'),
                         EnumerationFlag('-fexpensive-optimizations'),
                         EnumerationFlag('-fgcse'),
                         EnumerationFlag('-fgcse-lm'),
                         EnumerationFlag('-finline-small-functions'),
                         EnumerationFlag('-findirect-inlining'),
                         EnumerationFlag('-fipa-sra'),
                         EnumerationFlag('-foptimize-sibling-calls'),
                         EnumerationFlag('-fpartial-inlining'),
                         EnumerationFlag('-fpeephole2'),
                         EnumerationFlag('-fregmove'),
                         EnumerationFlag('-freorder-blocks'),
                         EnumerationFlag('-freorder-functions'),
                         EnumerationFlag('-frerun-cse-after-loop'),
                         EnumerationFlag('-fsched-interblock'),
                         EnumerationFlag('-fsched-spec'),
                         EnumerationFlag('-fschedule-insns'),
                         EnumerationFlag('-fschedule-insns2'),
                         EnumerationFlag('-fstrict-aliasing'),
                         EnumerationFlag('-fstrict-overflow'),
                         EnumerationFlag('-ftree-switch-conversion'),
                         EnumerationFlag('-ftree-tail-merge'),
                         EnumerationFlag('-ftree-pre'),
                         EnumerationFlag('-ftree-vrp'),
                         #03 turns on the following flags
                         EnumerationFlag('-finline-functions'), 
                         EnumerationFlag('-funswitch-loops'),
                         EnumerationFlag('-fpredictive-commoning'),
                         EnumerationFlag('-fgcse-after-reload'), 
                         EnumerationFlag('-ftree-vectorize'),
                         EnumerationFlag('-fvect-cost-model'),
                         EnumerationFlag('-ftree-partial-pre'),
                         EnumerationFlag('-fipa-cp-clone')]
    
    optimisation_flags_481 = optimisation_flags_480[:]
    
    optimisation_flags_482 = optimisation_flags_480[:]
    
