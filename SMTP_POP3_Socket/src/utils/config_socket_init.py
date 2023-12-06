import json, os, re, socket

class GeneralConfig:
    def __init__(self):
        self.configs = dict()
        self.configs["autoload"] = 0
    
    def toObject(self):
        return self.config
    
    def addConfig(self, key, value):
        email_regex_pattern = r"^\S+@(\S+)+\.\S+"
        if (key == "username"):
            self.configs[key] = value
            return True
        if (key == "password"):
            self.configs[key] = value
            return True
        if (key == "email_address"):
            if not re.match(email_regex_pattern, value):
                return False
            else:
                self.configs[key] = value
                return True
        if (key == "server"):
            self.configs[key] = value
            return True
        if (key == "smtp_port" or key == "pop3_port"):
            try:
                port = int(value)
                self.configs[key] = port
                return True
            except:
                return False #non-int port
        if (key == "autoload"):
            try:
                time = int(value)
                if (time < 0):
                    raise RuntimeError("Autoload time mustn't below 0\n")
                self.configs[key] = time
                return True
            except:
                return False #non-int or negative autoload time

        return False
    
    def toJSON(self, jsonFile):
        try:
            with open(jsonFile, 'w+') as writeJSON:
                json.dump(self.configs, writeJSON)
            return True
        except:
            return False

def readConfig(configFile):
    try:
        configObj = GeneralConfig()
        with open(configFile, 'r') as readConfig:
            json_str = readConfig.read()
            configs = json.loads(json_str)
        for config in configs:
             configObj.addConfig(config, configs.get(config))
        return configObj
    except:
        return None

def initSocket(configObj, isSending=True):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if isSending == True:
            s.connect((configObj.configs["server"], configObj.configs["smtp_port"]))           
        else:
            s.connect((configObj.configs["server"], configObj.configs["pop3_port"]))
        return s
    except:
        return None