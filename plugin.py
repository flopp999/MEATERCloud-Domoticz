# MEATER Link Python Plugin
#
# Author: flopp999
#
"""
<plugin key="MEATERLink" name="MEATER Link 0.15" author="flopp999" version="0.15" wikilink="https://github.com/flopp999/MEATERLink-Domoticz" externallink="https://meater.com/">
    <description>
        <h2>Support me with a coffee &<a href="https://www.buymeacoffee.com/flopp999">https://www.buymeacoffee.com/flopp999</a></h2><br/>
        <h2>https://meater.com/blog/with-meater-link-the-best-wireless-meat-thermometer-gets-even-better-thanks-to-wifi-connectivity/</h2>
    </description>
    <params>
        <param field="Mode1" label="Email address" width="320px" required="true" default="user@mail.com"/>
        <param field="Mode2" label="Password" width="350px" password="true" required="true" default="Password"/>
        <param field="Mode6" label="Debug to file (MEATERLink.log)" width="70px">
            <options>
                <option label="Yes" value="Yes" />
                <option label="No" value="No" />
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz

Package = True

try:
    import requests, json, os, logging
except ImportError as e:
    Package = False

try:
    from logging.handlers import RotatingFileHandler
except ImportError as e:
    Package = False

try:
    from datetime import datetime
except ImportError as e:
    Package = False

dir = os.path.dirname(os.path.realpath(__file__))
logger = logging.getLogger("MEATERLink")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(dir+'/MEATERLink.log', maxBytes=1000000, backupCount=5)
logger.addHandler(handler)

class BasePlugin:
    enabled = False

    def __init__(self):
        self.token = ''
        self.loop = 0
        self.Count = 5
        return

    def onStart(self):
        WriteDebug("===onStart===")
        self.Email = Parameters["Mode1"]
        self.Password = Parameters["Mode2"]
        self.Charger = 0
        self.NoOfSystems = ""
        self.FirstRun = True

        if len(self.Email) < 10:
            Domoticz.Log("Email address too short")
            WriteDebug("Email address too short")

        if len(self.Password) < 4:
            Domoticz.Log("Password too short")
            WriteDebug("Password too short")

        if os.path.isfile(dir+'/MEATERLink.zip'):
            if 'MEATERLink' not in Images:
                Domoticz.Image('MEATERLink.zip').Create()
            self.ImageID = Images["MEATERLink"].ID
        if os.path.isfile(dir+'/MEATERLinkBeef.zip'):
            if 'MEATERLinkBeef' not in Images:
                Domoticz.Image('MEATERLinkBeef.zip').Create()
            self.ImageIDBeef = Images["MEATERLinkBeef"].ID

        self.GetToken = Domoticz.Connection(Name="Get Token", Transport="TCP/IP", Protocol="HTTPS", Address="public-api.cloud.meater.com", Port="443")
        self.GetDevices = Domoticz.Connection(Name="Get Devices", Transport="TCP/IP", Protocol="HTTPS", Address="public-api.cloud.meater.com", Port="443")
        self.GetToken.Connect()

    def onDisconnect(self, Connection):
        WriteDebug("onDisconnect called for connection '"+Connection.Name+"'.")

    def onConnect(self, Connection, Status, Description):
        WriteDebug("onConnect")
        if CheckInternet() == True:
            if Connection.Name == ("Get Token"):
                WriteDebug("Get Token")
                data = "{\"email\":\""+self.Email+"\",\"password\":\""+self.Password+"\"}"
                headers = { 'accept': 'application/json', 'Host': 'public-api.cloud.meater.com', 'Content-Type': 'application/json'}
                Connection.Send({'Verb':'POST', 'URL': '/v1/login', 'Headers': headers, 'Data': data})

            elif Connection.Name == ("Get Devices"):
                WriteDebug("Get Devices")
                headers = { 'Host': 'public-api.cloud.meater.com', 'Authorization': 'Bearer '+self.token}
                Connection.Send({'Verb':'GET', 'URL': '/v1/devices', 'Headers': headers, 'Data': {} })

    def onMessage(self, Connection, Data):
        Status = int(Data["Status"])

        if Status == 200:

            if Connection.Name == ("Get Token"):
                Data = Data['Data'].decode('UTF-8')
                Data = json.loads(Data)
                self.token = Data["data"]["token"]
                self.GetToken.Disconnect()
                self.GetDevices.Connect()

            elif Connection.Name == ("Get Devices"):
                Data = Data['Data'].decode('UTF-8')
                Data = json.loads(Data)
#                Domoticz.Log(str(Data["data"]["devices"]))
                self.Devices = Data["data"]["devices"]
                count = 0
                while count < len(self.Devices):
                    UpdateDevice("Probe "+str(count+1)+" temp int", self.Devices[count]["temperature"]["internal"], count+1, self.ImageID)
                    UpdateDevice("Probe "+str(count+1)+" temp amb", self.Devices[count]["temperature"]["ambient"], count+2, self.ImageID)
                    if self.Devices[count]["cook"] == None:
                        UpdateDevice("Probe "+str(count+1)+" cook", "Not selected", count+3, self.ImageID)
                    elif self.Devices[count]["cook"]["name"] == "Tomahawk Steak":
                            UpdateDevice("Probe "+str(count+1)+" temp int", self.Devices[count]["temperature"]["internal"], count+1, self.ImageIDBeef)
                            UpdateDevice("Probe "+str(count+1)+" temp amb", self.Devices[count]["temperature"]["ambient"], count+2, self.ImageIDBeef)
                            UpdateDevice("Probe "+str(count+1)+" cook", self.Devices[count]["cook"]["name"], count+3, self.ImageIDBeef)
                            UpdateDevice("Probe "+str(count+1)+" temp target", self.Devices[count]["cook"]["temperature"]["target"], count+4, self.ImageIDBeef)
                            UpdateDevice("Probe "+str(count+1)+" time left", self.Devices[count]["cook"]["time"]["remaining"], count+5, self.ImageIDBeef)
                    else:
                        Domoticz.Error("Please create an issue at github and write this error. Missing "+str(self.Devices[count]["cook"]["name"]))
                    count += 1
                self.GetDevices.Disconnect()

        else:
            WriteDebug("Status = "+str(Status))
            Domoticz.Error(str("Status "+str(Status)))
            Domoticz.Error(str(Data))
            if _plugin.GetToken.Connected():
                _plugin.GetToken.Disconnect()
            if _plugin.GetDevices.Connected():
                _plugin.GetDevices.Disconnect()

    def onHeartbeat(self):
        self.Count += 1
        if self.Count == 6 :
            self.GetToken.Connect()
            self.Count = 0

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def UpdateDevice(name, sValue, ID, ImageID):

    if (ID in Devices):
        if (Devices[ID].sValue != sValue):
            Devices[ID].Update(0, str(sValue), Image=int(ImageID))

    if (ID not in Devices):
        if sValue == "-32768":
            Used = 0
        else:
            Used = 1
        if ID == 3 or ID == 13 or ID == 5 or ID == 15:
            Domoticz.Device(Name=name, Unit=ID, Image=int(ImageID), TypeName="Text", Used=1).Create()
        else:
            Domoticz.Device(Name=name, Unit=ID, Image=int(ImageID), TypeName="Temperature", Used=Used, Description="ParameterID=\nDesignation=").Create()
        Devices[ID].Update(0, str(sValue), Name=name)

def CheckInternet():
    WriteDebug("Entered CheckInternet")
    try:
        WriteDebug("Ping")
        requests.get(url='https://cloud.meater.com/', timeout=2)
        WriteDebug("Internet is OK")
        return True
    except:
        if _plugin.GetToken.Connected() or _plugin.GetToken.Connecting():
            _plugin.GetToken.Disconnect()
        if _plugin.GetDevices.Connected() or _plugin.GetDevices.Connecting():
            _plugin.GetDevices.Disconnect()

        WriteDebug("Internet is not available")
        return False

def WriteDebug(text):
    if Parameters["Mode6"] == "Yes":
        timenow = (datetime.now())
        logger.info(str(timenow)+" "+text)

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onMessage(Connection, Data):
    _plugin.onMessage(Connection, Data)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return
