# -*- coding: utf-8 -*-
"""
Created on Thu Nov 17 08:49:23 2016

@author: metz_is
"""



import numpy as np
from src_cpp import cbirds

import CDatalog

class Conflict_Detection_Birds:
    
    def __init__(self, traf, birds):
        


        self.counter_strikes = 0
        self.traf = traf
        self.birds = birds
        
        global earth_radius
        earth_radius = 6371000.0 # Earth radius in m          
        
        # Create datalog instance
        self.log = CDatalog.Datalog()
        
        # near misses should only be counted once, i.e. when the outer protected
        # area is penetrated for the first time. List for check is list of 
        # tuples with the ac/bird combinations
        self.registered_nm = []
        
        
        # C++ bla
        self.test_conflicts = cbirds.detect_birdstrikes

        

        return
        
     

        
    def conflict_detection(self, simt):

        
        # forward to the conflict detection code in c++ 
        # outputs are lists for near misses and collisions
        idx_nm_ac, idx_nm_birds, idx_coll_ac, idx_coll_birds = self.test_conflicts(self.birds, self.traf, simt)

        # first evaluate the near misses
        if len(idx_nm_ac) > 0:
         #   print  "NEARMISS", type(idx_nm_ac), type(idx_nm_birds), type(idx_coll_ac), type(idx_coll_birds)
            #print "IN NEARMISS, ac is ", self.traf.collision_radius, "bird is ", self.birds.collision_radius
            for idx_ac, idx_bird in zip(idx_nm_ac, idx_nm_birds):
                # check whether we already know about this nearmiss
                if (self.traf.id[idx_ac], self.birds.id[idx_bird]) not in self.registered_nm:
                    
                    # well, now we know, so add it to the registered-list
                    self.registered_nm.append((self.traf.id[idx_ac], self.birds.id[idx_bird]))
                    
                    # and log the incident
                    self.logging(idx_ac, idx_bird, simt, "nearmiss")
                    
                    # finally: save the logs from the current time step
                    self.log.save(self.birds.filename2save) 
                
                
                
        # then the collisions
        if len(idx_coll_ac) > 0:
           # print "COLLISION", type(idx_nm_ac), type(idx_nm_birds), type(idx_coll_ac), type(idx_coll_birds)
           # print  idx_nm_ac, idx_nm_birds, idx_coll_ac, idx_coll_birds
            for idx_ac, idx_bird in zip(idx_coll_ac, idx_coll_birds):
                
                # for bookkeeping in traf
                # 2DO: REQUIRED?
                self.traf.hit_ac[idx_ac] = idx_ac 
                
                #print "AFTER COLLISION, collrad birds ", self.birds.collision_radius, "collrad_ac",  self.traf.collision_radius
                
                                
                self.logging(idx_ac, idx_bird, simt, "collision")
                # finally: save the logs from the current time step
                self.log.save(self.birds.filename2save)
                
                # remove birds that were hit
                self.birds.remove_bird(idx_bird)
				
			
		     

  

        return 

    def logging(self, idx_ac, idx_bird, strike_time, occurrence_type):
       
        ac_data = str(self.traf.id[idx_ac]) + ' \t ' + str(self.traf.tas[idx_ac]) \
         + ' \t ' + str(self.traf.lat[idx_ac]) + ' \t ' + str(self.traf.lon[idx_ac]) \
         + ' \t ' + str(self.traf.alt[idx_ac]) + ' \t ' + str(self.traf.type[idx_ac]) \
         + ' \t ' + str(self.traf.orig[idx_ac]) + ' \t ' +  str(self.traf.dest[idx_ac])       
       

        bird_data = (str(self.birds.id[idx_bird]) + ' \t ' +  str(self.birds.tas[idx_bird]) \
                    + ' \t ' + str(self.birds.lat[idx_bird]) + ' \t ' +  str(self.birds.lon[idx_bird]) \
                    + ' \t ' + str(self.birds.alt[idx_bird]) + ' \t ' + str(self.birds.bird_size[idx_bird])\
                    + ' \t ' + str(self.birds.collision_radius[idx_bird]) + ' \t ' + str(self.birds.no_inds[idx_bird]) \
                    + ' \t ' + str(self.birds.flock_flag[idx_bird])) 
       

        self.log.write(self.birds.filename2save, str(strike_time), ac_data, bird_data, occurrence_type)

       
        return
       
        


