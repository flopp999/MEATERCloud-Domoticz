MEATER Link Python Plugin
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
        <param field="Mode4" label="Email address" width="320px" required="true" default="user@mail.com"/>
        <param field="Mode2" label="Password" width="350px" password="true" required="true" default="Password"/>
        <param field="Mode6" label="Debug to file (MeaterLink.log)" width="70px">
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
logger = logging.getLogger("EaseeCloud")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(dir+'/EaseeCloud.log', maxBytes=1000000, backupCount=5)
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
        self.PhoneNumber = Parameters["Mode4"]
        self.Password = Parameters["Mode2"]
        self.Agree = Parameters["Mode5"]
        self.Charger = 0
        self.NoOfSystems = ""
        self.FirstRun = True

        if len(self.PhoneNumber) < 10:
            Domoticz.Log("Phone number too short")
            WriteDebug("Phone number too short")

        if len(self.Password) < 4:
            Domoticz.Log("Password too short")
            WriteDebug("Password too short")

        if os.path.isfile(dir+'/Easee.zip'):
            if 'Easee' not in Images:
                Domoticz.Image('Easee.zip').Create()
            self.ImageID = Images["Easee"].ID

        self.GetToken = Domoticz.Connection(Name="Get Token", Transport="TCP/IP", Protocol="HTTPS", Address="api.easee.cloud", Port="443")
        self.GetRefreshToken = Domoticz.Connection(Name="Get Refrsh Token", Transport="TCP/IP", Protocol="HTTPS", Address="api.easee.cloud", Port="443")
        self.GetState = Domoticz.Connection(Name="Get State", Transport="TCP/IP", Protocol="HTTPS", Address="api.easee.cloud", Port="443")
        self.GetCharger = Domoticz.Connection(Name="Get Charger", Transport="TCP/IP", Protocol="HTTPS", Address="api.easee.cloud", Port="443")
        self.GetConfig = Domoticz.Connection(Name="Get Config", Transport="TCP/IP", Protocol="HTTPS", Address="api.easee.cloud", Port="443")
        self.GetToken.Connect()

    def onDisconnect(self, Connection):
        WriteDebug("onDisconnect called for connection '"+Connection.Name+"'.")

    def onConnect(self, Connection, Status, Description):
        WriteDebug("onConnect")
        if CheckInternet() == True:
            if Connection.Name == ("Get Token"):
                WriteDebug("Get Token")
                data = "{\"userName\":\""+self.PhoneNumber+"\",\"password\":\""+self.Password+"\"}"
                headers = { 'accept': 'application/json', 'Host': 'api.easee.cloud', 'Content-Type': 'application/*+json'}
                Connection.Send({'Verb':'POST', 'URL': '/api/accounts/token', 'Headers': headers, 'Data': data})

            elif Connection.Name == ("Get Refresh Token"):
                WriteDebug("Get Refresh Token")
                data = "{\"accessToken\":\""+self.Token+"\",\"refreshToken\":\""+self.RefreshToken+"\"}"
                headers = { 'accept': 'application/json', 'Host': 'api.easee.cloud', 'Content-Type': 'application/*+json'}
                Connection.Send({'Verb':'POST', 'URL': '/api/accounts/refresh_token', 'Headers': headers, 'Data': data})

            elif Connection.Name == ("Get Charger"):
                WriteDebug("Get Charger")
                headers = { 'Host': 'api.easee.cloud', 'Authorization': 'Bearer '+self.token}
                Connection.Send({'Verb':'GET', 'URL': '/api/chargers', 'Headers': headers, 'Data': {} })

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
                self.token = Data["accessToken"]
                self.refreshtoken = Data["refreshToken"]
                self.GetToken.Disconnect()
                self.GetCharger.Connect()

            elif Connection.Name == ("Get Refresh Token"):
                Data = Data['Data'].decode('UTF-8')
                Data = json.loads(Data)
                self.token = Data["accessToken"]
                self.refreshtoken = Data["refreshToken"]
                self.GetState.Connect()

            elif Connection.Name == ("Get Charger"):
                Data = Data['Data'].decode('UTF-8')
                Data = json.loads(Data)
                self.Charger = Data[0]["id"]
                self.GetCharger.Disconnect()
                self.GetState.Connect()

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

def UpdateDevice(name, nValue, sValue):

    if name == "smartCharging":
        ID = 1
        unit = ""
    elif name == "cableLocked":
        ID = 2
        unit = ""
    elif name == "chargerOpMode":
        ID = 3
        unit = ""
    elif name == "totalPower":
        ID = 4
        unit = ""
    elif name == "sessionEnergy":
        ID = 5
        unit = "kWh"
    elif name == "energyPerHour":
        ID = 6
        unit = ""
    elif name == "wiFiRSSI":
        ID = 7
        unit = "dBm"
    elif name == "cellRSSI":
        ID = 8
        unit = "dBm"
    elif name == "localRSSI":
        unit = ""
        ID = 9
    elif name == "outputPhase":
        ID = 10
        unit = ""
    elif name == "dynamicCircuitCurrentP1":
        ID = 11
        unit = ""
    elif name == "dynamicCircuitCurrentP2":
        ID = 12
        unit = ""
    elif name == "dynamicCircuitCurrentP3":
        ID = 13
        unit = ""
    elif name == "latestPulse":
        ID = 14
        sValue = sValue.replace('Z', '')
        sValue = sValue.replace('T', ' ')
        sValue = sValue + " UTC"
        unit = ""
    elif name == "chargerFirmware":
        ID = 15
        unit = ""
    elif name == "latestFirmware":
        ID = 16
        unit = ""
    elif name == "voltage":
        ID = 17
        unit = "Volt"
    elif name == "chargerRAT":
        ID = 18
        unit = ""
    elif name == "lockCablePermanently":
        ID = 19
        unit = ""
    elif name == "inCurrentT2":
        ID = 20
        unit = ""
    elif name == "inCurrentT3":
        ID = 21
        unit = ""
    elif name == "inCurrentT4":
        ID = 22
        unit = ""
    elif name == "inCurrentT5":
        ID = 23
        unit = ""
    elif name == "outputCurrent":
        ID = 24
        unit = ""
    elif name == "isOnline":
        ID = 25
        unit = ""
    elif name == "inVoltageT1T2":
        ID = 26
        unit = "Volt"
    elif name == "inVoltageT1T3":
        ID = 27
        unit = "Volt"
    elif name == "inVoltageT1T4":
        ID = 28
        unit = "Volt"
    elif name == "inVoltageT1T5":
        ID = 29
        unit = "Volt"
    elif name == "inVoltageT2T3":
        ID = 30
        unit = "Volt"
    elif name == "inVoltageT2T4":
        ID = 31
        unit = "Volt"
    elif name == "inVoltageT2T5":
        ID = 32
        unit = "Volt"
    elif name == "inVoltageT3T4":
        ID = 33
        unit = "Volt"
    elif name == "inVoltageT3T5":
        ID = 34
        unit = "Volt"
    elif name == "inVoltageT4T5":
        ID = 35
        unit = "Volt"
    elif name == "ledMode":
        ID = 36
        unit = ""
    elif name == "cableRating":
        ID = 37
        unit = ""
    elif name == "dynamicChargerCurrent":
        ID = 38
        unit = ""
    elif name == "circuitTotalAllocatedPhaseConductorCurrentL1":
        ID = 39
        unit = ""
    elif name == "circuitTotalAllocatedPhaseConductorCurrentL2":
        ID = 40
        unit = ""
    elif name == "circuitTotalAllocatedPhaseConductorCurrentL3":
        ID = 41
        unit = ""
    elif name == "circuitTotalPhaseConductorCurrentL1":
        ID = 42
        unit = "A"
    elif name == "circuitTotalPhaseConductorCurrentL2":
        ID = 43
        unit = "A"
    elif name == "circuitTotalPhaseConductorCurrentL3":
        ID = 44
        unit = "A"
    elif name == "reasonForNoCurrent":
        ID = 45
        unit = ""
    elif name == "wiFiAPEnabled":
        ID = 46
        unit = ""
    elif name == "lifetimeEnergy":
        ID = 47
        unit = "kWh"
    elif name == "offlineMaxCircuitCurrentP1":
        ID = 48
        unit = ""
    elif name == "offlineMaxCircuitCurrentP2":
        ID = 49
        unit = ""
    elif name == "offlineMaxCircuitCurrentP3":
        ID = 50
        unit = ""
    elif name == "errorCode":
        ID = 51
        unit = ""
    elif name == "fatalErrorCode":
        ID = 52
        unit = ""
    elif name == "errors":
        ID = 53
        unit = ""
    elif name == "isEnabled":
        ID = 54
        unit = ""
    elif name == "lockCablePermanently":
        ID = 55
        unit = ""
    elif name == "authorizationRequired":
        ID = 56
        unit = ""
    elif name == "remoteStartRequired":
        ID = 57
        unit = ""
    elif name == "smartButtonEnabled":
        ID = 58
        unit = ""
    elif name == "wiFiSSID":
        ID = 59
        unit = ""
    elif name == "detectedPowerGridType":
        ID = 60
        unit = ""
    elif name == "offlineChargingMode":
        ID = 61
        unit = ""
    elif name == "circuitMaxCurrentP1":
        ID = 62
        unit = ""
    elif name == "circuitMaxCurrentP2":
        ID = 63
        unit = ""
    elif name == "circuitMaxCurrentP3":
        ID = 64
        unit = ""
    elif name == "enableIdleCurrent":
        ID = 65
        unit = ""
    elif name == "limitToSinglePhaseCharging":
        ID = 66
        unit = ""
    elif name == "phaseMode":
        ID = 67
        unit = ""
    elif name == "localNodeType":
        ID = 68
        unit = ""
    elif name == "localAuthorizationRequired":
        ID = 69
        unit = ""
    elif name == "localRadioChannel":
        ID = 70
        unit = ""
    elif name == "localShortAddress":
        ID = 71
        unit = ""
    elif name == "localParentAddrOrNumOfNodes":
        ID = 72
        unit = ""
    elif name == "localPreAuthorizeEnabled":
        ID = 73
        unit = ""
    elif name == "localAuthorizeOfflineEnabled":
        ID = 74
        unit = ""
    elif name == "allowOfflineTxForUnknownId":
        ID = 75
        unit = ""
    elif name == "maxChargerCurrent":
        ID = 76
        unit = ""
    elif name == "ledStripBrightness":
        ID = 77
        unit = ""
    elif name == "chargingSchedule":
        ID = 78
        unit = ""
    elif name == "eqAvailableCurrentP1":
        ID = 79
        unit = ""
    elif name == "eqAvailableCurrentP2":
        ID = 80
        unit = ""
    elif name == "eqAvailableCurrentP3":
        ID = 81
        unit = ""
    elif name == "deratedCurrent":
        ID = 82
        unit = ""
    elif name == "deratingActive":
        ID = 83
        unit = ""

    else:
        Domoticz.Error(str(name))
        return

    if (ID in Devices):
        if (Devices[ID].sValue != sValue):
            Devices[ID].Update(nValue, str(sValue))

    if (ID not in Devices):
        if sValue == "-32768":
            Used = 0
        else:
            Used = 1
        if ID == 14 or ID == 59:
            Domoticz.Device(Name=name, Unit=ID, TypeName="Text", Used=1).Create()

        else:
            Domoticz.Device(Name=name, Unit=ID, TypeName="Custom", Options={"Custom": "0;"+unit}, Used=Used, Description="ParameterID=\nDesignation=").Create()


def CheckInternet():
    WriteDebug("Entered CheckInternet")
    try:
        WriteDebug("Ping")
        requests.get(url='https://api.easee.cloud/', timeout=2)
        WriteDebug("Internet is OK")
        return True
    except:
        if _plugin.GetToken.Connected() or _plugin.GetToken.Connecting():
            _plugin.GetToken.Disconnect()
        if _plugin.GetState.Connected() or _plugin.GetState.Connecting():
            _plugin.GetState.Disconnect()
        if _plugin.GetConfig.Connected() or _plugin.GetConfig.Connecting():
            _plugin.GetConfig.Disconnect()
        if _plugin.GetRefreshToken.Connected() or _plugin.GetRefreshToken.Connecting():
            _plugin.GetRefreshToken.Disconnect()
        if _plugin.GetCharger.Connected() or _plugin.GetCharger.Connecting():
            _plugin.GetCharger.Disconnect()

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
