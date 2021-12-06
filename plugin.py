#MEATER Link Python Plugin
#
# Author: flopp999
#
"""
<plugin key="MEATERLink" name="MEATER Link 0.1" author="flopp999" version="0.1" wikilink="https://github.com/flopp999/MEATERLink-Domoticz" externallink="https://meater.com/">
    <description>
        <h2>Support me with a coffee &<a href="https://www.buymeacoffee.com/flopp999">https://www.buymeacoffee.com/flopp999</a></h2><br/>
        <h2>https://meater.com/blog/with-meater-link-the-best-wireless-meat-thermometer-gets-even-better-thanks-to-wifi-connectivity/</h2>
        <h3>Categories that will be fetched</h3>
        <ul style="list-style-type:square">
            <li>Charger State</li>
            <li>Charger Config</li>
        </ul>
        <h3>Configuration</h3>
        <h2></h2>
        <h2></h2>
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
            Domoticz.Log("Phone number too short")
            WriteDebug("Phone number too short")

        if len(self.Password) < 4:
            Domoticz.Log("Password too short")
            WriteDebug("Password too short")

        if os.path.isfile(dir+'/MEATERLink.zip'):
            if 'MEATERLink' not in Images:
                Domoticz.Image('MEATERLink.zip').Create()
            self.ImageID = Images["MEATERLink"].ID

        self.GetToken = Domoticz.Connection(Name="Get Token", Transport="TCP/IP", Protocol="HTTPS", Address="public-api.cloud.meater.com", Port="443")
#        self.GetRefreshToken = Domoticz.Connection(Name="Get Refrsh Token", Transport="TCP/IP", Protocol="HTTPS", Address="api.easee.cloud", Port="443")
#        self.GetState = Domoticz.Connection(Name="Get State", Transport="TCP/IP", Protocol="HTTPS", Address="api.easee.cloud", Port="443")
        self.GetDevices = Domoticz.Connection(Name="Get Devices", Transport="TCP/IP", Protocol="HTTPS", Address="public-api.cloud.meater.com", Port="443")
#        self.GetConfig = Domoticz.Connection(Name="Get Config", Transport="TCP/IP", Protocol="HTTPS", Address="api.easee.cloud", Port="443")
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

            elif Connection.Name == ("Get Refresh Token"):
                WriteDebug("Get Refresh Token")
                data = "{\"accessToken\":\""+self.Token+"\",\"refreshToken\":\""+self.RefreshToken+"\"}"
                headers = { 'Host': 'api.easee.cloud', 'Content-Type': 'application/json'}
                Connection.Send({'Verb':'POST', 'URL': '/api/accounts/refresh_token', 'Headers': headers, 'Data': data})

            elif Connection.Name == ("Get Devices"):
                WriteDebug("Get Devices")
                headers = { 'Host': 'public-api.cloud.meater.com', 'Authorization': 'Bearer '+self.token}
                Connection.Send({'Verb':'GET', 'URL': '/v1/devices', 'Headers': headers, 'Data': {} })

            elif Connection.Name == ("Get State"):
                WriteDebug("Get State")
                headers = { 'Host': 'api.easee.cloud', 'Authorization': 'Bearer '+self.token}
                Connection.Send({'Verb':'GET', 'URL': '/api/chargers/'+self.Charger+'/state', 'Headers': headers, 'Data': {} })

            elif Connection.Name == ("Get Config"):
                WriteDebug("Get Config")
                headers = { 'Host': 'api.easee.cloud', 'Authorization': 'Bearer '+self.token}
                Connection.Send({'Verb':'GET', 'URL': '/api/chargers/'+self.Charger+'/config', 'Headers': headers, 'Data': {} })

    def onMessage(self, Connection, Data):
        Status = int(Data["Status"])

        if Status == 200:

            if Connection.Name == ("Get Token"):
                Data = Data['Data'].decode('UTF-8')
                Data = json.loads(Data)
#                Domoticz.Log(str(Data))
                self.token = Data["data"]["token"]
#                Domoticz.Log(str(self.token))
#                self.refreshtoken = Data["refreshToken"]
                self.GetToken.Disconnect()
                self.GetDevices.Connect()

            elif Connection.Name == ("Get Refresh Token"):
                Data = Data['Data'].decode('UTF-8')
                Data = json.loads(Data)
                self.token = Data["accessToken"]
                self.refreshtoken = Data["refreshToken"]
                self.GetState.Connect()

            elif Connection.Name == ("Get Devices"):
                Data = Data['Data'].decode('UTF-8')
                Data = json.loads(Data)
                Domoticz.Log(str(Data["data"]["devices"]))
                self.Devices = Data["data"]["devices"]
                count = 0
                while count < len(self.Devices):
                    UpdateDevice("Probe "+str(count+1)+" temp int", self.Devices[count]["temperature"]["internal"], count+1)
                    UpdateDevice("Probe "+str(count+1)+" temp amb", self.Devices[count]["temperature"]["ambient"], count+2)
                    if self.Devices[count]["cook"] == None:
                        UpdateDevice("Probe "+str(count+1)+" cook", "Not selected", count+3)
                    else:
                        UpdateDevice("Probe "+str(count+1)+" cook", self.Devices[count]["cook"]["name"], count+3)
                        UpdateDevice("Probe "+str(count+1)+" temp target", self.Devices[count]["cook"]["temperature"]["target"], count+4)
                        UpdateDevice("Probe "+str(count+1)+" time left", self.Devices[count]["cook"]["time"]["remaining"], count+5)
#                        UpdateDevice("Probe "+str(count+1)+" cook", self.Devices[count]["cook"]["name"], count+6)
                    count += 1



#                    Domoticz.Log(str(each))
#                    for each,data in each.items():
#                        Domoticz.Log(str(each))
#                        Domoticz.Log(str(data))
                self.GetDevices.Disconnect()
#                self.GetState.Connect()

            elif Connection.Name == ("Get State"):
                Data = Data['Data'].decode('UTF-8')
                Data = json.loads(Data)
                for name,value in Data.items():
                    UpdateDevice(name, 0, str(value))
                Domoticz.Log("State updated")
                self.GetState.Disconnect()
                self.GetConfig.Connect()

            elif Connection.Name == ("Get Config"):
                Data = Data['Data'].decode('UTF-8')
                Data = json.loads(Data)
                for name,value in Data.items():
                    UpdateDevice(name, 0, str(value))
                Domoticz.Log("Config updated")
                self.GetConfig.Disconnect()

        elif Status == 401:
            self.GetRefreshToken.Connect()

        else:
            WriteDebug("Status = "+str(Status))
            Domoticz.Error(str("Status "+str(Status)))
            Domoticz.Error(str(Data))
            if _plugin.GetToken.Connected():
                _plugin.GetToken.Disconnect()
            if _plugin.GetState.Connected():
                _plugin.GetState.Disconnect()

    def onHeartbeat(self):
        self.Count += 1
        if self.Count == 12:
            self.GetToken.Connect()
            self.Count = 0

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def UpdateDevice(name, sValue, ID):

#    else:
#        Domoticz.Error(str(name))
#        return

    if (ID in Devices):
        if (Devices[ID].sValue != sValue):
            Devices[ID].Update(0, str(sValue))

    if (ID not in Devices):
        if sValue == "-32768":
            Used = 0
        else:
            Used = 1
        if ID == 3 or ID == 13:
            Domoticz.Device(Name=name, Unit=ID, TypeName="Text", Used=1).Create()
        if ID == 5 or ID == 15:
            Domoticz.Device(Name=name, Unit=ID, TypeName="Text", Used=1).Create()
        else:
            Domoticz.Device(Name=name, Unit=ID, TypeName="Temperature", Used=Used, Description="ParameterID=\nDesignation=").Create()
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
#        if _plugin.GetState.Connected() or _plugin.GetState.Connecting():
#            _plugin.GetState.Disconnect()
#        if _plugin.GetConfig.Connected() or _plugin.GetConfig.Connecting():
#            _plugin.GetConfig.Disconnect()
#        if _plugin.GetRefreshToken.Connected() or _plugin.GetRefreshToken.Connecting():
#            _plugin.GetRefreshToken.Disconnect()
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
