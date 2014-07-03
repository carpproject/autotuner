import config
import enums
import debug
import internal_exceptions
import os
import abc

class BaseOption:
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
    def check(self):
        pass

class Option(BaseOption):
    """An option in the configuration file"""
    
    def __init__(self, name, help_message):
        self.name = name
        self.help = help_message
        
    def __hash__(self):
        return self.name.__hash__()
    
    def __eq__(self, other):
        return self.name == other.name
    
class TargetOption(Option):
    def check(self):
        if not hasattr(config.Arguments, self.name):
            raise internal_exceptions.UnsetOptionException("You must specify a target in the configuration file via '%s'" % self.name)
        all_targets = [enums.Targets.cuda, enums.Targets.opencl]
        the_target  = getattr(config.Arguments, self.name)
        if the_target not in all_targets:
            raise internal_exceptions.InvalidOptionException("The target must be one of {%s}. You chose '%s'" % (','.join(all_targets), the_target))
        
class PPCGOption(Option):
    def check(self):
        if not hasattr(config.Arguments, self.name):
            raise internal_exceptions.UnsetOptionException("You must specify how to launch PPCG via '%s'" % self.name)
        
class BuildOption(Option):
    def check(self):
        if not hasattr(config.Arguments, self.name):
            raise internal_exceptions.UnsetOptionException("You must specify how to build the application via '%s'" % self.name)
        
class RunOption(Option):
    def check(self):
        if not hasattr(config.Arguments, self.name):
            raise internal_exceptions.UnsetOptionException("You must specify how to run the application via '%s'" % self.name)

class Options:
    """Valid options in the configuration file""" 
    
    target = TargetOption("target", "the platform to generate code for. Choices: {%s, %s}" % (enums.Targets.cuda, enums.Targets.opencl))
    ppcg   = PPCGOption("ppcg", "how to invoke PPCG")
    build  = BuildOption("build", "how to build the application")
    run    = RunOption("run", "how to run the application")
    
    all = [target,
           ppcg,
           build,
           run]

def find_executable(executable):
    for path in os.environ["PATH"].split(os.pathsep):
        for root, dirs, files in os.walk(path):
            for aFile in files:
                if aFile == executable:
                    return os.path.abspath(os.path.join(root, aFile))
    return None    

def check_file(filename):
    filename = os.path.expanduser(filename)
    assert os.path.exists(filename), "The file '%s' does not exist" % filename
    assert os.path.isfile(filename), "The file '%s' is not a file" % filename
    return os.path.abspath(filename)

def do_parsing(filename):
    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                lexemes = line.split(":=")
                assert len(lexemes) == 2
                lhs = lexemes[0].strip().lower()
                rhs = lexemes[1].strip()
                if lhs not in [option.name for option in Options.all]:
                    raise internal_exceptions.InvalidOptionException("Unknown auto-tuning configuration option '%s'" % lhs)
                else:
                    if lhs == Options.target.name:
                        the_target = rhs.lower()
                        setattr(config.Arguments, Options.target.name, the_target)
                    
                    elif lhs == Options.ppcg.name:
                        setattr(config.Arguments, Options.ppcg.name, rhs)
                        
                    elif lhs == Options.build.name:
                        setattr(config.Arguments, Options.build.name, rhs)
                        
                    elif lhs == Options.run.name:
                        setattr(config.Arguments, Options.run.name, rhs)

def parse_file(filename):
    filename = check_file(filename)
    try:
        # Grab the configuration
        do_parsing(filename)
        # Check it
        for opt in Options.all:
            opt.check()
    except Exception as e: 
        debug.exit_message(e)
                