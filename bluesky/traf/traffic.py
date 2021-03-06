import numpy as np
from math import *
from random import random, randint
from ..tools import datalog
from ..tools import geo
from ..tools.aero import fpm, kts, ft, nm, g0, tas2eas, tas2mach, tas2cas, mach2tas,  \
                         mach2cas, cas2tas, cas2mach, Rearth, vatmos, \
                         vcas2tas, vtas2cas, vtas2mach, vcas2mach, vmach2tas
from ..tools.misc import degto180

from windsim import WindSim

from route import Route
from params import Trails
from adsbmodel import ADSBModel
#from asas import ASAS
#from birds import Birds
#from birds.cdbirds import Conflict_Detection_Birds
from .. import settings

try:
    if settings.performance_model == 'bluesky':
        from perf import Perf

    elif settings.performance_model == 'bada':
        from perfbada import PerfBADA as Perf

except ImportError as err:

    print 'Falling back to BlueSky performance model'
    from perf import Perf


class Traffic:
    """
    Traffic class definition    : Traffic data
    Methods:
        Traffic()            :  constructor
        reset()              :  Reset traffic database w.r.t a/c data
        create(acid,actype,aclat,aclon,achdg,acalt,acspd) : create aircraft
        delete(acid)         : delete an aircraft from traffic data
        deletall()           : delete all traffic
        update(sim)          : do a numerical integration step
        id2idx(name)         : return index in traffic database of given call sign
        selhdg(i,hdg)        : set autopilot heading and activate heading select mode
        selspd(i,spd)        : set autopilot CAS/Mach and activate heading select mode
        engchange(i,engtype) : change engine type of an aircraft
        changeTrailColor(color,idx)     : change colour of trail of aircraft idx
        setNoise(A)          : Add turbulence
    Members: see create
    Created by  : Jacco M. Hoekstra
    """

    def __init__(self, navdb):     
        
        
        # ASAS object
        #self.asas = ASAS()
        self.wind = WindSim()
        


        # All traffic data is initialized in the reset function
        self.reset(navdb)

    def reset(self, navdb):
        #  model-specific parameters.
        # Default: BlueSky internal performance model.
        # Insert your BADA files to the folder "BlueSky/data/coefficients/BADA"
        # for working with EUROCONTROL`s Base of Aircraft Data revision 3.12

        self.perf = Perf(self)

        self.ntraf = 0

        # Traffic list & arrays definition

        # !!!IMPORTANT NOTE!!!
        # Any variables added here should also be added in the Traffic
        # methods self.create() (append) and self.delete() (delete)
        # which can be found directly below __init__

        # Traffic basic flight data

        # Traffic basic flight data
        self.id      = []  # identifier (string)
        self.type    = []  # aircaft type (string)
        self.lat     = np.array([])  # latitude [deg]
        self.lon     = np.array([])  # longitude [deg]
        self.hdg     = np.array([])  # traffic heading [deg]
        self.trk     = np.array([])  # track angle [deg]
        self.tas     = np.array([])  # true airspeed [m/s]
        self.gs      = np.array([])  # ground speed [m/s]
        self.gsnorth = np.array([])  # ground speed [m/s]
        self.gseast  = np.array([])  # ground speed [m/s]
        self.cas     = np.array([])  # calibrated airspeed [m/s]
        self.M       = np.array([])  # mach number
        self.alt     = np.array([])  # altitude [m]
        self.fll     = np.array([])  # flight level [ft/100]
        self.vs      = np.array([])  # vertical speed [m/s]
        self.p       = np.array([])  # atmospheric air pressure [N/m2]
        self.rho     = np.array([])  # atmospheric air density [kg/m3]
        self.Temp    = np.array([])  # atmospheric air temperature [K]
        self.dtemp   = np.array([])  # delta t for non-ISA conditions

        # Traffic performance data
        self.avsdef = np.array([])  # [m/s]default vertical speed of autopilot
        self.aphi   = np.array([])  # [rad] bank angle setting of autopilot
        self.ax     = np.array([])  # [m/s2] absolute value of longitudinal accelleration
        self.bank   = np.array([])  # nominal bank angle, [radian]
        self.bphase = np.array([])  # standard bank angles per phase
        self.hdgsel = np.array([])  # determines whether aircraft is turning

        # Help variables to save computation time
        self.coslat = np.array([])  # Cosine of latitude for flat-earth aproximations

        # Crossover altitude
        self.abco   = np.array([])
        self.belco  = np.array([])

        # Traffic autopilot settings
        self.atrk   = []  # selected track angle [deg]
        self.aspd   = []  # selected spd(CAS) [m/s]
        self.aptas  = []  # just for initializing
        self.ama    = []  # selected spd above crossover altitude (Mach) [-]
        self.apalt  = []  # selected alt[m]
        self.apfll  = []  # selected fl [ft/100]
        self.avs    = []  # selected vertical speed [m/s]

        # limit settings
        self.limspd      = []  # limit speed
        self.limspd_flag = [] # flag for limit spd - we have to test for max and min
        self.limalt      = []  # limit altitude
        self.limvs       = []  # limit vertical speed due to thrust limitation
        self.limvs_flag  = []

        # Traffic navigation information
        self.orig   = []  # Four letter code of origin airport
        self.dest   = []  # Four letter code of destination airport

        # LNAV route navigation
        self.swlnav = np.array([])  # Lateral (HDG) based on nav?
        self.swvnav = np.array([])  # Vertical/longitudinal (ALT+SPD) based on nav info

        self.actwplat  = np.array([])  # Active WP latitude
        self.actwplon  = np.array([])  # Active WP longitude
        self.actwpalt  = np.array([])  # Active WP altitude to arrive at
        self.actwpspd  = np.array([])  # Active WP speed
        self.actwpturn = np.array([])  # Distance when to turn to next waypoint
        self.actwpflyby = np.array([])  # Distance when to turn to next waypoint
        self.next_qdr  = np.array([])  # bearing next leg

        # VNAV variablescruise level
        self.crzalt  = np.array([])    # Cruise altitude[m]
        self.dist2vs = np.array([])    # Distance to start V/S of VANAV
        self.actwpvs = np.array([])    # Actual V/S to use

        # Route info
        self.route = []
        
        # Desired aircraft states
        self.desalt     = np.array([])  # desired altitude [m]
        self.deshdg     = np.array([])  # desired heading [deg]
        self.destrk     = np.array([])  # desired track angle [deg]
        self.desvs      = np.array([])  # desired vertical speed [m/s]
        self.desspd     = np.array([])  # desired speed [m/s]

        # Display information on label
        self.label      = []  # Text and bitmap of traffic label
        self.trailcol   = []  # Trail color: default 'Blue'

        # Transmitted data to other aircraft due to truncated effect
        self.adsbtime   = np.array([])
        self.adsblat    = np.array([])
        self.adsblon    = np.array([])
        self.adsbalt    = np.array([])
        self.adsbtrk    = np.array([])
        self.adsbtas    = np.array([])
        self.adsbgs     = np.array([])
        self.adsbvs     = np.array([])
        
        # bird strike info
        self.nr_strikes = np.array([]) # counter for strikes
        self.hit_ac     = []           # aircraft with a strike  

        #-----------------------------------------------------------------------------
        # Not per aircraft data

        # Scheduling of FMS and ASAS
        self.t0fms = -999.  # last time fms was called
        self.dtfms = 1.01  # interval for fms

        # Flight performance scheduling
        self.perfdt = 0.1           # [s] update interval of performance limits
        self.perft0 = -self.perfdt  # [s] last time checked (in terms of simt)
        self.warned2 = False        # Flag: Did we warn for default engine parameters yet?

        # ADS-B transmission-receiver model
        self.adsb = ADSBModel(self)

        # Import navigation data base
        self.navdb  = navdb

        # Traffic area: delete traffic when it leaves this area (so not when outside)
        self.swarea     = False
        self.arealat0   = 0.0  # [deg] lower latitude defining area
        self.arealat1   = 0.0  # [deg] upper latitude defining area
        self.arealon0   = 0.0  # [deg] lower longitude defining area
        self.arealon1   = 0.0  # [deg] upper longitude defining area
        self.areafloor  = -999999.0  # [m] Delete when descending through this h
        self.areatop    = 100000000.0 # [m]
        self.areadt     = 5.0  # [s] frequency of area check (simtime)
        self.areat0     = -100.  # last time checked
        self.arearadius = 100.0  # [NM] radius of experiment area if it is a circle
        


        self.inside = []
        self.fir_circle_point = (0.0, 0.0)
        self.fir_circle_radius = 1.0

        # Taxi switch
        self.swtaxi = False  # Default OFF: delete traffic below 1500 ft

        # Research Area ("Square" for Square, "Circle" for Circle area)
        self.area = ""

        # Bread crumbs for trails
        self.lastlat  = []
        self.lastlon  = []
        self.lasttim  = []
        self.trails   = Trails()
        self.swtrails = False  # Default switched off

        # Noise (turbulence, ADBS-transmission noise, ADSB-truncated effect)
        self.setNoise(False)

        self.eps = np.array([])

        #self.asas.reset()

        self.wind.clear()

        # Make a list of variables that can be logged
        logvars = [
            # Traffic basic flight data
            'id', 'type', 'lat', 'lon', 'trk', 'tas', 'gs', 'cas', 'M', 'alt', 'fll', 'vs', 'p', 'rho', 'Temp',

            # Crossover altitude
            'abco', 'belco',

            # Traffic autopilot settings
            'ahdg', 'aspd', 'aptas', 'ama', 'apalt', 'apfll', 'avs',

            # limit settings
            'limspd', 'limalt', 'limvs', 

            # Traffic navigation information
            'orig', 'dest',

            # LNAV route navigation
            'swlnav', 'swvnav', 'actwplat', 'actwplon', 'actwpalt', 'actwpspd', 'actwpturn', 'actwpflyby',

            # VNAV variables cruise level
            'crzalt', 'dist2vs', 'actwpvs',

            # Route info
            # 'route',

            # Transmitted data to other aircraft due to truncated effect
            'adsbtime', 'adsblat', 'adsblon', 'adsbalt', 'adsbtrk', 'adsbtas', 'adsbgs', 'adsbvs'
        ]
        snapheader = '# SNAPLOG logfile.'
        datalog.createPeriodicLog('SNAPLOG', snapheader, settings.snapdt, (self, logvars))

        # Temporarily make the other default periodic logs here as well
        instheader = '# INSTLOG logfile.'
        datalog.createPeriodicLog('INSTLOG', instheader, settings.instdt)
        skyheader = '# SKYLOG logfile.'
        datalog.createPeriodicLog('SKYLOG', skyheader, settings.skydt)

    def mcreate(self, count, actype=None, alt=None, spd=None, dest=None, area=None):
        """ Create multiple random aircraft in a specified area """
        idbase = chr(randint(65, 90)) + chr(randint(65, 90))
        if actype is None:
            actype = 'B744'

        for i in xrange(count):
            acid  = idbase + '%05d' % i
            aclat = random() * (area[1] - area[0]) + area[0]
            aclon = random() * (area[3] - area[2]) + area[2]
            achdg = float(randint(1, 360))
            acalt = (randint(2000, 39000) * ft) if alt is None else alt
            acspd = (randint(250, 450) * kts) if spd is None else spd

            self.create(acid, actype, aclat, aclon, achdg, acalt, acspd)

    def create(self, acid, actype, aclat, aclon, achdg, acalt, casmach):
        """Create an aircraft"""
        # Check if not already exist
        if self.id.count(acid.upper()) > 0:
            return False, acid + " already exists."  # already exists do nothing

        # Increase number of aircraft
        self.ntraf = self.ntraf + 1

        # Convert speed
        if 0.1 < casmach < 1.0 :
            acspd = mach2tas(casmach, acalt)
        else:
            acspd = cas2tas(casmach, acalt)

        # Process input
        self.id.append(acid.upper())
        self.type.append(actype)
        self.lat   = np.append(self.lat, aclat)
        self.lon   = np.append(self.lon, aclon)
        self.hdg   = np.append(self.hdg, achdg)
        self.alt   = np.append(self.alt, acalt)
        self.fll   = np.append(self.fll, (acalt) / (100 * ft))
        self.vs    = np.append(self.vs, 0.)
        c_temp, c_rho, c_p = vatmos(acalt)
        self.p     = np.append(self.p, c_p)
        self.rho   = np.append(self.rho, c_rho)
        self.Temp  = np.append(self.Temp, c_temp)
        self.dtemp = np.append(self.dtemp, 0)  # at the moment just ISA conditions
        self.tas   = np.append(self.tas, acspd)
        self.cas   = np.append(self.cas, tas2cas(acspd, acalt))
        self.M     = np.append(self.M, tas2mach(acspd, acalt))
        
        # Using heading,TAS and wind vector, compute track angle and ground spd
        tasnorth = self.tas[-1]*cos(radians(self.hdg[-1]))
        taseast  = self.tas[-1]*sin(radians(self.hdg[-1]))       
        if self.wind.winddim>0:
            vnwnd,vewnd     = self.wind.getdata(self.lat[-1],self.lon[-1],self.alt[-1])
            self.gsnorth    = np.append(self.gsnorth,tasnorth + vnwnd)
            self.gseast     = np.append(self.gseast, taseast  + vewnd)
            self.trk        = np.append(self.trk,np.degrees(np.arctan2(self.gseast[-1],self.gsnorth[-1])))
            self.gs         = np.append(self.gs,np.sqrt(self.gsnorth[-1]*self.gsnorth[-1] + self.gseast[-1]*self.gseast[-1])) 

        else:
            self.trk     = np.append(self.trk, achdg)
            self.gs      = np.append(self.gs, acspd)
            self.gsnorth = np.append(self.gsnorth,tasnorth)
            self.gseast  = np.append(self.gseast,taseast)

        # AC is initialized with neutral max bank angle
        self.bank = np.append(self.bank, radians(25.))
        if self.ntraf < 2:
            self.bphase = np.deg2rad(np.array([15, 35, 35, 35, 15, 45]))
        self.hdgsel = np.append(self.hdgsel, False)

        #------------------------------Performance data--------------------------------
        # Type specific data
        #(temporarily default values)
        self.avsdef = np.append(self.avsdef, 1500. * fpm)  # default vertical speed of autopilot
        self.aphi   = np.append(self.aphi, radians(25.))  # bank angle setting of autopilot
        self.ax     = np.append(self.ax, kts)  # absolute value of longitudinal accelleration

        # Crossover altitude
        self.abco   = np.append(self.abco, 0)
        self.belco  = np.append(self.belco, 1)

        # performance data
        self.perf.create(actype)

        # Traffic autopilot settings: hdg[deg], spd (CAS,m/s), alt[m], vspd[m/s]
        self.atrk  = np.append(self.atrk, self.trk[-1])  # selected heading [deg]
        self.aspd  = np.append(self.aspd, tas2cas(acspd, acalt))  # selected spd(cas) [m/s]
        self.aptas = np.append(self.aptas, acspd)  # [m/s]
        self.ama   = np.append(self.ama, 0.)  # selected spd above crossover (Mach) [-]
        self.apalt = np.append(self.apalt, acalt)  # selected alt[m]
        self.apfll = np.append(self.apfll, (acalt / 100))  # selected fl[ft/100]
        self.avs   = np.append(self.avs, 0.)  # selected vertical speed [m/s]

        # limit settings: initialize with -999 / False
        self.limspd      = np.append(self.limspd, -999.)
        self.limspd_flag = np.append (self.limspd_flag, False)
        self.limalt      = np.append(self.limalt, -999.)
        
        # limit vertical speed: initialization is -999, as 0 is used for ac taking off
        self.limvs      = np.append(self.limvs, -9999.)
        self.limvs_flag = np.append(self.limvs_flag, True)

        # Help variables to save computation time
        self.coslat = np.append(self.coslat, cos(radians(aclat)))  # Cosine of latitude for flat-earth aproximations

        # Traffic navigation information
        self.dest.append("")
        self.orig.append("")

        # LNAV route navigation
        self.swlnav = np.append(self.swlnav, False)  # Lateral (HDG) based on nav
        self.swvnav = np.append(self.swvnav, False)  # Vertical/longitudinal (ALT+SPD) based on nav info

        self.actwplat   = np.append(self.actwplat, 89.99)  # Active WP latitude
        self.actwplon   = np.append(self.actwplon, 0.0)   # Active WP longitude
        self.actwpalt   = np.append(self.actwpalt, 0.0)   # Active WP altitude
        self.actwpspd   = np.append(self.actwpspd, -999.)   # Active WP speed
        self.actwpturn  = np.append(self.actwpturn, 1.0)   # Distance to active waypoint where to turn
        self.actwpflyby = np.append(self.actwpflyby, 1.0)   # Flyby/fly-over switch
        self.next_qdr  = np.append(self.next_qdr, -999.0)    # bearing next leg

        # VNAV cruise level
        self.crzalt = np.append(self.crzalt, -999.)    # Cruise altitude[m] <0=None
        self.dist2vs = np.append(self.dist2vs, -999.)  # Distance to start V/S of VANAV
        self.actwpvs = np.append(self.actwpvs, 0.0)    # Actual V/S to use then

        # Route info
        self.route.append(Route(self.navdb))  # create empty route connected with nav databse

        eas = tas2eas(acspd, acalt)
        
        # Desired aircraft states   
        self.desalt  = np.append(self.desalt, acalt)
        self.desvs   = np.append(self.desvs, 0.0)
        self.desspd  = np.append(self.desspd, eas)
        self.deshdg  = np.append(self.deshdg, achdg)
        self.destrk  = np.append(self.destrk, self.trk[-1])

        # Area variable set to False to avoid deletion upon creation outside
        self.inside.append(False)

        # Display information on label
        self.label.append(['', '', '', 0])

        # Bread crumbs for trails
        self.trailcol.append(self.trails.defcolor)
        self.lastlat = np.append(self.lastlat, aclat)
        self.lastlon = np.append(self.lastlon, aclon)
        self.lasttim = np.append(self.lasttim, 0.0)

        # Transmitted data to other aircraft due to truncated effect
        self.adsbtime   = np.append(self.adsbtime, np.random.rand(self.trunctime))
        self.adsblat    = np.append(self.adsblat, aclat)
        self.adsblon    = np.append(self.adsblon, aclon)
        self.adsbalt    = np.append(self.adsbalt, acalt)
        self.adsbtrk    = np.append(self.adsbtrk, self.trk[-1])
        self.adsbtas    = np.append(self.adsbtas, acspd)
        self.adsbgs     = np.append(self.adsbgs, acspd)
        self.adsbvs     = np.append(self.adsbvs, 0.)

        self.eps        = np.append(self.eps, 0.01)

        #self.asas.create(self.trk[-1], acspd, acalt)
        
        # bird strike info

        self.hit_ac.append([])


        return True

    def delete(self, acid):
        """Delete an aircraft"""

        # Look up index of aircraft
        idx = self.id2idx(acid)

        # Do nothing if not found
        if idx < 0:
            return False

        # remove from birdstrike list --> no, they should be saved and stored (check for errors)
       # if self.id[idx] in self.nr_strikes:
        #    self.nr_strikes = np.delete(self.nr_strikes, np.where(self.nr_strikes ==self.id[idx]))
        
        # and remove the index
        del self.hit_ac[idx] 



        del self.id[idx]
        del self.type[idx]

        # Traffic basic data
        self.lat     = np.delete(self.lat, idx)
        self.lon     = np.delete(self.lon, idx)
        self.hdg     = np.delete(self.hdg, idx)
        self.trk     = np.delete(self.trk, idx)
        self.alt     = np.delete(self.alt, idx)
        self.fll     = np.delete(self.fll, idx)
        self.vs      = np.delete(self.vs, idx)
        self.tas     = np.delete(self.tas, idx)
        self.gs      = np.delete(self.gs, idx)
        self.gsnorth = np.delete(self.gsnorth, idx)
        self.gseast  = np.delete(self.gseast, idx)
        self.cas     = np.delete(self.cas, idx)
        self.M       = np.delete(self.M, idx)

        self.p      = np.delete(self.p, idx)
        self.rho    = np.delete(self.rho, idx)
        self.Temp   = np.delete(self.Temp, idx)
        self.dtemp  = np.delete(self.dtemp, idx)
        self.hdgsel = np.delete(self.hdgsel, idx)
        self.bank   = np.delete(self.bank, idx)

        # Crossover altitude
        self.abco   = np.delete(self.abco, idx)
        self.belco  = np.delete(self.belco, idx)

        # Type specific data (temporarily default values)
        self.avsdef = np.delete(self.avsdef, idx)
        self.aphi   = np.delete(self.aphi, idx)
        self.ax     = np.delete(self.ax, idx)

        # performance data
        self.perf.delete(idx)

        # Traffic autopilot settings: hdg[deg], spd (CAS,m/s), alt[m], vspd[m/s]
        self.atrk   = np.delete(self.atrk, idx)
        self.aspd   = np.delete(self.aspd, idx)
        self.ama    = np.delete(self.ama, idx)
        self.aptas  = np.delete(self.aptas, idx)
        self.apalt  = np.delete(self.apalt, idx)
        self.apfll  = np.delete(self.apfll, idx)
        self.avs    = np.delete(self.avs, idx)

        # limit settings
        self.limspd      = np.delete(self.limspd, idx)
        self.limspd_flag = np.delete(self.limspd_flag, idx)
        self.limalt      = np.delete(self.limalt, idx)
        self.limvs       = np.delete(self.limvs, idx)
        self.limvs_flag  = np.delete(self.limvs_flag, idx)

        # Help variables to save computation time
        self.coslat = np.delete(self.coslat, idx)  # Cosine of latitude for flat-earth aproximations

        # Traffic navigation variables
        del self.dest[idx]
        del self.orig[idx]

        self.swlnav = np.delete(self.swlnav, idx)
        self.swvnav = np.delete(self.swvnav, idx)

        self.actwplat   = np.delete(self.actwplat, idx)
        self.actwplon   = np.delete(self.actwplon, idx)
        self.actwpalt   = np.delete(self.actwpalt, idx)
        self.actwpspd   = np.delete(self.actwpspd, idx)
        self.actwpturn  = np.delete(self.actwpturn, idx)
        self.actwpflyby = np.delete(self.actwpflyby, idx)
        self.next_qdr   = np.delete(self.next_qdr, idx)

        # VNAV cruise level
        self.crzalt    = np.delete(self.crzalt, idx)
        self.dist2vs   = np.delete(self.dist2vs, idx)    # Distance to start V/S of VANAV
        self.actwpvs   = np.delete(self.actwpvs, idx)    # Actual V/S to use

        # Route info
        del self.route[idx]
        
        # Desired aircraft states
        self.desalt     = np.delete(self.desalt, idx)
        self.desvs      = np.delete(self.desvs, idx)
        self.desspd     = np.delete(self.desspd, idx)
        self.deshdg     = np.delete(self.deshdg, idx)
        self.destrk     = np.delete(self.destrk, idx)

        # Metrics, area
        del self.inside[idx]

        # Traffic display data: label
        del self.label[idx]

        # Delete bread crumb data
        self.lastlat = np.delete(self.lastlat, idx)
        self.lastlon = np.delete(self.lastlon, idx)
        self.lasttim = np.delete(self.lasttim, idx)
        del self.trailcol[idx]

        # Transmitted data to other aircraft due to truncated effect
        self.adsbtime = np.delete(self.adsbtime, idx)
        self.adsblat  = np.delete(self.adsblat, idx)
        self.adsblon  = np.delete(self.adsblon, idx)
        self.adsbalt  = np.delete(self.adsbalt, idx)
        self.adsbtrk  = np.delete(self.adsbtrk, idx)
        self.adsbtas  = np.delete(self.adsbtas, idx)
        self.adsbgs   = np.delete(self.adsbgs, idx)
        self.adsbvs   = np.delete(self.adsbvs, idx)

        # Decrease number fo aircraft
        self.ntraf = self.ntraf - 1

        self.eps = np.delete(self.eps, idx)

        #self.asas.delete(idx)
        return True

    def update(self, simt, simdt):
        # Update only necessary if there is traffic
        if self.ntraf == 0:
            return

        #---------------- Atmosphere ----------------
        self.p, self.rho, self.Temp = vatmos(self.alt)

        ###############################################################################
        # Debugging: add 10000 random aircraft
        #            if simt>1.0 and self.ntraf<1000:
        #                for i in range(10000):
        #                   acid="KL"+str(i)
        #                   aclat = random.random()*180.-90.
        #                   aclon = random.random()*360.-180.
        #                   achdg = random.random()*360.
        #                   acalt = (random.random()*18000.+2000.)*0.3048
        #                   self.create(acid,'B747',aclat,aclon,achdg,acalt,350.)
        #
        #################################################################################

        #-------------------- ADSB update: --------------------

        self.adsbtime = self.adsbtime + simdt
        if self.ADSBtrunc:
            ADSB_update = np.where(self.adsbtime > self.trunctime)
        else:
            ADSB_update = range(self.ntraf)

        for i in ADSB_update:
            self.adsbtime[i] = self.adsbtime[i] - self.trunctime
            self.adsblat[i]  = self.lat[i]
            self.adsblon[i]  = self.lon[i]
            self.adsbalt[i]  = self.alt[i]
            self.adsbtrk[i]  = self.trk[i]
            self.adsbtas[i]  = self.tas[i]
            self.adsbgs[i]   = self.gs[i]
            self.adsbvs[i]   = self.vs[i]

        # New version ADSB Model
        self.adsb.update(simt)

        #------------------- ASAS update: ---------------------
        # Reset label because of colour change
        # Save old result

        #iconf0 = np.array(self.asas.iconf)

        #self.asas.update(self, simt)

        # chnged = np.where(iconf0 != np.array(self.asas.iconf))[0]
        #if settings.gui == "pygame":
           # for i in range(self.ntraf):
            #    if np.any(iconf0[i] != self.asas.iconf[i]):
             #       self.label[i] = [" ", " ", "", " "]
#
        #-----------------  FMS GUIDANCE & NAVIGATION  ------------------
        # Scheduling: when dt has passed or restart:
        if self.t0fms + self.dtfms < simt or simt < self.t0fms:
            self.t0fms = simt

            # FMS LNAV mode:
            qdr, dist = geo.qdrdist(self.lat, self.lon, self.actwplat, self.actwplon)  # [deg][nm])
            
            # turn distance, turn radius

            # Calculate distance before waypoint where to start the turn
            # Turn radius:      R = V2 tan phi / g
            # Distance to turn: wpturn = R * tan (1/2 delhdg) but max 4 times radius
            # using default bank angle per flight phase
            # bank angle already is in radians
            turnrad = self.tas*self.tas / np.maximum(self.eps,np.tan(self.bank)*g0*nm) # [nm]
    
            next_qdr = np.where(self.next_qdr < -900., qdr, self.next_qdr)

            # distance to turn initialisation point
            self.actwpturn = np.maximum(0.1, np.abs(turnrad*np.tan(np.radians(0.5*degto180(np.abs(qdr -    \
                 next_qdr))))))

            # Check whether shift based dist [nm] is required, set closer than WP turn distanc
            iwpclose = np.where(self.swlnav * (dist < self.actwpturn))[0]

            # Shift waypoints for aircraft i where necessary
            for i in iwpclose:

                # Get next wp (lnavon = False if no more waypoints)
                lat, lon, alt, spd, xtoalt, toalt, lnavon, flyby, self.next_qdr[i] =  \
                       self.route[i].getnextwp(self, i)  # note: xtoalt,toalt in [m]
                       
                # End of route/no more waypoints: switch off LNAV
                if not lnavon:
                    self.swlnav[i] = False  # Drop LNAV at end of route

                # In case of no LNAV, do not allow VNAV mode on it sown
                if not self.swlnav[i]:
                    self.swvnav[i] = False

                self.actwplat[i]   = lat
                self.actwplon[i]   = lon
                self.actwpflyby[i] = int(flyby)  # 1.0 in case of fly by, els fly over

                # User has entered an altitude for this waypoint
                if alt >= 0.:
                    self.actwpalt[i] = alt


                # VNAV = FMS ALT/SPD mode
                # calculated altitude is available and active
                if toalt  >= 0. and self.swvnav[i]:  # somewhere there is an altitude constraint ahead


                    # Descent VNAV mode (T/D logic)
                    if self.alt[i] > toalt + 10. * ft:


                        #Steepness dh/dx in [m/m], for now 1:3 rule of thumb
                        steepness = 3000. * ft / (10. * nm)

                        #Calculate max allowed altitude at next wp (above toalt)
                        self.actwpalt[i] = toalt + xtoalt * steepness



                        # Dist to waypoint where descent should start
                        self.dist2vs[i] = (self.alt[i] - self.actwpalt[i]) / steepness

                        # Flat earth distance to next wp
                        dy = (lat - self.lat[i])
                        dx = (lon - self.lon[i]) * self.coslat[i]
                        legdist = 60. * nm * sqrt(dx * dx + dy * dy)


                        # If descent is urgent, descent with maximum steepness
                        if legdist < self.dist2vs[i]:
                            self.apalt[i] = self.actwpalt[i]  # dial in altitude of next waypoint as calculated


                            t2go         = max(0.1, legdist) / max(0.01, self.gs[i])
                            self.actwpvs[i]  = (self.actwpalt[i] - self.alt[i]) / t2go

                        else:
                            # normal case: still time till descent starts


                            # Calculate V/s using steepness,
                            # protect against zero/invalid ground speed value
                            self.actwpvs[i] = -steepness * (self.gs[i] +
                                            (self.gs[i] < 0.2 * self.tas[i]) * self.tas[i])

                    # Climb VNAV mode: climb as soon as possible (T/C logic)
                    elif self.swvnav[i] and self.alt[i] < toalt - 10. * ft:

                        self.actwpalt[i] = toalt
                        self.apalt[i]    = self.actwpalt[i]  # dial in altitude of next waypoint as calculated
                        self.dist2vs[i]  = 9999.

                    # Level leg: never start V/S
                    else:

                        self.dist2vs[i] = -999.

                #No altirude defined: never start V/S
                else:

                    self.dist2vs[i] = -999.

                # VNAV spd mode: use speed of this waypoint as commanded speed
                # while passing waypoint and save next speed for passing next wp
                if self.swvnav[i] and self.actwpspd[i] > 0.0:  # check mode and value

                    # Select CAS or Mach command by checking value of actwpspd
                    if self.actwpspd[i] < 2.0:  # Mach command
                        self.aspd[i] = mach2cas(self.actwpspd[i], self.alt[i])
                        self.ama[i]  = self.actwpspd[i]

                    else:    # CAS command
                        self.aspd[i] = self.actwpspd[i]
                        self.ama[i]  = cas2tas(spd, self.alt[i])

                if spd > 0. and self.swlnav[i] and self.swvnav[i]:  # Valid speed and LNAV and VNAV ap modes are on
                    self.actwpspd[i] = spd

                else:
                    self.actwpspd[i] = -999.


            #=============== End of Waypoint switching loop ===================

            # VNAV Guidance

            # Do VNAV start of descent check
            dy = (self.actwplat - self.lat)
            dx = (self.actwplon - self.lon) * self.coslat
            dist2wp   = 60. * nm * np.sqrt(dx * dx + dy * dy)
            steepness = 3000. * ft / (10. * nm)
            
            # VNAV logic: descend as late as possible, climb as soon as possible
            startdescent = self.swvnav * ((dist2wp < self.dist2vs)+(self.actwpalt > self.alt)) 
            
            # If not lnav:Climb/descend if doing so before lnav/vnav was switched off
            #    (because there are no more waypoints). This is needed
            #    to continue descending when you get into a conflict
            #    while descending to the destination (the last waypoint)
            #    USe 185.2 m cirlce in case turndist might be zero
            self.swvnavvs = np.where(self.swlnav, startdescent, dist <= np.maximum(185.2,self.actwpturn))            
            
            #Recalculate V/S based on current altitude and distance
            t2go = dist2wp/np.maximum(0.5,self.gs)
            self.actwpvs = (self.actwpalt-self.alt)/np.maximum(1.0,t2go)            


            self.avs  = np.where(self.swvnavvs, self.actwpvs, self.avs)            

            # VNAV AP LOGIC: descend as late as possible, climb as soon as possible
            # First term: descend when distance to next wp is descent distance
            # Second term: climb when still below altitude of next waypoint
            # Third line: climb/descend if doing so before lnav/vnav was switched off
            #               (because there are no more waypoints). This is needed
            #               to continue descending when you get into a conflict
            #               while descending to the destination (the last waypoint)
            #self.swvnavvs = self.swlnav * self.swvnav * ((dist2wp < self.dist2vs) +
            #                         (self.actwpalt > self.alt)) + \
            #                         (1 - self.swlnav) * (dist < self.actwpturn)

            #self.avs = (1-self.swvnavvs)*self.avs + self.swvnavvs*steepness*self.gs
            self.apalt = (1-self.swvnavvs)*self.apalt + self.swvnavvs*self.actwpalt   
            #self.aspd = (1-self.swvnav*self.swlnav)*self.aspd + self.swlnav*self.swvnav*self.actwpspd
           # print "aspd is", self.aspd, "actwpspd is", self.actwpspd, "LNAV on", self.swlnav, "VNAV on", self.swvnav
            # LNAV commanded track angle
            self.atrk = np.where(self.swlnav, qdr, self.atrk)







        #-------------END of FMS update -------------------
         
        # NOISE: Turbulence
        if self.turbulence:
            timescale=np.sqrt(simdt)
            trkrad=np.radians(self.trk)

            #write turbulences in array
            turb=np.array(self.standardturbulence)
            turb=np.where(turb>1e-6,turb,1e-6)

            #horizontal flight direction
            turbhf=np.random.normal(0,turb[0]*timescale,self.ntraf) #[m]

            #horizontal wing direction
            turbhw=np.random.normal(0,turb[1]*timescale,self.ntraf) #[m]

            #vertical direction
            turbalt=np.random.normal(0,turb[2]*timescale,self.ntraf) #[m]

            #lateral, longitudinal direction
            turblat=np.cos(trkrad)*turbhf-np.sin(trkrad)*turbhw #[m]
            turblon=np.sin(trkrad)*turbhf+np.cos(trkrad)*turbhw #[m]

        else:
            turbalt=np.zeros(self.ntraf) #[m]
            turblat=np.zeros(self.ntraf) #[m]
            turblon=np.zeros(self.ntraf) #[m]


        #--------- Input to Autopilot settings to follow: destination or ASAS ----------   
                
        # Below crossover altitude: CAS=const, above crossover altitude: MA = const
        self.aptas = vcas2tas(self.aspd, self.alt)*self.belco + vmach2tas(self.ama, self.alt)*self.abco
        
        # Convert the ASAS commanded speed from ground speed to TAS
        '''if self.wind.winddim>0:            
            vwn, vwe     = self.wind.getdata(self.lat,self.lon,self.alt)
            asastasnorth = self.asas.asasspd * np.cos(np.radians(self.asas.asastrk)) - vwn
            asastaseast  = self.asas.asasspd * np.sin(np.radians(self.asas.asastrk)) - vwe    
            asastas      = np.sqrt(asastasnorth*asastasnorth + asastaseast*asastaseast)
        # no wind, then ground speed = TAS
        else:
            asastas = self.asas.asasspd

        # Determine desired states from ASAS or AP. Select asas if there is a conflict AND resolution is on. 
        self.destrk = self.asas.asasactive*self.asas.asastrk + (1-self.asas.asasactive)*self.atrk
        self.desspd = self.asas.asasactive*asastas           + (1-self.asas.asasactive)*self.aptas
        self.desalt = self.asas.asasactive*self.asas.asasalt + (1-self.asas.asasactive)*self.apalt
        self.desvs  = self.asas.asasactive*self.asas.asasvsp + (1-self.asas.asasactive)*self.avs'''
        
        self.destrk = self.atrk
        self.desspd = self.aptas
        self.desalt = self.apalt
        self.desvs  = self.avs        

        # Compute the desired heading needed to compensate for the wind
        if self.wind.winddim>0:
            # Calculate wind correction 
            vwn, vwe = self.wind.getdata(self.lat,self.lon,self.alt)
            Vw       = np.sqrt(vwn*vwn + vwe*vwe)
            winddir  = np.arctan2(vwe,vwn)
            drift    = np.radians(self.destrk)-winddir #[rad]
            steer    = np.arcsin(np.minimum(1.0,np.maximum(-1.0,\
                           Vw*np.sin(drift)/np.maximum(0.001,self.tas))))
            # desired heading
            self.deshdg = (self.destrk + np.degrees(steer))%360. 
        else:
            self.deshdg = self.destrk%360.

        # check for the flight envelope
        self.delalt = self.apalt - self.alt  # [m]
        self.perf.limits()

        # Update desired sates with values within the flight envelope
        # To do: add const Mach const CAS mode
        self.desspd = np.where (self.limspd_flag, vcas2tas(self.limspd,self.alt), self.desspd )

        # Autopilot selected altitude [m]
        self.desalt = (self.limalt < -900.)*self.desalt + (self.limalt > -900.)*self.limalt


        # Autopilot selected vertical speed (V/S)
        self.desvs = (self.limvs< -9000.)*self.desvs + (self.limvs > -9000.)*self.limvs
        self.desvs = np.where(self.desvs >0.1, np.minimum(self.desvs, 10.26), self.desvs)

        # To be discussed: Following change in VNAV mode only?
        # below crossover altitude: CAS=const, above crossover altitude: MA = const
        #climb/descend above crossover: Ma = const, else CAS = const
        #ama is fixed when above crossover
        self.ama = np.where(self.abco*(self.ama == 0.), \
                                vcas2mach(self.aspd,self.alt), self.ama)

        # ama is deleted when below crossover
        self.ama = np.where(self.belco*(self.ama!=0.), 0.0, self.ama)         

        #---------- Basic Autopilot  modes ----------

        # Update TAS
        self.delspd = self.desspd - self.tas
        swspdsel = np.abs(self.delspd) > 0.001  # <1 kts = 0.514444 m/s

        # acceleration: ground /standard acceleration depending on flight phase
        ax = self.perf.acceleration(simdt)       
        self.tas = swspdsel * (self.tas + ax * np.sign(self.delspd) * simdt) \
                               + (1. - swspdsel) * self.tas

        # Speed conversions using updated TAS
        self.cas = vtas2cas(self.tas, self.alt)
        self.M   = vtas2mach(self.tas, self.alt)

        # Update performance every self.perfdt seconds
        if abs(simt - self.perft0) >= self.perfdt:               
            self.perft0 = simt            
            self.perf.perf()

        # Update altitude
        self.eps = np.array(self.ntraf * [0.01])  # almost zero for misc purposes        
        swaltsel = np.abs(self.desalt-self.alt) >      \
                  np.maximum(3.,np.abs(2. * simdt * np.abs(self.vs))) # 3.[m] = 10 [ft] eps alt   
                  
        # TO DO: ADD some vertical speed dynamics so that the desired VS can't be obtained instantly
        # if asas is not active AND VNAV is not active, then it should use the standard climb rate.
        # In this case, desvs is not considered - hence a flag is required to prevent
        # that aircraft taking off start climbing before they have reached v_2
        # if asas is active AND VNAV is not active it should use asasvs (which is desvs)
        # if asas is not active and VNAV is active desvs
        # if asas AND VNAV is active then use desvs
                  # 10.26 is 2000fpm
        self.vs = swaltsel*np.sign(self.desalt-self.alt)* \
                    ((1-self.swvnav)*np.abs(1500./60*ft)*self.limvs_flag+\
                        self.swvnav*np.abs(self.desvs))
                        
                  #((1-self.asas.asasactive)*(1-self.swvnav)*np.abs(1500./60*ft)*self.limvs_flag+\
                   #self.asas.asasactive*(1-self.swvnav)*np.abs(self.desvs)+\
                   #(1-self.asas.asasactive)*self.swvnav*np.abs(self.desvs)+\
                   #self.asas.asasactive*self.swvnav*np.abs(self.desvs))

        self.alt = swaltsel * (self.alt + self.vs * simdt) +   \
                   (1. - swaltsel) * self.desalt + turbalt


        # HDG HOLD/SEL mode: atrk = ap selected track angle
        delhdg = (self.deshdg - self.hdg + 180.) % 360 - 180.  # [deg]

        # nominal bank angles per phase from BADA 3.12
        omega = np.degrees(g0 * np.tan(self.bank) / \
                           np.maximum(self.tas, self.eps))

        self.hdgsel = np.abs(delhdg) > np.abs(2. * simdt * omega)
        self.hdg = (self.hdg + simdt * omega * self.hdgsel * np.sign(delhdg)) % 360.

        #--------- Kinematics: update lat,lon,alt ----------

        # Compute ground speed and track from heading,airspeed and wind
        if self.wind.winddim==0: # no wind
            self.gs  = self.tas
            self.gsnorth  = self.tas * np.cos(np.radians(self.hdg))
            self.gseast   = self.tas * np.sin(np.radians(self.hdg))
            self.trk = self.hdg

        else:
        # Add wind to ground speed
            tasnorth = self.tas * np.cos(np.radians(self.hdg))
            taseast  = self.tas * np.sin(np.radians(self.hdg))

            windnorth, windeast = self.wind.getdata(self.lat, self.lon, self.alt)

            self.gsnorth  = tasnorth + windnorth
            self.gseast   = taseast  + windeast
   
            self.gs  = np.sqrt(self.gsnorth*self.gsnorth + self.gseast*self.gseast) 
            self.trk = np.degrees(np.arctan2(self.gseast, self.gsnorth))%360.

        dsnorth = simdt * self.gsnorth
        dseast = simdt * self.gseast

        self.lat = self.lat + np.degrees((dsnorth + turblat) / Rearth)

        self.coslat = np.cos(np.deg2rad(self.lat))

        self.lon = self.lon + np.degrees((dseast + turblon) / self.coslat / Rearth)

        # Update trails when switched on
        if self.swtrails:
            self.trails.update(simt, self.lat, self.lon,
                               self.lastlat, self.lastlon,
                               self.lasttim, self.id, self.trailcol)
        else:
            self.lastlat = self.lat
            self.lastlon = self.lon
            self.lasttim[:] = simt

        # ----------------AREA check----------------
        # Update area once per areadt seconds:
        if self.swarea and abs(simt - self.areat0) > self.areadt:
            # Update loop timer
            self.areat0 = simt
            # Check all aircraft
            i = 0
            while (i < self.ntraf):
                # Current status
                if self.area == "Square":
                    inside = self.arealat0 <= self.lat[i] <= self.arealat1 and \
                             self.arealon0 <= self.lon[i] <= self.arealon1 and \
                             self.areatop >= self.alt[i] >= self.areafloor
                    


                elif self.area == "Circle":

                    # delete aircraft if it is too far from the center of the circular area, or if has decended below the minimum altitude
                    distance = geo.kwikdist(self.arealat0, self.arealon0, self.lat[i], self.lon[i])  # [NM]
                    inside = distance < self.arearadius and self.areatop >= self.alt[i] >= self.areafloor

                # Compare with previous: when leaving area: delete command
                if self.inside[i] and not inside:
                    self.delete(self.id[i])


                else:
                    # Update area status
                    self.inside[i] = inside
                    i = i + 1

    #########################################################################
    #
    # birds
    #
    #########################################################################
#        self.cd_birds.conflict_detection(self, self.birds)


        return

    def id2idx(self, acid):
        """Find index of aircraft id"""
        try:
            return self.id.index(acid.upper())
        except:
            return -1

    def setTrails(self, *args):
        """ Set trails on/off, or change trail color of aircraft """
        if type(args[0]) == bool:
            # Set trails on/off
            self.swtrails = args[0]
            if len(args) > 1:
                self.trails.dt = args[1]
            if not self.swtrails:
                self.trails.clear()
        else:
            # Change trail color
            if len(args) < 2 or args[1] not in ["BLUE", "D", "YELLOW"]:
                return False, "Set aircraft trail color with: TRAIL acid BLUE/RED/YELLOW"
            self.changeTrailColor(args[1], args[0])

    def changeTrailColor(self, color, idx):
        """Change color of aircraft trail"""
        self.trailcol[idx] = self.trails.colorList[color]
        return

    def setNoise(self, noiseflag=None):
        """Noise (turbulence, ADBS-transmission noise, ADSB-truncated effect)"""

        if noiseflag is None:
            return True, "Noise is currently " + ("on" if self.noise else "off")

        self.noise              = noiseflag           # Noise/turbulence switch
        self.trunctime          = 1                   # seconds
        self.transerror         = [1, 100, 100 * ft]  # [degree,m,m] standard bearing, distance, altitude error
        self.standardturbulence = [0, 0.1, 0.1]       # m/s standard turbulence  (nonnegative)
        # in (horizontal flight direction, horizontal wing direction, vertical)

        self.turbulence     = self.noise
        self.ADSBtransnoise = self.noise
        self.ADSBtrunc      = self.noise

        return True

    def engchange(self, acid, engid):
        """Change of engines"""
        self.perf.engchange(acid, engid)
        return

    def selhdg(self, idx, hdg):  # HDG command
        """ Select heading command: HDG acid, hdg """
        
        # If there is wind, compute the corresponding track angle            
        if self.wind.winddim>0:
            tasnorth = self.tas[idx]*cos(radians(hdg))
            taseast  = self.tas[idx]*sin(radians(hdg)) 
            vnwnd,vewnd = self.wind.getdata(self.lat[idx],self.lon[idx],self.alt[idx])
            gsnorth    = tasnorth + vnwnd
            gseast     = taseast  + vewnd
            trk        = np.degrees(np.arctan2(gseast,gsnorth))
        else:             
            trk = hdg           

        self.atrk[idx]   = trk
        self.swlnav[idx] = False
        # Everything went ok!
        return True

    def selspd(self, idx, casmach):  # SPD command
        """ Select speed command: SPD acid, casmach (= CASkts/Mach) """
        # When >=1.0 it is probably CASkts else it is Mach
        if 0.1 < casmach < 1.0:
            self.aspd[idx] = mach2cas(casmach, self.alt[idx])  # Convert Mach to CAS m/s
            self.ama[idx]  = casmach
        else:
            self.aspd[idx] = casmach  # CAS m/s
            self.ama[idx]  = cas2mach(casmach, self.alt[idx])
        # Switch off VNAV: SPD command overrides
        self.swvnav[idx]   = False

        return True

    def move(self, idx, lat, lon, alt=None, hdg=None, casmach=None, vspd=None):
        self.lat[idx]      = lat
        self.lon[idx]      = lon

        if alt:
            self.alt[idx]  = alt
            self.apalt[idx] = alt

        if hdg:
            self.hdg[idx]  = hdg
            self.atrk[idx] = hdg

        if casmach:
            # Convert speed
            if 0.1 < casmach < 1.0:
                self.tas[idx]  = mach2tas(casmach, alt)
                self.aspd[idx] = mach2cas(casmach, alt)
            else:
                self.tas[idx]  = cas2tas(casmach, alt)
                self.aspd[idx] = casmach

        if vspd:
            self.vs[idx]       = vspd
            self.swvnav[idx]   = False

    def selalt(self, idx, alt, vspd=None):
        """ Select altitude command: ALT acid, alt, [vspd] """
        self.apalt[idx]    = alt
        self.apfll[idx]    = alt / (100. * ft)
        self.swvnav[idx]   = False

        # Check for optional VS argument
        if vspd:
            self.avs[idx] = vspd
        else:
            delalt        = alt - self.alt[idx]
            # Check for VS with opposite sign => use default vs
            # by setting autopilot vs to zero
            if self.avs[idx] * delalt < 0. and abs(self.avs[idx]) > 0.01:
                self.avs[idx] = 0.

    def selvspd(self, idx, vspd):
        """ Vertical speed autopilot command: VS acid vspd """
        self.avs[idx] = vspd
        # self.vs[idx] = vspd
        self.swvnav[idx] = False

    def nom(self, idx):
        """ Reset acceleration back to nominal (1 kt/s^2): NOM acid """
        self.ax[idx] = kts

    def setTaxi(self, flag):
        """ Set taxi delete flag: OFF auto deletes traffic below 1500 ft """
        self.swtaxi = flag

    def setLNAV(self, idx, flag=None):
        """ Set LNAV on or off for a specific or for all aircraft """
        if idx is None:
            # All aircraft are targeted
            self.swlnav = np.array(self.ntraf*[flag])

        elif flag is None:
            return True, (self.id[idx] + ": LNAV is " + "ON" if self.swlnav[idx] else "OFF")

        elif flag:
            route = self.route[idx]
            if route.nwp > 0:
                self.swlnav[idx] = True

                route.direct(self, idx, route.wpname[route.findact(self, idx)])
                self.next_qdr[idx] = route.getnextqdr()
            else:
                return False, ("LNAV " + self.id[idx] + ": no waypoints or destination specified")
        else:
            self.swlnav[idx] = False

    def setVNAV(self, idx, flag=None):
        """ Set VNAV on or off for a specific or for all aircraft """
        if idx is None:
            # All aircraft are targeted
            self.swvnav = np.array(self.ntraf*[flag])

        elif flag is None:
            return True, (self.id[idx] + ": VNAV is " + "ON" if self.swvnav[idx] else "OFF")

        elif flag:
            if not self.swlnav[idx]:
                return False, (self.id[idx] + ": VNAV ON requires LNAV to be ON")

            route = self.route[idx]
            if route.nwp > 0:
                self.swvnav[idx] = True

                route.direct(self, idx, route.wpname[route.findact(self, idx)])
                self.next_qdr[idx] = route.getnextqdr()
            else:
                return False, ("VNAV " + self.id[idx] + ": no waypoints or destination specified")
        else:
            self.swvnav[idx] = False

    def setDestOrig(self, cmd, idx, *args):
        
        if len(args) == 0:
            if cmd == 'DEST':
                return True, ('DEST ' + self.id[idx] + ': ' + self.dest[idx])
            else:
                return True, ('ORIG ' + self.id[idx] + ': ' + self.orig[idx])

        route = self.route[idx]

        if len(args) == 1:

            name = args[0]


            apidx = self.navdb.getapidx(name)
            if apidx < 0:
                return False, (cmd + ": Airport " + name + " not found.")
            lat = self.navdb.aplat[apidx]
            lon = self.navdb.aplon[apidx]

            
        elif len(args)==2:
            lat, lon = args
            name = self.id[idx]+cmd


        elif len(args)==3:
            name, lat, lon = args

            if name=="":
                name = self.id[idx]+cmd


        else:
            return False,cmd+" needs lat/lon or airport"
            

        if cmd == "DEST":
            self.dest[idx] = name

            
            iwp = route.addwpt(self, idx, name, route.dest,
                               lat, lon, 0.0, self.cas[idx])
            

            # If only waypoint: activate
            if (iwp == 0) or (self.orig[idx] != "" and route.nwp == 2):

                self.actwplat[idx] = route.wplat[iwp]
                self.actwplon[idx] = route.wplon[iwp]
                self.actwpalt[idx] = route.wpalt[iwp]
                self.actwpspd[idx] = route.wpspd[iwp]

                self.swlnav[idx] = True
                route.iactwp = iwp

            # If not found, say so
            elif iwp < 0:

                return False, (self.dest[idx] + " not found.")

        # Origin: bookkeeping only for now
        else:

            self.orig[idx] = name

            iwp = route.addwpt(self, idx, self.orig[idx], route.orig,
                               self.lat[idx], self.lon[idx], 0.0, self.cas[idx])
               
            if iwp < 0:

                return False, (self.orig[idx] + " not found.")

    def acinfo(self, acid):
        idx           = self.id.index(acid)
        actype        = self.type[idx]
        lat, lon      = self.lat[idx], self.lon[idx]
        alt, hdg,trk  = self.alt[idx] / ft, self.hdg[idx], self.trk[idx]
        cas           = self.cas[idx] / kts
        tas           = self.tas[idx] / kts
        route         = self.route[idx]
        line = "Info on %s %s index = %d\n" % (acid, actype, idx) \
             + "Pos = %.2f, %.2f. Spd: %d kts CAS, %d kts TAS\n" % (lat, lon, cas, tas) \
             + "Alt = %d ft, Hdg = %d, Trk = %d\n" % (alt, hdg, trk)
        if self.swlnav[idx] and route.nwp > 0 and route.iactwp >= 0:
            if self.swvnav[idx]:
                line += "VNAV, "
            line += "LNAV to " + route.wpname[route.iactwp] + "\n"
        if self.orig[idx] != "" or self.dest[idx] != "":
            line += "Flying"
            if self.orig[idx] != "":
                line += " from " + self.orig[idx]
            if self.dest[idx] != "":
                line += " to " + self.dest[idx]

        return line

    def setArea(self, scr, metric, *args):

        if args[0] == 'OFF':
            self.swarea = False
            self.area   = ""
            scr.objappend(2, "AREA", None)  # delete square areas
            scr.objappend(3, "AREA", None)  # delete circle areas
            return True

        if type(args[0]) == float and len(args) >= 4:

            # This is a square area
            self.arealat0 = min(args[0], args[2])
            self.arealat1 = max(args[0], args[2])
            self.arealon0 = min(args[1], args[3])
            self.arealon1 = max(args[1], args[3])

            if len(args) == 5:

                self.areafloor = args[4] * ft
            elif len(args) ==6:

                self.areafloor = args[4] * ft
                self.areatop = args[5] * ft
            else:
                self.areafloor = -9999999.
                self.areatop   = 100000000.

            self.area = "Square"
            self.swarea = True
            scr.objappend(2, "AREA", [args[0], args[1], args[2], args[3]])

            # Avoid mass delete due to redefinition of area
            self.inside = self.ntraf * [False]
            return True
        elif args[0] == "FIR" and len(args) <= 4:
            for i in range(0, len(self.navdb.fir)):
                if args[1] == self.navdb.fir[i][0]:
                    break
            if args[1] != self.navdb.fir[i][0]:
                return False, "Unknown FIR, try again"

            metric.fir_number        = i
            metric.fir_circle_point  = metric.metric_Area.FIR_circle(self.navdb, metric.fir_number)
            metric.fir_circle_radius = float(args[1])

            if len(args) == 3:
                self.areafloor = args[2] * ft
            elif len(args) ==4:
                self.areafloor = args[2] * ft
                self.areatop = args[3] * ft
            else:
                self.areafloor = -9999999.
                self.areatop   = 100000000.
                
            self.area   = "Circle"
            self.swarea = True
            self.inside = self.ntraf * [False]
            scr.objappend(3, "AREA", [metric.fir_circle_point[0] , metric.fir_circle_point[1], metric.fir_circle_radius])
            return True
        elif args[0] == "CIRCLE" and len(args) in [4, 5, 6]:
            # draw circular experiment area
            self.arealat0 = args[1]    # Latitude of circle center [deg]
            self.arealon0 = args[2]    # Longitude of circle center [deg]
            self.arearadius = args[3]  # Radius of circle Center [NM]

            # Deleting traffic flying out of experiment area
            self.area = "Circle"
            self.swarea = True

            if len(args) == 5:
                self.areafloor = args[4] * ft  # [m]
                
            elif len(args) ==6:
                self.areafloor = args[4] * ft  # [m]
                self.areatop = args[5] * ft  # [m]
            else:
                self.areafloor = -9999999.  # [m]
                self.areatop = 10000000000. #[m]

            # draw the circular experiment area on the radar gui
            scr.objappend(3, "AREA", [self.arealat0, self.arealon0, self.arearadius])

            # Avoid mass delete due to redefinition of area
            self.inside = self.ntraf * [False]

            return True

        return False
