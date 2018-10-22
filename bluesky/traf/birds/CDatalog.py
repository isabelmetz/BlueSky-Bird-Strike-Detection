""" 
Datalog class definition : Data logging class

Methods:
    Datalog(filename)          :  constructor

    write(txt)         : add a line to the datalogging buffer
    save()             : save data to file
   
Created by  : Isabel Metz
Date        : March 2015

Modification  :
By            :
Date          :

"""

import os
dir = os.path.dirname(__file__)
#-----------------------------------------------------------------

class Datalog():
    def __init__(self):

# Create a buffer and save filename

        self.buffer=[]
        
        #filename will be set in first run
        self.filename_flag = False

         
        return
    
    def write(self, filename,time, ac_data, bird_data, occurrence_type):


        # filename[5:15] is the date
        self.buffer.append( filename[5:15] +" \t "  + time +" \t " + ac_data + " \t " + bird_data + '\t' + occurrence_type + chr(13) + chr(10))
       
        return

    def save(self, filename):
        
        # files are saved per airport. Hence only create a new file if 
        # no file for this airport exists
        log_file = os.path.join(dir, "log/" + filename[0:4] + "/" + filename + ".txt" )

        if not os.path.isfile(log_file):  
           # log_file = "log/" + filename_def + ".txt"
           # self.log_file = os.path.join(dir, log_file)
            #print "INIT", filename_def, filename, log_file
            
            with open(log_file, "a") as writeto:
                writeto.write('date \t time \t id_ac \t tas \t lat \t lon \t alt \t type \t orig \t dest id_bird \t tas \t lat \t lon \t alt \t size \t coll_rad \t number \t flock_flag \t occurrence type \n')
        
        
       # if not self.filename_flag:
          #  filename = "log/" + filename + ".txt"
            
           # self.filename = os.path.join(dir,  filename)

            # write the header            
            #with open(self.filename, "a") as writeto:
            #    writeto.write('time \t id_ac \t tas \t lat \t lon \t alt \t type \t orig \t dest id_bird \t tas \t lat \t lon \t alt \t size \t coll_rad \t number \t flock_flag \n')

            #self.filename_flag = True

# Write buffer to file 

        with open(log_file, "a") as writeto:
            for i in xrange(len(self.buffer)):

                writeto.write(self.buffer[i])


        self.buffer = []    
        


        
        
        
        
        return