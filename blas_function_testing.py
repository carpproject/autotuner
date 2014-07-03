from __future__ import print_function

import config
import re
import os
import shutil
import collections
import copy
import sys
import debug
import internal_exceptions
import subprocess
import timeit
import pycparser
from pycparser import c_ast
from pycparser import c_generator
from numpy import random 

def run_compiler(the_cmd):  
    debug.verbose_message("Running '%s'" % the_cmd, __name__)
    start = timeit.default_timer()
    proc  = subprocess.Popen(the_cmd, shell=True, stderr=subprocess.PIPE)    
    end   = timeit.default_timer() 
    config.time_VOBLA += end - start
    if proc.wait():
        raise internal_exceptions.FailedCompilationException("FAILED: '%s'" % the_cmd) 

def compile_test_case(test_file, host_file):
    ocl_file          = config.Arguments.ppcg_home + os.sep + "ocl_utilities.c"
    test_file_obj     = "%s.o" % os.path.splitext(test_file)[0]
    host_file_obj     = "%s.o" % os.path.splitext(host_file)[0]
    ocl_utilities_obj = "%s.o" % os.path.splitext(ocl_file)[0]
    binary            = "%s" % os.path.splitext(test_file)[0]
    
    test_file_cmd = '%s -O3 -std=c99 -I%s -include "pencil.h" -c %s -o %s' % (config.Arguments.cc,
                                                                              config.Arguments.pencil_home + os.sep + "etc",
                                                                              test_file,
                                                                              test_file_obj)
    
    host_file_cmd = '%s -O3 -std=c99 -I%s -include "CL/opencl.h" -include "pencil.h" -c %s -o %s' % (config.Arguments.cc,
                                                                                                     config.Arguments.pencil_home + os.sep + "etc",
                                                                                                     host_file,
                                                                                                     host_file_obj)
    
    ocl_file_cmd = '%s -O3 -std=c99 -c %s -o %s' % (config.Arguments.cc,
                                                    ocl_file,
                                                    ocl_utilities_obj)
    
    binary_cmd = '%s %s %s %s -o %s -lOpenCL' % (config.Arguments.cc,
                                                 ocl_utilities_obj,
                                                 test_file_obj,
                                                 host_file_obj,
                                                 binary)
    
    run_compiler(test_file_cmd)
    run_compiler(host_file_cmd)
    run_compiler(ocl_file_cmd)
    run_compiler(binary_cmd)
    return binary

def write_to_file(ast_new_file, ppcg_input_file):
    generator  = c_generator.CGenerator()
    old_stdout = sys.stdout
    test_file  = "%s.test.c" % config.Arguments.tuning_function
    f          = open(test_file, 'w')
    try:
        sys.stdout = f
        # Include the standard library and the time headers for random number generation
        print('#include "stdlib.h"')
        print('#include "time.h"')
        print("")
        # Generate the code
        print(generator.visit(ast_new_file))
    finally:
        f.close()
        sys.stdout = old_stdout
    return os.path.abspath(test_file)

def create_main(pencil_info):
    debug.verbose_message("Create AST for function 'main'", __name__)
    
    # The statements in "main"
    main_stmts = []
    
    # Initialise the pseudo-random number generator
    ast_time_param = c_ast.Constant("int", "0") 
    ast_time_call  = c_ast.FuncCall(c_ast.ID("time"), c_ast.ExprList([ast_time_param]))
    ast_srand_call = c_ast.FuncCall(c_ast.ID("srand"), c_ast.ExprList([ast_time_call]));
    main_stmts.append(ast_srand_call);
    
    # Create local variable declarations matching those in the
    # formal parameter list of each function.
    # Each scalar is initialised using the value selected
    for function_name in pencil_info.functions.keys():
        for formal_param in pencil_info.get_formal_params(function_name):
            ast_local_decl = copy.deepcopy(formal_param)
            if isinstance(formal_param.type, c_ast.TypeDecl):
                if isinstance(formal_param.type.type, c_ast.IdentifierType):
                    ast_local_decl.init = c_ast.Constant(ast_local_decl.type.type.names[0], str(formal_param.value))     
            main_stmts.append(ast_local_decl)
            
    # Initialise array variables using a loop nest of the appropriate depth
    for function_name in pencil_info.functions.keys():
        for formal_param in pencil_info.get_formal_params(function_name):
            if isinstance(formal_param.type, c_ast.ArrayDecl):
                # The name of the loop indices to create
                loop_indices = ["test_%d" % dim for dim in range(0,len(formal_param.dimensions))]
                # The innermost loop index is the last one in the list
                inner_loop_index = len(formal_param.dimensions) - 1
                # Create the statement that assigns into an array element
                for i in range(0, len(formal_param.dimensions)):
                    if i == 0:
                        ast_array_reference = c_ast.ArrayRef(c_ast.ID(formal_param.name), c_ast.ID(loop_indices[i]))
                    else:
                        ast_array_reference = c_ast.ArrayRef(ast_array_reference, c_ast.ID(loop_indices[i]))
                # Create the loop nest
                for i in reversed(range(0, len(formal_param.dimensions))):
                    ast_loop_header_step = c_ast.UnaryOp("++", 
                                                         c_ast.ID(loop_indices[i]))
                    ast_loop_header_cond = c_ast.BinaryOp("<", 
                                                          c_ast.ID(loop_indices[i]), 
                                                          c_ast.ID(formal_param.dimensions[i]))
                    ast_loop_header_decl = c_ast.Decl(loop_indices[i], 
                                                      [], 
                                                      [], 
                                                      [], 
                                                      c_ast.TypeDecl(loop_indices[i], [], c_ast.IdentifierType(["int"])),
                                                      c_ast.Constant("int", "0"), 
                                                      None)
                    ast_loop_header_init = c_ast.DeclList([ast_loop_header_decl])
                    if i == inner_loop_index:
                        ast_rand_call = c_ast.FuncCall(c_ast.ID("rand"), c_ast.ExprList([]))                        
                        if len(formal_param.base_type) == 1:
                            ast_cast_type      = c_ast.TypeDecl(None, None, c_ast.IdentifierType([formal_param.base_type[0]]))
                            ast_cast_rand_call = c_ast.Cast(c_ast.Typename(None, ast_cast_type), ast_rand_call)
                            ast_loop_body      = c_ast.Assignment("=", ast_array_reference, ast_cast_rand_call)
                        else:
                            loop_body_stmts = []
                            struct_field_initialisers = []
                            for j in range(0, len(formal_param.base_type)):
                                ast_cast_type      = c_ast.TypeDecl(None, None, c_ast.IdentifierType([formal_param.base_type[j]]))
                                ast_cast_rand_call = c_ast.Cast(c_ast.Typename(None, ast_cast_type), ast_rand_call)
                                struct_field_initialisers.append(ast_cast_rand_call)
                            ast_struct_initialiser = c_ast.InitList(struct_field_initialisers)
                            ast_struct_decl = c_ast.Decl("rand_value", 
                                                         [],
                                                         [],
                                                         [],
                                                         c_ast.TypeDecl("rand_value", [], c_ast.Struct(formal_param.struct_name, None)),
                                                         ast_struct_initialiser,
                                                         None)
                            loop_body_stmts.append(ast_struct_decl)
                            
                            ast_array_assignment = c_ast.Assignment("=", ast_array_reference, c_ast.ID("rand_value"))
                            loop_body_stmts.append(ast_array_assignment)
                            ast_loop_body = c_ast.Compound(loop_body_stmts)
                        ast_loop = c_ast.For(ast_loop_header_init, 
                                             ast_loop_header_cond, 
                                             ast_loop_header_step, 
                                             ast_loop_body)
                    else:
                        ast_loop = c_ast.For(ast_loop_header_init, 
                                             ast_loop_header_cond, 
                                             ast_loop_header_step, 
                                             ast_loop)
                main_stmts.append(ast_loop)
        
    # Create function calls into each PENCIL function
    for function_name in pencil_info.functions.keys():
        expr_list = []
        for formal_param in pencil_info.get_formal_params(function_name):
            the_type = formal_param.type
            # Whittle down through array declarations to get the identifier
            while isinstance(the_type, c_ast.ArrayDecl):
                the_type = the_type.type
            expr_list.append(c_ast.ID(the_type.declname))
        ast_func_call = c_ast.FuncCall(c_ast.ID(function_name), c_ast.ExprList(expr_list))
        main_stmts.append(ast_func_call)
    
    # The return statement
    ast_return = c_ast.Return(c_ast.Constant("int", "0"))
    main_stmts.append(ast_return)
    
    # The function body for "main"
    ast_type_decl = c_ast.TypeDecl("main", 
                                   [], 
                                   c_ast.IdentifierType(["int"]))
    ast_func_decl = c_ast.FuncDecl(c_ast.ParamList([]), 
                                   ast_type_decl)
    ast_decl      = c_ast.Decl(ast_type_decl.declname, 
                               [], 
                               [], 
                               [], 
                               ast_func_decl, 
                               None, 
                               None)
    ast_main_func = c_ast.FuncDef(ast_decl, 
                                  None, 
                                  c_ast.Compound(main_stmts))
    return ast_main_func  

def copy_ast_declarations(pencil_info, struct_info):
    decls = []  
    for struct in struct_info.structs:
        decls.append(copy.deepcopy(struct))
    for function_name in pencil_info.functions.keys():
        # Even though we have a handle on the function declarations, quite 
        # annoyingly pycparser wants those AST nodes to be wrapped by 
        # c_ast.Decl nodes. So we just do it and everyone is happy.
        ast_func_decl = copy.deepcopy(pencil_info.functions[function_name])
        ast_decl      = c_ast.Decl(function_name, 
                                   [], [], [],
                                   ast_func_decl, 
                                   None, None)
        decls.append(ast_decl)
    ast_new_file = c_ast.FileAST(decls)
    return ast_new_file
     
def decorate_formal_params(node, struct_info):
    # We decorate the AST formal parameter node with a new attribute such that:
    # a) If the type is a scalar, the attribute is 'value', and it is a random 
    #    number.
    # b) If the type is an array, the attribute is 'dimensions', and it is a tuple 
    #    where the i_th value in the tuple corresponds to the variable or constant
    #    size of the i_th dimension in the array.
    if isinstance(node.type, c_ast.TypeDecl):
        if isinstance(node.type.type, c_ast.IdentifierType):
            # Scalar type
            assert len(node.type.type.names) == 1
            (base_type,) = node.type.type.names
            if base_type == "int":
                node.value = random.randint(2,17)
            elif base_type == "float":
                node.value = random.uniform(1,10)
            elif base_type == "double":
                node.value = random.uniform(1,10)
            else:
                assert False, "Unknown base type %s" % base_type
        elif isinstance(node.type.type, c_ast.Struct):
            node.base_type = struct_info.flattened_types[node.type.type.name]
    else:
        assert isinstance(node.type, c_ast.ArrayDecl)
        node.dimensions = ()
        the_type = node.type
        while isinstance(the_type, c_ast.ArrayDecl):
            node.dimensions += (the_type.dim.name,)
            the_type = the_type.type
        node.base_type = None
        node.struct_name = None
        if isinstance(the_type.type, c_ast.IdentifierType):
            node.base_type = [the_type.type.names[0]]  
        else:
            node.base_type = struct_info.flattened_types[the_type.type.name]
            node.struct_name = the_type.type.name

class StructDefintionVisitor(c_ast.NodeVisitor):
    def __init__(self):
        self.structs         = []
        self.flattened_types = collections.OrderedDict()
        
    def expand_struct_fields(self, node):
        the_types = []
        if isinstance(node, c_ast.Struct):
            if node.decls:
                # If the stuct AST node has 'decls' then it represents a 
                # struct definition
                for decl in node.decls:
                    if isinstance(decl.type.type, c_ast.IdentifierType):
                        # Bottomed out
                        the_types.extend(decl.type.type.names)
                    else:
                        # Recursive call due to inner struct reference
                        the_types.extend(self.expand_struct_fields(decl.type.type))
            else:
                # If not then it is a reference to a previously-defined
                # struct
                the_types.extend(self.flattened_types[node.name])
        return the_types
    
    def visit_Decl(self, node):
        if isinstance(node.type, c_ast.Struct):            
            self.structs.append(node)
            struct_node = node.type
            self.flattened_types[struct_node.name] = self.expand_struct_fields(struct_node)            

class FuncDeclVisitor(c_ast.NodeVisitor):
    regex_pencil_prefix = re.compile(r'pencil[_a-zA-Z0-9]+')
    
    def __init__(self):
        self.functions = collections.OrderedDict()
        
    def get_formal_params(self, function_name):
        node = self.functions[function_name]
        return [child[1] for child in node.args.children()]
    
    def visit_FuncDecl(self, node):
        function_name = node.type.declname
        if FuncDeclVisitor.regex_pencil_prefix.match(function_name):
            self.functions[function_name] = node
        
def remove_pencil_qualifiers_from_file(filename):
    filename2    = filename + ".temp"
    regex_pencil = re.compile(r'(static|restrict|const)')
    f1 = open(filename, 'r') 
    f2 = open(filename2, 'w')
    try:
        for line1 in f1:
            line2 = regex_pencil.sub("", line1)
            f2.write(line2)
    finally: 
        f1.close()
        f2.close()
        shutil.move(filename2, filename)
    
def create_test_case(ppcg_input_file, ppcg_output_files):   
    assert len(ppcg_output_files) == 1, "Currently support OpenCL only for VOBLA"     
    # Remove PENCIL qualifiers from C code otherwise it will not parse
    remove_pencil_qualifiers_from_file(ppcg_input_file)                      
    # Pre-process and parse the file               
    ast = pycparser.parse_file(ppcg_input_file, use_cpp=True)
    gen = c_generator.CGenerator()
    gen.visit(ast)
    # Find PENCIL function declarations
    pencil_info = FuncDeclVisitor()
    pencil_info.visit(ast)
    # Find struct definitions
    struct_info = StructDefintionVisitor()
    struct_info.visit(ast)
    # We need the struct and function prototypes to dump in the test file
    ast_new_file = copy_ast_declarations(pencil_info, struct_info)
    # Analyse the types of parameters in each PENCIL function
    for function_name in pencil_info.functions.keys():
        for formal_param in pencil_info.get_formal_params(function_name):            
            decorate_formal_params(formal_param, struct_info)
    # Create a main function that will call the PENCIL functions
    main_func = create_main(pencil_info)
    ast_new_file.ext.append(main_func)
    # Write the program to a file
    test_file = write_to_file(ast_new_file, ppcg_input_file)
    # Compile the code
    binary = compile_test_case(test_file, ppcg_output_files[0])
    return binary
    