# -*- coding: utf-8 -*-
"""
Created on Thu Nov 17 08:49:23 2016

@author: metz_is
"""



import numpy as np

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
        

        return
        
     
        
        return
        
    def conflict_detection(self, simt):
        
        # only run if there are birds and aircraft
        if (len(self.birds.id) <1 ) or (len(self.traf.id) <1):
            return

        # bring input to correct format
        lat_birds, lon_birds, alt_birds, lat_aircraft, lon_aircraft, alt_aircraft = self.reshape()       

        # first filter:lateral distance
        dxy = self.distance(np.radians(lat_birds), np.radians(lon_birds), np.radians(lat_aircraft), np.radians(lon_aircraft))

        # is this already in the dangerous area?
        # input for ac is already radius (diameter/2)
        # for birds we are fixed now: 0.5m individuals, 5m flocks
        c_rad_birds = self.birds.collision_radius.reshape(len(self.birds.collision_radius), 1)
        c_rad_ac = self.traf.collision_radius.reshape(1,len(self.traf.collision_radius))
        dangerous_dist = (dxy <= c_rad_birds + c_rad_ac)*1.
        
        # only continue for bird-ac combinations where the lateral distance is too small
        if len(np.where(np.any(dangerous_dist == 1. , axis = 1) == True)[0]) > 0 and \
           len(np.where(np.any(dangerous_dist == 1. , axis = 0) == True)[0]) > 0 : 
               

               
               # filter
               alt_birds = alt_birds[np.where(np.any(dangerous_dist == 1. , axis = 1) == True)[0]]
               alt_aircraft = alt_aircraft[0][np.where(np.any(dangerous_dist == 1., axis = 0) == True)[0]]
               collision_height = self.traf.collision_height[np.where(np.any(dangerous_dist == 1. , axis = 0) == True)[0]]                
               
               # filter
               lat_birds    = lat_birds[np.where(np.any(dangerous_dist == 1. , axis = 1) == True)[0]]
               lon_birds    = lon_birds[np.where(np.any(dangerous_dist == 1. , axis = 1) == True)[0]]
               lat_aircraft = lat_aircraft[0][np.where(np.any(dangerous_dist == 1., axis = 0) == True)[0]]
               lon_aircraft = lon_aircraft[0][np.where(np.any(dangerous_dist == 1., axis = 0) == True)[0]]
               
               
               # is a list and has therefore to be converted 
               id_ac = np.array(self.traf.id)
               # used for later
               sweep = self.traf.sweep[np.where(np.any(dangerous_dist == 1. , axis = 0) == True)[0]]
               hdg   = self.traf.hdg[np.where(np.any(dangerous_dist == 1. , axis = 0) == True)[0]]
               id_ac = id_ac[np.where(np.any(dangerous_dist == 1. , axis = 0) == True)[0]]
               id_bird = self.birds.id[np.where(np.any(dangerous_dist == 1. , axis = 1) == True)[0]]




               # altiutde difference: 
               # only birds in the same plane as the aircraft are interesting
               # input is already ac_height/2
               dangerous_alt = (abs(alt_birds - alt_aircraft) <= collision_height)*1.
               
               # only continue if there are bird-ac combinations within 
               #dangerous distance AND in the same altitude band
    
                # only continue if any birds and aircraft are in the same altitude layer
               if len(np.where(np.any(dangerous_alt == 1. , axis = 1) == True)[0]) > 0 and \
                  len(np.where(np.any(dangerous_alt == 1. , axis = 0) == True)[0]) > 0 :

                    
                    # filter
                    lat_birds    = lat_birds[np.where(np.any(dangerous_alt == 1. , axis = 1) == True)[0]]
                    lon_birds    = lon_birds[np.where(np.any(dangerous_alt == 1. , axis = 1) == True)[0]]
                    

                    lat_aircraft = lat_aircraft[np.where(np.any(dangerous_alt == 1., axis = 0) == True)[0]]
                    lon_aircraft = lon_aircraft[np.where(np.any(dangerous_alt == 1., axis = 0) == True)[0]]
                    

                    sweep        = sweep[np.where(np.any(dangerous_alt == 1. , axis = 0) == True)[0]]
                    hdg          = hdg[np.where(np.any(dangerous_alt == 1. , axis = 0) == True)[0]]
                    id_ac        = id_ac[np.where(np.any(dangerous_alt == 1. , axis = 0) == True)[0]]
                    id_bird      = id_bird[np.where(np.any(dangerous_alt == 1. , axis = 1) == True)[0]]

            
                    # bearing between bird and aircraft
                    bearing = self.bearing(np.radians(lat_aircraft), np.radians(lon_aircraft), np.radians(lat_birds), np.radians(lon_birds))
    
                    # top view of the aircraft: bird strikes only occurr if 
                    # they take place in the front half (end is wingtip)
                    # relative values required
                    pacman_high = ( 90. + sweep)
                    pacman_low  = (-90. - sweep)
                    
                    # explanation in method
                    delta_heading = ((((hdg - bearing)%360.) + 180. + 360.)% 360.) - 180.        
                    
                
                    # and is it within the front area of the aircraft?
                    # then we have a strike!
                    pacman = ((delta_heading > pacman_low) & (delta_heading < pacman_high) )* 1.

                    # which birds were hit? 

                    id_hit_birds = id_bird[np.where(np.any(pacman ==1., axis = 1) == True)[0]]
                    id_hit_ac = id_ac[np.where(np.any(pacman ==1., axis = 0) == True)[0]]


                    
                    # only continue if there was a strike
                    if len(id_hit_birds) > 0:
                        strike_time = simt
                        
                        idx_birds_hit = []
                        bird_data = []
                        lat_birds = []
                        lon_birds = []
                        
                        for identity in id_hit_birds:
                            # this is the index in the class birds
                            index_birds = int(np.where(self.birds.id == float(identity))[0][0])
                            idx_birds_hit.append(index_birds) 
                            lat_birds.append(self.birds.lat[index_birds])
                            lon_birds.append(self.birds.lon[index_birds])
                            
                            bird_data.append(str(self.birds.id[index_birds]) + ' \t ' +  str(self.birds.tas[index_birds]) \
                                              + ' \t ' + str(self.birds.lat[index_birds]) + ' \t ' +  str(self.birds.lon[index_birds]) \
                                              + ' \t ' + str(self.birds.alt[index_birds]) + ' \t ' + str(self.birds.bird_size[index_birds])\
                                              + ' \t ' + str(self.birds.collision_radius[index_birds]) + ' \t ' + str(self.birds.no_inds[index_birds]) \
                                              + ' \t ' + str(self.birds.flock_flag[index_birds]))   
                        
                            # log data
                            #self.log.write(str(strike_time), "BIRD", str(self.birds.id[index_birds]),\
                            #                str(self.birds.tas[index_birds]), str(self.birds.lat[index_birds]), \
                             #               str(self.birds.lon[index_birds]), str(self.birds.alt[index_birds]), \
                             #               str(self.birds.cat[index_birds]), str(self.birds.flock_flag[index_birds]), \
                               #             "BUFFER")
                                                                    
                            
                        
                        # remove them        
                        self.birds.remove_bird(idx_birds_hit)
          
                        # store IDs of hit aircraft
                        #id_hit_ac = id_ac[np.where(np.any(pacman ==1., axis = 0) == True)[0]]

                        
                        # increase counter
                        self.counter_strikes = self.counter_strikes + len(id_hit_ac)

                        #  store the aircraft id's of the hit aircraft - preparation
                        to_mark = []
                        for identity in id_hit_ac:

                            if identity in self.traf.id:
                                to_mark.append(int(np.where(np.array(self.traf.id) == identity)[0][0]))
                        to_mark = np.unique(to_mark)
                       
                        # store the aircraft indices of the hit aircraft - execution 
                        # idx is the index of the array: 0:n
                        # pos is the value of to_mark at the index - in this case
                        # it marks the position of the aircraft within the hit_ac array
                        
                        for idx in to_mark:

                            self.traf.hit_ac[idx] = idx
                            ac_data = str(self.traf.id[idx]) + ' \t ' + str(self.traf.tas[idx]) \
                             + ' \t ' + str(self.traf.lat[idx]) + ' \t ' + str(self.traf.lon[idx]) \
                             + ' \t ' + str(self.traf.alt[idx]) + ' \t ' + str(self.traf.type[idx]) \
                             + ' \t ' + str(self.traf.orig[idx]) + ' \t ' +  str(self.traf.dest[idx])
                            
                            # which bird did this aircraft hit?
                            # determination via lat-lon difference (max. 0.001 resp.)
                            for i in xrange(len(idx_birds_hit)):

                                if (abs(self.traf.lat[idx] - lat_birds[i]) < 0.001) and \
                                    (abs(self.traf.lon[idx] - lon_birds[i] < 0.001)):

                                        self.log.write(self.birds.filename2save, str(strike_time), ac_data, bird_data[i], "collision")

                                        
                            # log data
                           # self.log.write(str(strike_time), "AIRCRAFT", str(self.traf.id[idx]), str(self.traf.tas[idx]), \
                            #               str(self.traf.lat[idx]), str(self.traf.lon[idx]), str(self.traf.alt[idx]), str(self.traf.type[idx]), \
                             #              str(self.traf.orig[idx]), str(self.traf.dest[idx]))
                                           
                         # write: str(strike_time), aircraft, bird --> header true/false?



                        # store the aircraft id's as well
                        # even if an aircraft has more than one strike: we only want to store it's id once
                        # np.in1d: is arg1 in arg2?
                        new_id_hit_ac = id_hit_ac[np.where(np.in1d( id_hit_ac, self.traf.nr_strikes, invert = True))]        
                        self.traf.nr_strikes = np.append(self.traf.nr_strikes, new_id_hit_ac)
                        #print "traf_strikes", self.traf.nr_strikes

                    # log data
                        

                        self.log.save(self.birds.filename2save) 





        
    
        return 



    # format input for calculation
    # hint: name the reshapes differently oooooooor make an individual module
    # individual module might have adavantages as there are inputs from traf. and from birds.
    # height and radius of aircraft: store in input_files or find ways to get it via other parameters
    def reshape(self):


        # birds are the columns, aircraft are the rows
        lat_birds = self.birds.lat.reshape((len(self.birds.lat),1))
        lon_birds = self.birds.lon.reshape((len(self.birds.lon),1))
        alt_birds = self.birds.alt.reshape((len(self.birds.alt),1))

        
        lat_aircraft = self.traf.lat.reshape((1,len(self.traf.lat)))
        lon_aircraft = self.traf.lon.reshape((1,len(self.traf.lon)))
        alt_aircraft = self.traf.alt.reshape((1,len(self.traf.alt)))        
        
        
        
        return lat_birds, lon_birds, alt_birds, lat_aircraft, lon_aircraft, alt_aircraft
        
        
    # use the haversine formula to calculate the distance between birds and ac    
    # input is already in radians
    def distance(self, lat_birds, lon_birds, lat_ac, lon_ac):


        
        a = np.sin((lat_birds-lat_ac)/2)*np.sin((lat_birds-lat_ac)/2) + \
            np.cos(lat_birds)*np.cos(lat_ac)*np.sin((lon_birds-lon_ac)/2)*np.sin((lon_birds-lon_ac)/2)
   
        c= 2*np.arctan2(np.sqrt(a), np.sqrt(1-a))
        distance= earth_radius*c # 6317000m corresponds to the earth radius

        
        return distance

    def bearing(self, lat1, lon1, lat2, lon2):
    
        deltal = lon2-lon1
    
    # calculate runway bearing
        bearing = np.arctan2(np.sin(deltal)*np.cos(lat2), (np.cos(lat1)*np.sin(lat2)-
                np.sin(lat1)*np.cos(lat2)*np.cos(deltal)))
        
        # normalize to 0-360 degrees
        bearing = (np.degrees(bearing)+360)%360
        
        return bearing


'''
cd = Conflict_Detection()

traffic_traffic = np.array([[0,0,555],
                            [0,0,2],
                            [0,0,3],
                            [0,0,4],
                            [0,0,12],
                            [0,0,6],
                            [0,0,1],
                            [0,0,13],
                            [0,0,22],
                            [0,1,10]])

flock = np.array([1,0,0,0,1,0,2,1,2,0])
flock_flag = np.array([True, False, False, False, True, False, True, True, True, False])              
bird_id = np.array([11,0,0,0,12,0,21,13,22,99])              

bird_ids_removed, non_colliding_birds = cd.conflict_detection(traffic_traffic, flock, flock_flag, bird_id)
print "still alive", non_colliding_birds
print "no more", bird_ids_removed

'''
   
