# -*- coding: utf-8 -*-
"""
Bird class definition    : Traffic data
Methods:
    Birds()              :  constructor
    reset()              :  Reset traffic database w.r.t a/c data
    create()             :  readin database and create bird
    check_bird()         : check whether bird is already flying
    remove_bird(birdid)  : delete a bird from bird data
    remove_input()       : delete used input
    update(simt)         : do a numerical integration step
    update_position()    : update all bird's positions
    calculate_position() : calculate all bird's positions
    determine_secs(time) : time conversion


Created by  : Isabel Metz

"""

import numpy as np
import datetime
import pandas as pd
import os

from randomize_birdies import randomize_birds


class Birds:
    
    

    def __init__(self):

        self.starttime = datetime.datetime.now()
        global earth_radius
        earth_radius = 6371000.0 # Earth radius in m  
        
        global individual_radius
        global flock_radius
        
        individual_radius = 0.5
        flock_radius = 5.
        
        global lat_south
        global lat_north
        global lon_west
        global lon_east
        

        lat_south = 51.2855167
        lat_north = 51.552975

        lon_west = 5.1347806
        lon_east = 5.50
        
        self.dir = os.path.dirname(__file__)

        # create the buffers for all variables
        self.reset()
        
        return

###############

    def determine_secs(self,input_time):
        input_time = list(input_time)
        input_time_converted = []
                
        for timestamp in input_time:
            t = timestamp.split(" ")[-1].split(":")
            seconds = float(t[0])*3600 + float(t[1])*60 + float(t[2])
                
            input_time_converted.append(seconds)
            
        return np.array(input_time_converted)
        
        

###############

    def reset(self):
        
        # values from file
        self.input_time = np.array([])
        
        # values for calculation 
        self.last_ts    = np.array([])
        self.last_lat   = np.array([])
        self.last_lon   = np.array([])
        self.lat        = np.array([])
        self.lon        = np.array([])
        self.tas        = np.array([])
        self.trk        = np.array([])
        self.alt        = np.array([])
        self.flock_flag = np.array([], dtype = int)
        self.id         = np.array([], dtype = int)
        self.bird_size  = np.array([], dtype = int)
        self.no_inds    = np.array([], dtype = int)
        self.collision_radius = np.array([])
        
        # birds which experienced a strike don't fly anymore
        self.removed_id = np.array([])
        
        # set timer for deletions
        self.deletedt = 60. # [s] interval to delete birds that left the area
        self.deletet0 = -self.deletedt # init
        
        

        return  


########################


    # provide the data to the simulation    
    def create(self, filename):
        #print "in readin", datetime.datetime.now() - self.starttime, datetime.datetime.now()

        # required for Monte-Carlo-Sims: the full name of the file (e.g. EGKK_2016_06_03-1)
        # is needed for the logging. But as we have the same file as imput for all
        # of the scenarios, only EGKK_2016_06_03 should be used for the path
        # where to read the file from
        self.filename2save = filename # used for recording
        
        # we do not always do MC simulations, so here is the back door
        if len(self.filename2save) > 15:
            print "MONTE CARLO SIMULATION!!!", filename, filename[0:15]
            filename2use = "movements/" + filename[0:15] + ".csv"
            filename_path = os.path.join(self.dir, filename2use)
            print filename_path
            
            # in case of MC simulations, we want randomized speed, heading and position

            # if the filename works: pass on to randomizer
            if os.path.isfile(filename_path):
                
                
                # seed depends on bird movement plan number
                # filename2use[15] is the underline. Hence the number starts at position filename2use[16]
                seed = int(filename[16:])
                print "bird movement plan exists for that day, seed is ", seed
                data = randomize_birds(seed, filename_path)

                self.assign_values(data)
                
                
            else:
                print "no such file ", filename      
            
            
            
            
            
            
            
        else:
            print "NOOOOOOOOOOOOOOO MONTE CARLO", filename
            filename2use = "movements/" + filename + ".csv"
            filename = os.path.join(self.dir, filename2use)

            print "yay, we have a file, we read from", filename
        
            # if not: tell the user
            try:
            
            # cat means bird size

            # because of the MC simulations, more  columns are required. However, we only need the limited set to continue

                data = pd.read_csv(filename, sep = "\,", \
                                     names = ['id', 'date', 'lon','lat', 'alt', 'cat', 'no_individuals', 'flock_flag',\
                                     'id1', 'hdg', 'spd', 'lat_s1', 'lat_n1', 'lon_w1', 'lon_e1','lat_s2', 'lat_n2', 'lon_w2', 'lon_e2'], index_col = False, engine = 'python')

                data = data.drop(['lat_s1', 'lat_n1', 'lon_w1', 'lon_e1','lat_s2', 'lat_n2', 'lon_w2', 'lon_e2'], axis=1)
                                   
                self.assign_values(data)
                
            except:
                print "no such file"
                return

    

        #print self.input_id1[0], self.input_id2[0], self.input_lat[0], self.input_lon[0], self.input_spd[0], self.input_hdg[0], self.input_alt[0], self.input_bird_size[0], self.input_time[0]
    
        #print "end of readin", datetime.datetime.now() - self.starttime, datetime.datetime.now()


  
        return

    def assign_values(self, data):
        self.input_id1 = np.array(pd.to_numeric(data["id"])).astype(int)
        self.input_id2 = np.array(pd.to_numeric(data["id1"])).astype(int)
        self.input_lat = np.array(pd.to_numeric(data["lat"]))
        self.input_lon = np.array(pd.to_numeric(data["lon"]))
        self.input_spd = np.array(pd.to_numeric(data["spd"]))
        self.input_hdg = np.array(pd.to_numeric(data["hdg"]))
        self.input_alt = np.array(pd.to_numeric(data["alt"]))
        
        self.input_bird_size  = np.array(pd.to_numeric(data["cat"])).astype(int)
        self.input_flock_flag = np.array(data["flock_flag"])
        self.input_no_inds    = np.array(data['no_individuals']).astype(int)
        
        self.input_time = np.array(pd.to_numeric(data['date']))           
        return
           



#######################


    # check whether the current bird is known already. If not, create    
    def check_bird(self, input_id1, input_bird_size, input_no_inds, input_flock_flag, input_alt):

        # test 1: not in removed_id: if an avian radar bird was eaten by
        # an aircraft, it still might have track data. But as it has been eaten,
        # it can't fly anymore

        # WARNING: THis bird_idx_to add does refer to the idx in the list "input_id1", not the position
        # in the input list containing all birdies
        bird_idx_to_add = np.where(np.in1d(input_id1, self.removed_id, invert = True) & (np.in1d(input_id1, self.id, invert = True)))[0]


#print test[np.where(np.in1d(test, already_in, invert = True) & (np.in1d(test, killed, invert = True)))[0]]

            
            # np.where idx is not in removed or id
            # append the values with these idxs
            
       # print "inputs", input_id1, input_bird_size, input_flock_flag, input_alt
        #print "in removed", np.in1d(input_id1, self.removed_id, invert = True), "in id", (np.in1d(input_id1, self.id, invert = True)), "both", bird_idx_to_add, "id", self.id, "removed", self.removed_id, "input", input_id1      
        
        # collision radius of birds: f(span, size, number)
        add_no_inds = input_no_inds[bird_idx_to_add]
        add_bird_size = input_bird_size[bird_idx_to_add]


        # spans are
        # small: 0.34 m
        # medium: 0.69 m
        # large: 1.43 m
     
        # radius for protected zone around birds
        add_radius = np.zeros(len(bird_idx_to_add))

        # *0.5 because span is diameter and we need radius
        add_radius[add_bird_size == 6] = (np.sqrt(add_no_inds[add_bird_size == 6])* 0.5 * 0.32) + 0.06
        add_radius[add_bird_size == 5] = (np.sqrt(add_no_inds[add_bird_size == 5])* 0.5 * 0.68) + 0.16
        add_radius[add_bird_size == 4] = (np.sqrt(add_no_inds[add_bird_size == 4])* 0.5 * 1.40) + 0.41
        
        add_radius[np.where((add_bird_size == 6)&(add_no_inds ==1))] = 0.5 * 0.32
        add_radius[np.where((add_bird_size == 5)&(add_no_inds ==1))] = 0.5 * 0.68
        add_radius[np.where((add_bird_size == 4)&(add_no_inds ==1))] = 0.5 * 1.40


        
        self.id         = np.append(self.id, input_id1[bird_idx_to_add])
        self.bird_size  = np.append(self.bird_size, add_bird_size )
        self.no_inds    = np.append(self.no_inds, add_no_inds )
        self.flock_flag = np.append(self.flock_flag, input_flock_flag[bird_idx_to_add])
        # and a placeholder for all the other items
        self.last_ts  = np.append(self.last_ts, np.zeros([len(bird_idx_to_add)])) 
        self.last_lat = np.append(self.last_lat, np.zeros([len(bird_idx_to_add)]))
        self.last_lon = np.append(self.last_lon, np.zeros([len(bird_idx_to_add)]))
        self.lat      = np.append(self.lat, np.zeros([len(bird_idx_to_add)]))
        self.lon      = np.append(self.lon, np.zeros([len(bird_idx_to_add)]))
        self.tas      = np.append(self.tas, np.zeros([len(bird_idx_to_add)]))
        self.trk      = np.append(self.trk, np.zeros([len(bird_idx_to_add)]))

        self.alt      = np.append(self.alt, input_alt[bird_idx_to_add])
        self.collision_radius = np.append(self.collision_radius, add_radius)
       # print "id", self.id, "idx_add", bird_idx_to_add, "coll_rad", self.collision_radius, "input_bird_size", input_bird_size
        #print "birdie ", input_id1[bird_idx_to_add], "is inited as ", input_flock_flag[bird_idx_to_add], "with ",  add_no_inds, "members"

        #print "ids are now ", self.id, "radii are ", self.collision_radius
        return
         
         
#####################

    def remove_input(self, no_to_remove):

        # remove the info we already looked at
    # these are the first x elements. So the array now starts at the position [element]+1

        self.input_time             = self.input_time[no_to_remove :]
        self.input_id1              = self.input_id1[no_to_remove :]
        self.input_id2              = self.input_id2[no_to_remove :]
        self.input_lat              = self.input_lat[no_to_remove :]
        self.input_lon              = self.input_lon[no_to_remove :]
        self.input_spd              = self.input_spd[no_to_remove :]
        self.input_hdg              = self.input_hdg[no_to_remove :]   
        self.input_alt              = self.input_alt[no_to_remove :]
        self.input_flock_flag       = self.input_flock_flag[no_to_remove :]
        self.input_bird_size        = self.input_bird_size[no_to_remove :]
        self.input_no_inds          = self.input_no_inds[no_to_remove : ]

        
        return
        
        
########################
        
        
    def remove_bird(self, index_to_remove):
        # as soon as a bird leaves the simulation, its information has to be removed
        # idx is the index, where the bird info is stored per list

        # mark the bird as removed
        self.removed_id = np.append(self.removed_id, self.id[index_to_remove])
        
        self.last_ts          = np.delete(self.last_ts, index_to_remove)
        self.last_lat         = np.delete(self.last_lat, index_to_remove)
        self.last_lon         = np.delete(self.last_lon, index_to_remove)
        self.lat              = np.delete(self.lat, index_to_remove)
        self.lon              = np.delete(self.lon, index_to_remove)
        self.trk              = np.delete(self.trk, index_to_remove)    
        self.alt              = np.delete(self.alt, index_to_remove)
        self.tas              = np.delete(self.tas, index_to_remove)
        self.id               = np.delete(self.id, index_to_remove)   
        self.bird_size        = np.delete(self.bird_size, index_to_remove)
        self.no_inds          = np.delete(self.no_inds, index_to_remove)
        self.flock_flag       = np.delete(self.flock_flag, index_to_remove)
        self.collision_radius = np.delete(self.collision_radius, index_to_remove)
        

        return


######################

    def update_position(self, simtime):
        delta_t = abs(simtime - self.last_ts)
        delta_s = self.tas * delta_t
        #print "lastts", self.last_ts[0:10],  "simtime", simtime
        #print "DELTAAAAAAAAAAAAAAAAA", delta_t[0:10]
        
        
        
        self.calculate_position(delta_t, delta_s)
        
        # removal of birds that left the area: only once per minute
        if abs(simtime - self.deletet0) >= self.deletedt:
            
            # test if any birds already left the area
            left_south = np.where(self.lat < lat_south)[0]
            left_north = np.where(self.lat > lat_north)[0]
            left_west  = np.where(self.lon < lon_west)[0]
            left_east  = np.where(self.lon > lon_east)[0]
            
            all_left = list(np.unique(np.concatenate((left_south, left_north, left_west, left_east))))
            self.remove_bird(all_left)
            
            # reset timer
            self.deletet0 = simtime
        return
        

    # all calculations are performed in radians
    def calculate_position(self, delta_t, delta_s):

        theta = np.radians(self.trk)
        last_lat = np.radians(self.last_lat)
        last_lon = np.radians(self.last_lon)
        
        
        d = delta_s/earth_radius

        lat_pos = np.arcsin(np.sin(last_lat)*np.cos(d) + np.cos(last_lat)*np.sin(d)*np.cos(theta))
        
        lon_pos = last_lon + np.arctan2(np.sin(theta)*np.sin(d)*np.cos(last_lat),
                      np.cos(d) - np.sin(last_lat)*np.sin(lat_pos))        

        
        self.lat = np.degrees(lat_pos)
        self.lon = np.degrees(lon_pos)

        
        return

####################




    def update(self, simtime):

        # only process when there is at least one bird left


        if len(self.input_time) <1 or simtime > self.input_time[-1]:
            self.reset()
            return
            
        # work with all values corresponding to timestamps already over
        '''
        This is a little faster (and looks nicer)

        np.argmax(aa>5)

        Since argmax will stop at the first True ("In case of multiple occurrences of the 
        maximum values, the indices corresponding to the first occurrence are returned.") 
        and doesn't save another list.
        --> use  index in sense of input_time = self.input_time[0:index]
        '''    
            
            
        #idx_time_passed = np.where(self.input_time <= simtime)[0]  
        idx_time_passed = np.argmax(self.input_time > simtime)
       # print "idx time passed", idx_time_passed         
            

        

        # bird info to the check-function
        # check bird is performed for all the birds that we got in the lists
        #print "we check", input_id1
        if idx_time_passed > 0:
            input_time            = self.input_time[ : idx_time_passed]
            input_id1             = self.input_id1[ : idx_time_passed]
            input_id2             = self.input_id2[ : idx_time_passed]
            input_bird_size       = self.input_bird_size[ : idx_time_passed]
            input_no_inds         = self.input_no_inds[ : idx_time_passed]
            input_flock_flag      = self.input_flock_flag[ : idx_time_passed]
            input_alt             = self.input_alt[ : idx_time_passed]      
            input_lat             = self.input_lat[ : idx_time_passed]
            input_lon             = self.input_lon[ : idx_time_passed]
            input_spd             = self.input_spd[ : idx_time_passed]
            input_hdg             = self.input_hdg[ : idx_time_passed]
                
            self.check_bird(input_id1, input_bird_size, input_no_inds, input_flock_flag, input_alt)

            # there are probably birds in this set which reached their last timestep.
            # they have to be removed
            # trigger: id1 != id2
            # input_id and self.id have different order - we need the positions
            #  of self.id!
            id_to_remove = input_id1[np.where(input_id1 != input_id2)[0]]
            if len(id_to_remove) > 0:
                to_remove = []

                for identity in id_to_remove:
                
                    if identity in self.id:
                        
                        to_remove = to_remove + list(np.where(self.id == identity)[0])

            # and remove the bird from the simulation
            # but only if there is anything to remove
                self.remove_bird(to_remove) 
                

                # input_id1 has to be adjusted as well, otherwise we run into 
                # trouble with the curr_idx-comparison
                # input_id1 = np.delete(input_id1, index_to_remove)


        # position update
        # explanation np.ndenumerate: index is the iterator through the array
        # while id1 is the actual value. 
        # e.g. ([4,3,7]): index = 0,1,2, id1 = 4,3,7

            for index, id1 in np.ndenumerate(input_id1):
                index_to_replace = np.where(self.id == id1)[0]        
            
                self.last_ts[index_to_replace]  = input_time[index]
                self.last_lat[index_to_replace] = input_lat[index]
                self.last_lon[index_to_replace] = input_lon[index]
                self.tas[index_to_replace]      = input_spd[index]
                self.trk[index_to_replace]      = input_hdg[index]





            self.remove_input(idx_time_passed)
        
        
        self.update_position(simtime)

            
        return


