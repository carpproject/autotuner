
class UnsetOptionException(Exception):
    def __init__(self, message):
        Exception.__init__(self, "configuration file error: unset option: %s"  % message)

class InvalidOptionException(Exception):
    def __init__(self, message):
        Exception.__init__(self, "configuration file error: invalid option: %s"  % message)

class NoFittestException(Exception):
    pass
    
class FailedCompilationException(Exception):
    pass

class BinaryRunException(Exception):
    pass