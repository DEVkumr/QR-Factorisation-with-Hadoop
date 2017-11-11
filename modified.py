import sys
import os
import random
import time

import numpy
import numpy.linalg

import hadoopy

import hadoopy_util

# the globally saved options.  The actual mapreduce jobs pickup 
# their saved options from the command line environment.  The 
# source job picks up its options from the command line arguments.
gopts = hadoopy_util.SavedOptions()

class SerialTSQR():
    def __init__(self,blocksize=3,keytype='random',isreducer=False):
        self.blocksize=blocksize
        if keytype=='random':
            self.keyfunc = lambda x: random.randint(0, 4000000000)
        elif keytype=='first':
            self.keyfunc = self._firstkey
        else:
            raise Error("Unkonwn keytype %s"%(keytype))
        self.first_key = None
        self.nrows = 0
        self.data = []
        self.ncols = None
        
        if isreducer:
            self.__call__ = self.reducer
        else:
            self.__call__ = self.mapper
    
    def _firstkey(self, i):
        if isinstance(self.first_key, (list,tuple)):
            return (util.flatten(self.first_key),i)
        else:
            return (self.first_key,i)
    
    def array2list(self,row):
        return [float(val) for val in row]

    def QR(self):
        A = numpy.array(self.data)
        return numpy.linalg.qr(A,'r')
        
    def compress(self):
        """ Compute a QR factorization on the data accumulated so far. """
        t0 = time.time()
        R = self.QR()
        dt = time.time() - t0
        hadoopy.counter('Timer','numpy time (millisecs)',int(1000*dt))
        
        # reset data and re-initialize to R
        self.data = []
        for row in R:
            self.data.append(self.array2list(row))
            
            
    
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
            
    def close(self):
        self.compress()
        for i,row in enumerate(self.data):
            key = self.keyfunc(i)
            yield key, row
            
    def mapper(self,key,value):
        if isinstance(value, str):
            # handle conversion from string
            value = [float(p) for p in value.split()]
        self.collect(key,value)
        
    def reducer(self,key,values):
        for value in values:
            self.mapper(key,value)
        
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
    output = args.get('output','%s-qrr%s'%(matname,matext))
    if hadoopy.exists(output):
        print "Removing %s"%(output)
        hadoopy.rm(output)
    
    outputnamefunc = lambda x: output+"_iter%i"%(x)
    steps = schedule.split(',')
    
    jobconfs = []
    
    # determine the split size
    if 'split_size' in args:
        splitsize = args['split_size']
        jobconfs.append(
            'mapreduce.input.fileinputformat.split.minsize='+str(splitsize))
    
        
    for i,step in enumerate(steps):
        if i>0:
            input = curoutput
            mapper = 'org.apache.hadoop.mapred.lib.IdentityMapper'
        else:
            mapper = True # use the command line mapper
            
        if i+1==len(steps):
            curoutput = output
        else:
            curoutput = output+"_iter%i"%(i+1)
            if hadoopy.exists(curoutput):
                hadoopy.rm(curoutput)
            
        gopts.setkey('iter',i)
            
        if launch:
            hadoopy.launch_frozen(input, curoutput, __file__, 
                mapper=mapper,
                cmdenvs=gopts.cmdenv(), num_reducers=int(step),
                jobconfs=jobconfs)
    
    
def runner():
    """ The function that calls haoodpy.run """
    iter = gopts.getintkey('iter')
    blocksize = gopts.getintkey('blocksize')
    reduce_schedule = gopts.getstrkey('reduce_schedule')
    
    mapper = SerialTSQR(blocksize=blocksize,isreducer=False)
    reducer = SerialTSQR(blocksize=blocksize,isreducer=True)
    
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