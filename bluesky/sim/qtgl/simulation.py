try:
    # Try Qt5 first
    from PyQt5.QtCore import QThread, QObject
except ImportError:
    # Else PyQt4 imports
    from PyQt4.QtCore import QThread, QObject
import time

# Local imports
from screenio import ScreenIO

from simevents import StackTextEventType, BatchEventType, BatchEvent, \
    SimStateEvent, SimQuitEventType

from ...navdb import Navdatabase
from ... import stack
from ...traf import Metric
from ... import settings
from ...tools.datafeed import Modesbeast
from ...tools import datalog
from ...tools.misc import txt2tim,tim2txt


from ...traf import Traffic
from ...traf.birds import Birds

# make sure that the program is compatible with windows and ubuntu
from sys import platform

if 'linux' in platform:
    print "linux"
    from ...traf.birds.cdbirds_ubuntu import Conflict_Detection_Birds

elif 'win' in platform:
    print "windows"
    from ...traf.birds.cdbirds_windows import Conflict_Detection_Birds

else:
    print platform, " is not supported"





import cProfile

onedayinsec = 24*3600 # [s] time of one day in seconds for clock time

class Simulation(QObject):
    # simulation modes
    init, op, hold, end = range(4)

    # =========================================================================
    # Functions
    # =========================================================================
    def __init__(self, manager):
        super(Simulation, self).__init__()
        self.manager     = manager
        self.running     = True
        self.state       = Simulation.init
        self.prevstate   = None

        # Set starting system time [milliseconds]
        self.syst        = 0.0

        # Benchmark time and timespan [seconds]
        self.bencht      = 0.0
        self.benchdt     = -1.0

        # Starting simulation time [seconds]
        self.simt        = 0.0

        # Simulation timestep [seconds]
        self.simdt       = settings.simdt

        # Simulation timestep multiplier: run sim at n x speed
        self.dtmult      = 1.0
        
        # Simulated clock time
        self.deltclock = 0.0
        self.simtclock = self.simt        

        # System timestep [milliseconds]
        self.sysdt       = int(self.simdt / self.dtmult * 1000)

        # Flag indicating running at fixed rate or fast time
        self.ffmode      = False
        self.ffstop      = None

        # If available, name of the currently running scenario
        self.scenname    = 'Untitled'

        # Simulation objects
        self.navdb       = Navdatabase('global')
        self.screenio    = ScreenIO(self, manager)
        self.traf        = Traffic(self.navdb)
        self.birds       = Birds()
        self.cdbirds     = Conflict_Detection_Birds(self.traf, self.birds)

        # Additional modules
        self.metric      = Metric()
        self.beastfeed   = Modesbeast(self.traf)

        # Initialize the stack module once
        stack.init(self, self.traf, self.birds, self.screenio)

    def doWork(self):
        self.syst  = int(time.time() * 1000.0)
        self.fixdt = self.simdt

        while self.running:
            # Update screen logic
            self.screenio.update()

            # Update the Mode-S beast parsing
            self.beastfeed.update()

            # Simulation starts as soon as there is traffic, or pending commands
            if self.state == Simulation.init:
                if self.traf.ntraf > 0 or len(stack.get_scendata()[0]) > 0:
                    self.start()
                    if self.benchdt > 0.0:
                        self.fastforward(self.benchdt)
                        self.bencht = time.time()

            if self.state == Simulation.op:
                stack.checkfile(self.simt)

            # Always update stack
            stack.process(self, self.traf, self.screenio)

            if self.state == Simulation.op:

                self.traf.update(self.simt, self.simdt)

                # update bird info
                #cProfile.runctx("self.birds.update(self.simt)",globals(),locals())
                self.birds.update(self.simt)                
                

                # check for bird strikes
                self.cdbirds.conflict_detection(self.simt)
                

                
                ##### birds update

                # Update metrics
                self.metric.update(self)

                # Update log
                datalog.update(self.simt)

                # Update time for the next timestep
                self.simt += self.simdt
                

            # Update clock
            self.simtclock = (self.deltclock + self.simt)%onedayinsec                
                

            # Process Qt events
            self.manager.processEvents()

            # When running at a fixed rate, or when in hold/init, increment system time with sysdt and calculate remainder to sleep
            if not self.ffmode or not self.state == Simulation.op:
                self.syst += self.sysdt
                remainder = self.syst - int(1000.0 * time.time())

                if remainder > 0:
                    QThread.msleep(remainder)
            elif self.ffstop is not None and self.simt >= self.ffstop:
                if self.benchdt > 0.0:
                    self.screenio.echo('Benchmark complete: %d samples in %.3f seconds.' % (self.screenio.samplecount, time.time() - self.bencht))
                    self.benchdt = -1.0
                    self.pause()
                else:
                    self.start()

            # Inform main of our state change
            if not self.state == self.prevstate:
                self.sendState()
                self.prevstate = self.state

    def stop(self):
        self.state   = Simulation.end
        datalog.reset()

    def start(self):
        if self.ffmode:
            self.syst = int(time.time() * 1000.0)
        self.ffmode  = False
        self.state   = Simulation.op

    def pause(self):
        self.state   = Simulation.hold

    def reset(self):
        self.simt     = 0.0
        self.deltclock = 0.0
        self.simtclock = self.simt 
        self.state    = Simulation.init
        self.ffmode   = False
        self.scenname = 'Untitled'
        self.traf.reset(self.navdb)
        self.birds.reset()
        stack.reset()
        datalog.reset()
        self.screenio.reset()
        self.cdbirds.counter_strikes = 0
        
        
        

    def quit(self):
        self.running = False

    def setDt(self, dt):
        self.simdt = abs(dt)
        self.sysdt = int(self.simdt / self.dtmult * 1000)

    def setDtMultiplier(self, mult):
        self.dtmult = mult
        self.sysdt = int(self.simdt / self.dtmult * 1000)

    def setFixdt(self, flag, nsec=None):
        if flag:
            self.fastforward(nsec)
        else:
            self.start()

    def fastforward(self, nsec=None):
        self.ffmode = True
        if nsec is not None:
            self.ffstop = self.simt + nsec
        else:
            self.ffstop = None

    def benchmark(self, fname='IC', dt=300.0):
        stack.ic(self.screenio, self, fname)
        self.bencht  = 0.0  # Start time will be set at next sim cycle
        self.benchdt = dt

    def scenarioInit(self, name):
        self.screenio.echo('Starting scenario ' + name)
        self.scenname = name

    def sendState(self):
        self.manager.sendEvent(SimStateEvent(self.state))

    def addNodes(self, count):
        self.manager.addNodes(count)

    def batch(self, filename):
        # The contents of the scenario file are meant as a batch list: send to manager and clear stack
        result = stack.openfile(filename)
        scentime, scencmd = stack.get_scendata()
        if result is True:
            print "we have scens"
            self.manager.sendEvent(BatchEvent(scentime, scencmd))
        self.reset()
        return result




    def event(self, event):
        # Keep track of event processing
        event_processed = False

        if event.type() == StackTextEventType:
            # We received a single stack command. Add it to the existing stack
            stack.stack(event.cmdtext)
            event_processed = True

        elif event.type() == BatchEventType:
            # We are in a batch simulation, and received an entire scenario. Assign it to the stack.
            self.reset()
            stack.set_scendata(event.scentime, event.scencmd)
            self.start()
            event_processed     = True
                        
            
            
            
        elif event.type() == SimQuitEventType:
            # BlueSky is quitting
            self.quit()
        else:
            # This is either an unknown event or a gui event.
            event_processed = self.screenio.event(event)

        return event_processed

    def setclock(self,txt=""):
            """ Set simulated clock time offset"""
            if txt == "":
                pass # avoid error message, just give time
           
            elif txt.upper()== "RUN":
                self.deltclock = 0.0
                self.simtclock = self.simt
               
            elif txt.upper()== "REAL":
                self.simtclock = self.syst
                self.deltclock = self.simtclock - self.simt
           
            elif txt.replace(":","").replace(".","").isdigit():
                self.simtclock = txt2tim(txt)
                self.deltclock = self.simtclock - self.simt
            else:
                return False,"Time syntax error"
     
            return True,"Time is now "+tim2txt(self.simtclock)