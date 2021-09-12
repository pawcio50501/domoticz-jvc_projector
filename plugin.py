#           Python Plugin for Domoticz
#
#
#           Author: pawcio, 2021
#           1.0.0:  initial release
#       


# Below is what will be displayed in Domoticz GUI under HW
#
"""
<plugin key="JVCProjector" name="JVC Projector" author="pawcio" version="1.0.0" wikilink="no" externallink="https://github.com/pawcio50501/domoticz-jvc_projector">
    <params>
        <param field="Address" label="IP Address" width="200px" required="true" default="192.168.1.86"/>
        <param field="Port" label="Port" width="40px" required="true" default="20554"/>
      
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal"  default="True" />
            </options>
        </param>
    </params>
</plugin>
"""
#
# Main Import
import Domoticz
from enum import Enum

class Commands(Enum):
    # power commands
    power_on = b"\x21\x89\x01\x50\x57\x31\x0A"
    power_off = b"\x21\x89\x01\x50\x57\x30\x0A"

    # lens memory commands
    memory1 = b"\x21\x89\x01\x49\x4E\x4D\x4C\x30\x0A"
    memory2 = b"\x21\x89\x01\x49\x4E\x4D\x4C\x31\x0A"
    memory3 = b"\x21\x89\x01\x49\x4E\x4D\x4C\x32\x0A"
    memory4 = b"\x21\x89\x01\x49\x4E\x4D\x4C\x33\x0A"
    memory5 = b"\x21\x89\x01\x49\x4E\x4D\x4C\x34\x0A"

    # input commands
    hdmi1 = b"\x21\x89\x01\x49\x50\x36\x0A"
    hdmi2 = b"\x21\x89\x01\x49\x50\x37\x0A"

    # power status query commands
    power_status   = b"\x3F\x89\x01\x50\x57\x0A"
    current_output = b"\x3F\x89\x01\x49\x50\x0A"
    
    # picture mode commands
    pm_cinema = b"\x21\x89\x01\x50\x4D\x50\x4D\x30\x31\x0A"
    pm_hdr = b"\x21\x89\x01\x50\x4D\x50\x4D\x30\x34\x0A"
    pm_natural = b"\x21\x89\x01\x50\x4D\x50\x4D\x30\x33\x0A"
    pm_film = b"\x21\x89\x01\x50\x4D\x50\x4D\x30\x30\x0A"
    pm_THX = b"\x21\x89\x01\x50\x4D\x50\x4D\x30\x36\x0A"
    pm_user1 = b"\x21\x89\x01\x50\x4D\x50\x4D\x30\x43\x0A"
    pm_user2 = b"\x21\x89\x01\x50\x4D\x50\x4D\x30\x44\x0A"
    pm_user3 = b"\x21\x89\x01\x50\x4D\x50\x4D\x30\x45\x0A"
    pm_user4 = b"\x21\x89\x01\x50\x4D\x50\x4D\x30\x46\x0A"
    pm_user5 = b"\x21\x89\x01\x50\x4D\x50\x4D\x31\x30\x0A"
    pm_user6 = b"\x21\x89\x01\x50\x4D\x50\x4D\x31\x31\x0A"
    pm_hlg = b"\x21\x89\x01\x50\x4D\x50\x4D\x31\x34\x0A"

    # low latency enable/disable
    pm_low_latency_enable = b"\x21\x89\x01\x50\x4D\x4C\x4C\x31\x0A"
    pm_low_latency_disable = b"\x21\x89\x01\x50\x4D\x4C\x4C\x30\x0A"


class PowerStates(Enum):
    standby   = b"\x40\x89\x01\x50\x57\x30\x0A"
    cooling   = b"\x40\x89\x01\x50\x57\x32\x0A"
    emergency = b"\x40\x89\x01\x50\x57\x34\x0A"

    # on some projectors like the DLA-X5900, the status
    # is returned as the "reserved" on below when the
    # projector lamp is warming up and "lamp_on" when
    # the lamp is on
    lamp_on  = b"\x40\x89\x01\x50\x57\x31\x0A"
    reserved = b"\x40\x89\x01\x50\x57\x33\x0A"


class ACKs(Enum):
    power_ack = b"\x06\x89\x01\x50\x57\x0A"
    input_ack = b"\x06\x89\x01\x49\x50\x0A"


class BasePlugin:
          
    conn = None
    commands = []
    
    def onStart(self):
        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging(1)
            # DumpConfigToLog()

        if (len(Devices) == 0):

            Options = {"LevelActions": "||",
                       "LevelNames": "Off|Turn Off|Turn On",
                       "LevelOffHidden": "true",
                       "SelectorStyle": "0"
                       }
            Domoticz.Device(Name="Source", Unit=1, TypeName="Selector Switch", Switchtype=18,
                            Image=9,
                            Options=Options).Create()
            Domoticz.Log("Devices created.")

        # Enable heartbeat
        # Domoticz.Heartbeat(10)
        
        return True

    def addCommand(self, data):
        JVC_REQ = b'PJREQ'
        self.commands.append(data)

        if self.conn == None:
            self.commands.insert(0, (JVC_REQ, False))
            self.handleConnect()
        else:        
            if len(self.commands) == 1: # start sending process with first command, than it will be handled directly by sending process.
                #send commands
                self.sendCommand(data)
        
    def sendCommand(self, data):

        self.conn.Send(data) 
        
        if Parameters["Mode6"] == "Debug":        
            Domoticz.Log("Send data: " + str(data))
    
    def onConnect(self, Connection, Status, Description):
        if (Connection == self.conn):
            if (Status == 0):
                if Parameters["Mode6"] == "Debug":
                    Domoticz.Log("Connected successfully to: "+Connection.Address)
            else:
                Domoticz.Log("Failed to connect ("+str(Status)+") to: "+Parameters["Address"]+" with error: "+Description)
                #remove all commands from the list
                self.commands.clear()
        else:
            Domoticz.Log("Failed to connect ("+str(Status)+") to: "+Parameters["Address"]+" with error: "+Description)


    # executed each time we click on device thru domoticz GUI
    def onCommand(self, Unit, Command, Level, Hue):
        if Parameters["Mode6"] == "Debug":
            Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

        val = ''
        
        if "Set Level" == Command:
            if 10 == Level:     #off
                val = Commands.power_off.value
            elif 20 == Level:   #on
                val = Commands.power_on.value
            else:
                return False

        data = (val, False)
        Domoticz.Log("data: " + str(data))
        self.addCommand(data)
            
        return True

    def onMessage(self, Connection, Data):
        Domoticz.Log("onMessage called: " + str(Data))
        if Parameters["Mode6"] == "Debug":
            Domoticz.Log("onMessage called: " + str(Data))
        
        JVC_GREETING = b'PJ_OK'
        JVC_ACK = b'PJACK'
        ACK_LEN = 6
        dataToProcess = ''
        
        values = {item.name:item.value for item in ACKs if item.value == Data[:6]}

        if Data == JVC_GREETING:
            Domoticz.Log("Got greeting")
            self.sendCommand(self.commands[0][0])
            return;
        elif Data == JVC_ACK:
            Domoticz.Log("Got ack")
        elif values:
            Domoticz.Log("ack name: " + ACKs(Data[:ACK_LEN]).name)
            if False == self.commands[0][1] or len(Data) > ACK_LEN:
                # got full response
                dataToProcess = Data[ACK_LEN:]
            else:
                # wait for data response...
                return
        else:
            # command response? Let's check it
            dataToProcess = Data

        powerState = {item.name:item.value for item in PowerStates if item.value == dataToProcess}
        if powerState:
            Domoticz.Log("power state: " + PowerStates(dataToProcess).name + ", data len: " + str(len(Data)))
            
        # todo... rest of possible responses
        del self.commands[0]
            
        while self.commands:
            self.sendCommand(self.commands[0][0])
            if False == self.commands[0][1]:
                # no ack for this command
                del self.commands[0]
            else:
                break
        
        if len(self.commands) == 0:
            self.conn.Disconnect()
            self.conn = None

        return


    def onDisconnect(self, Connection):
        if Parameters["Mode6"] == "Debug":
            Domoticz.Log("Device has disconnected")
        self.conn = None
        self.commands.clear()
        
        return

    def handleConnect(self):
        self.conn = Domoticz.Connection(Name="Projector", Transport="TCP/IP", Protocol="None", Address=Parameters["Address"], Port=Parameters["Port"])
        self.conn.Connect()

    # def onHeartbeat(self):
        # Domoticz.Debug("Heartbeating...")
        # self.addCommand((Commands.power_status.value, True))
        
################ base on example ######################
global _plugin
_plugin = BasePlugin()


def onStart():
    global _plugin
    _plugin.onStart()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)


def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)


def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

# def onHeartbeat():
    # global _plugin
    # _plugin.onHeartbeat()
    
# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Settings count: " + str(len(Settings)))
    for x in Settings:
        Domoticz.Debug("'" + x + "':'" + str(Settings[x]) + "'")
    Domoticz.Debug("Image count: " + str(len(Images)))
    for x in Images:
        Domoticz.Debug("'" + x + "':'" + str(Images[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
        Domoticz.Debug("Device Image:     " + str(Devices[x].Image))
    return


def UpdateDevice(Unit, nValue, sValue, TimedOut):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it 
    if (Unit in Devices):
        if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue):
            Devices[Unit].Update(nValue=nValue, sValue=str(sValue), TimedOut=TimedOut)
            Domoticz.Log("Update " + str(nValue) + ":'" + str(sValue) + "' (" + Devices[Unit].Name + ")")
    return
    