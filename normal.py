import sys
import os
import random

import numpy
import numpy.linalg

import hadoopy

import hadoopy_util

# the globally saved options.  The actual mapreduce jobs pickup 
# their saved options from the command line environment.  The 
# source job picks up its options from the command line arguments.
gopts = hadoopy_util.SavedOptions()

class NormalEquations():
    def __init__(self,blocksize=3,isreducer=False):
        self.blocksize=blocksize
        self.first_key = None
        self.nrows = 0
        self.data = []
        self.ncols = None
        self.accum = None
        
        if isreducer:
            self.__call__ = self.reducer
        else:
            self.__call__ = self.mapper
            self.close = self.mapper_close

    def array2list(self,row):
        return [float(val) for val in row]

    def AtA(self):
        """ Compute the product A'*A with the local block of rows. """
        A = numpy.array(self.data)
        return A.T.dot(A)
        
    def compress(self):
        """ Compute a QR factorization on the data accumulated so far. """
        if self.accum is None:
            self.accum = self.AtA()
        else:
            self.accum += self.AtA()
        self.data = []
    
    def collect(self,key,value):
        if len(self.data) == 0:
            self.first_key = key
        
        if self.ncols == None:
            self.ncols = len(value)
            print >>sys.stderr, "Matrix size: %i columns"%(self.ncols)
        else:
            # TODO should we warn and truncate here?
            # No. that seems like something that will introduce
            # bugs.  Maybe we could add a "liberal" flag
            # for that.
            assert(len(value) == self.ncols)
        
        self.data.append(value)
        self.nrows += 1
        
        if len(self.data)>self.blocksize*self.ncols:
            hadoopy.counter('Program','QR Compressions',1)
            # compress the data
            self.compress()
            
        # write status updates so Hadoop doesn't complain
        if self.nrows%50000 == 0:
            hadoopy.counter('Program','rows processed',50000)
            
    def mapper_close(self):
        self.compress()
        for i,row in enumerate(self.accum):
            yield i, self.array2list(row)
            
    def mapper(self,key,value):
        if isinstance(value, str):
            # handle conversion from string
            value = [float(p) for p in value.split()]
        self.collect(key,value)
        
    def reducer(self,key,values):
        accum = None
        for value in values:
            if accum is None:
                accum = numpy.array(value)
            else:
                accum += numpy.array(value)
        yield key, self.array2list(accum)
            
        
def starter(args, launch=True):
    """ The function that calls hadoopy.launch_frozen """
    gopts.args = args
    
    mat = args.get('mat',None)
    if mat is None:
        raise NameError("'mat' option not specified on the command line")
        
    input = mat
    matname,matext = os.path.splitext(mat)
    
    gopts.getintkey('blocksize',3)
    schedule = gopts.getstrkey('reduce_schedule','1')

    # clear the output
    output = args.get('output','%s-normal%s'%(matname,matext))
    if hadoopy.exists(output):
        print "Removing %s"%(output)
        hadoopy.rm(output)
    
    outputnamefunc = lambda x: output+"_iter%i"%(x)
    steps = schedule.split(',')
        
    for i,step in enumerate(steps):
        if i>0:
            input = curoutput
            
        if i+1==len(steps):
            curoutput = output
        else:
            curoutput = output+"_iter%i"%(i+1)
            if hadoopy.exists(curoutput):
                hadoopy.rm(curoutput)
            
        gopts.setkey('iter',i)
            
        if launch:
            if i>0:
                mapper="org.apache.hadoop.mapred.lib.IdentityMapper"
                hadoopy.launch_frozen(input, curoutput, __file__, 
                    mapper=mapper,
                    cmdenvs=gopts.cmdenv(), num_reducers=int(step))
            else:
                hadoopy.launch_frozen(input, curoutput, __file__, 
                    cmdenvs=gopts.cmdenv(), num_reducers=int(step))
    
    
def runner():
    """ The function that calls haoodpy.run """
    iter = gopts.getintkey('iter')
    blocksize = gopts.getintkey('blocksize')
    reduce_schedule = gopts.getstrkey('reduce_schedule')
    
    mapper = NormalEquations(blocksize=blocksize,isreducer=False)
    reducer =  NormalEquations(blocksize=blocksize,isreducer=True)
    
    
    hadoopy.run(mapper, reducer)
            

if __name__=='__main__':
    args = hadoopy_util.get_args(sys.argv[1:])
    print >>sys.stderr, sys.argv[1:]
    if sys.argv[1] == 'freeze':
        starter(args,launch=False)
        runner()
    elif sys.argv[1] != 'map' and sys.argv[1] != 'reduce':
        starter(args)
    else:
        runner()