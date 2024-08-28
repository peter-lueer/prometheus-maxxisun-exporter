import argparse
from configparser import ConfigParser
import datetime
import json
import logging
import os
import prometheus_client
import requests
import signal
import sys
import time


logging.basicConfig(level=logging.INFO, format='%(asctime)-15s :: %(levelname)8s :: %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

class Exporter(object):
    """
    Prometheus Exporter for Maxxisun API
    """
    def __init__(self, args):
        """
        initializes the exporter

        :param args: the argparse.Args
        """
        
        self.__metric_port = int(args.metric_port)
        self.__collect_interval_seconds = int(args.collect_interval_seconds)
        self.__collect_interval_seconds_Backup = int(args.collect_interval_seconds)
        self.__collect_Error = 0
        self.__collect_Max_Connect_Error = 5
        self.__log_level = int(os.getenv('LOG_LEVEL',args.log_level))
        
        if self.__log_level == 10:
            logger.debug("Set Logging to DEBUG")
            logger.setLevel(logging.DEBUG)
        elif self.__log_level == 20:
            logger.info("Set Logging to INFO")
            logger.setLevel(logging.INFO)
        elif self.__log_level == 30:
            logger.warning("Set Logging to WARNING")
            logger.setLevel(logging.WARNING)
        elif self.__log_level == 40:
            logger.error("Set Logging to ERROR")
            logger.setLevel(logging.ERROR)
        elif self.__log_level == 50:
            logger.critical("Set Logging to CRITICAL")
            logger.setLevel(logging.CRITICAL)
        
        logger.info(
            "exposing metrics on port '{}'".format(self.__metric_port)
        )

        # #Delete old unhealthy file
        # file_path = os.path.dirname(__file__) + '/'
        # self.__healthy_file_path = file_path + "maybe_unhealthy"
        # if os.path.exists(self.__healthy_file_path):
        #     os.remove(self.__healthy_file_path)

        self.__init_client(args.config_file, args.api_url, args.maxxisun_email, args.maxxisun_ccu)
        self.__init_metrics()
        try:
            prometheus_client.start_http_server(self.__metric_port)
        except Exception as e:
            logger.critical(
                "starting the http server on port '{}' failed with: {}".format(self.__metric_port, str(e))
            )
            sys.exit(1)

    
    def __init_client(self, config_file, api_url, maxxisun_email, maxxisun_ccu):

        try:
            if api_url != None and maxxisun_email != None and maxxisun_ccu != None:
                logger.info("use commandline parameters")
                self.api_url = api_url
                self.maxxisun_email = maxxisun_email
                self.maxxisun_ccu = maxxisun_ccu
            elif os.getenv('api_url',None) != None or (os.getenv('maxxisun_email',None) != None and os.getenv('maxxisun_ccu', None) != None):
                logger.info("use environment variables")
                self.api_url = os.getenv('api_url',None)
                self.maxxisun_email = os.getenv('maxxisun_email',None)
                self.maxxisun_ccu= os.getenv('maxxisun_ccu',None)
            else:
                logger.info("use config file '{}'".format(config_file))
                configur = ConfigParser()
                configur.read(config_file)
                try:
                    self.api_url = configur.get('Maxxisun','URL')
                    self.maxxisun_email = configur.get('Maxxisun','Email')
                    self.maxxisun_ccu = configur.get('Maxxisun','CCU')
                except:
                    logger.warning(
                        "no Config-File found")
            
            self.api_auth_url = 'https://maxxisun.app:3000/api/authentication/log-in'

            if self.api_url == None or self.maxxisun_email == None or self.maxxisun_ccu == None:
                logger.error("No URL '{}' and Mail '{}' CCU '{}' Config found".format(self.api_url, self.maxxisun_email, self.maxxisun_ccu))
                sys.exit(1)

        except Exception as e:
            logger.critical(
                "Initializing failed with: {}".format(str(e))
            )
            sys.exit(1)

    def __init_metrics(self):
        namespace = 'maxxisun_api'

        self.version_info = prometheus_client.Gauge(
            name = 'version_info',
            documentation = 'Project version info',
            labelnames = ['project_version'],
            namespace = namespace
        )

        self.connected_info = prometheus_client.Gauge(
            name = 'connected',
            documentation = 'Is API is connected',
            namespace = namespace
        )

        self.metrics = {}
        
        file_path = os.path.dirname(__file__) + '/'

        objectFile = open(file_path + 'objectlist.json')
        self.objectList = json.load(objectFile)

        for data in self.objectList:
            try:
                metrics_data = self.objectList[data]
                name = metrics_data["name"]

                try:
                    documentation = metrics_data["documentation"]
                except:
                    documentation = metrics_data["name"]
                #index = self.addPrefix(data)
                try:
                    dataType = metrics_data["type"]
                except:
                    dataType = ""

                self.__add_metric(name, documentation, namespace, dataType, metrics_data)


                #print(data + "- " + self.objectList[data]["name"] + ": ")
            except Exception as ex:
                #no Name found
                name=""

    def __add_metric(self, name, documentation, namespace, dataType, metrics_data):

        if dataType == "TEMPERATURE":
            self.metrics[name] = prometheus_client.Gauge(
                name = name,
                documentation = documentation,
                namespace = namespace
            )
        elif dataType == "Number":
            self.metrics[name] = prometheus_client.Gauge(
                name = name,
                documentation = documentation,
                namespace = namespace
            )
        elif dataType == "Number_List":
            self.metrics[name] = prometheus_client.Gauge(
                name = name,
                documentation = documentation,
                namespace = namespace,
                labelnames=['Item']
            )
        elif dataType == "List":
            self.metrics[name] = prometheus_client.Info(
                name = name,
                documentation = documentation,
                namespace = namespace,
                labelnames=['Item']
            )
        elif dataType == "IO":
            self.metrics[name] = prometheus_client.Gauge(
                name = name,
                documentation = documentation,
                namespace = namespace
            )
        elif dataType == "SECONDS":
            self.metrics[name] = prometheus_client.Gauge(
                name = name,
                documentation = documentation,
                namespace = namespace
            )
        elif dataType == "TIMESTAMP":
            self.metrics[name] = prometheus_client.Gauge(
                name = name,
                documentation = documentation,
                namespace = namespace
            )
        elif dataType == "COUNTER":
            self.metrics[name] = prometheus_client.Gauge(
                name = name,
                documentation = documentation,
                namespace = namespace
            )
        elif dataType == "IP":
            #do not save IP Information
            self.metrics[name] = prometheus_client.Info(
                name = name,
                documentation = documentation,
                namespace = namespace
            )
            nothing="empty"

        elif dataType == "ENUM":
            self.metrics[name] = prometheus_client.Enum(
                name = name,
                documentation = documentation,
                namespace = namespace,
                states = metrics_data['enum']
            )
        
        else:
            self.metrics[name] = prometheus_client.Info(
                name = name,
                documentation = documentation,
                namespace = namespace
            )

    def __collect_device_info_metrics(self):
        logger.debug(
            "collect info metrics"
        )
        # general device info metric
        self.version_info.labels(
            project_version="0.5"
        ).set(1)

    def typeExists(self, listelement):
        try:
            dataType = listelement['type']
            return True
        except:
            return False
        #'type' in objectList[index]


    def isset(self, listelement):
        try:
            if listelement == {}:
                return False
            else:
                return True
        except:
            return False

    # def int2ip(self, v):
    #     part1 = v & 255
    #     part2 = ((v >> 8) & 255)
    #     part3 = ((v >> 16) & 255)
    #     part4 = ((v >> 24) & 255)
    #     return str(part4) + "." + str(part3) + "." + str(part2) + "." + str(part1)

    def addPrefix(self, index):
        result = str(index)
        while len(result) < 3 :
            result = "0" + result
        return result

    def findType(self, valueToFind):
        try:
            return self.objectList[valueToFind]["type"]
        except:
            return ""

    def getEnumDefinition(self,  objectName, enumToFind):
        result = ""
        for data in self.objectList[objectName]:
                if data['name'] == objectName:
                    try:
                        result = data['enum'][int(enumToFind)]
                        return result
                    except:
                        return ""

        return result
    
    def setMetricsValue(self, resultJsonData, prefix=None, listCount=0):

        logger.debug("Read Values")
        try:
            for dataObject in resultJsonData:
                name = dataObject
                value = resultJsonData[dataObject]

                if hasattr(resultJsonData[dataObject], "__len__") and (not isinstance(resultJsonData[dataObject], str)):
                    logger.debug("This is an Array")
                    i=0
                    for innerValue in value:
                        self.setMetricsValue(innerValue, name, i)
                        i+=1
                    if (i > 0):
                        continue
                
                
                if (prefix != None):
                    name = prefix + "_" + name

                dataType = self.findType(name)
                if dataType == "TEMPERATURE" or dataType == "ANALOG":
                    state = int(value)/10
                elif dataType == "IO":
                    state = value > 0
                elif dataType == "IP":
                    #state = self.int2ip(value)
                    self.metrics[name].info({ name : value })
                    continue
                elif dataType == "ENUM":
                    state = self.getEnumDefinition(name,value)
                    self.metrics[name].state(state)
                    continue
                elif dataType == "Number_List":
                    self.metrics[name].labels(Item=listCount).set(value)
                    continue
                elif dataType == "List":
                    self.metrics[name].labels(Item=listCount).info({ name : value } )
                    continue
                elif dataType == "":
                    self.metrics[name].info({ name : value } )
                    continue
                
                self.metrics[name].set(value)
            
        except Exception as ex:
            logger.warning("Date not saved. Error parsing data.")
            error="Set Value Error"

    def __collect_data_from_API(self):

        try:
            canConnectToAPI=False
            responseData = None
            #Check Connection to Maxxisun
            
            if (self.authToken == None):
                logger.error("No AUTH Token found")
                

            try:
                logger.debug("Check Maxxisun online")
                headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0', 'Accept':'application/json, text/plain, */*', "Authorization": 'Bearer '+ self.authToken}
                responseData = requests.get(self.api_url, headers=headers, verify=False)

                canConnectToAPI = True
                self.__collect_Error = 0
                logger.debug("API is online, lets go")
            except Exception as e: 
                logger.warning("Unable to connect to: " + str(self.api_ip) + " on Port: " + str(self.api_port))
                self.__collect_Error += 1

            if canConnectToAPI:
                self.connected_info.set(1)
                self.setMetricsValue(json.loads(responseData.text))
                logger.info("Data collected and published")
                # if os.path.exists(self.__healthy_file_path):
                #     os.remove(self.__healthy_file_path)
            else:
                #empty Power States
                self.connected_info.set(0)
                        
        except Exception as ex:
            logger.error('Failed while reading from API')
            self.__collect_Error += 1

    def collect(self):
        """
        collect discovers all devices and generates metrics
        """
        try:
            logger.info('Start collect method')

            #Collect Data from API
            self.__collect_device_info_metrics()

            self.__collect_data_from_API()
        
        except Exception as e:
            logger.warning(
                "collecting data from API failed with: {1}".format(str(e))
            )
        finally:
            if  self.__collect_Error >= self.__collect_Max_Connect_Error:
                self.__collect_Error = self.__collect_Max_Connect_Error
                logger.debug("Maybe offline - write File")
                f = open(self.__healthy_file_path, 'w')
                f.write("maybe")
                f.close()

            self.__collect_interval_seconds = self.__collect_interval_seconds_Backup * (self.__collect_Error + 1)
            logger.info('waiting {}s before next collection cycle'.format(self.__collect_interval_seconds))
            time.sleep(self.__collect_interval_seconds)
    
    def auth_to_API(self):
        try:    
            self.authToken = None
            headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0', 'Accept':'application/json, text/plain, */*', 'Accept-Encoding': 'gzip, deflate, br, zstd', 'Content-Type': 'application/json'}
            responseData = requests.post(self.api_auth_url, headers=headers, verify=False, data='{"email":"' + self.maxxisun_email + '","ccu":"' + self.maxxisun_ccu + '"}')

            if (responseData.status_code >= 200 and responseData.status_code < 300):
                self.auth_JSON = json.loads(responseData.text)
                self.authToken = self.auth_JSON['jwt']
                return

            logger.error("Something went wrong with auth")
        except Exception as e:
            logger.error("Auth failed")


def handler(signum, frame):
    logger.warning("Signal handler called with signal: {1}".format(signum))
    sys.exit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Maxxisun API Prometheus Exporter',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--metric-port',
                        default=9120,
                        help='port to expose the metrics on')
    parser.add_argument('--config-file',
                        default='/etc/maxxisun/config.ini',
                        help='path to the configuration file')
    parser.add_argument('--collect-interval-seconds',
                        default=30,
                        help='collection interval in seconds')
    parser.add_argument('--api-url',
                        default="https://maxxisun.app:3000/api/last",
                        help='IP of Maxxisun API')
    parser.add_argument('--maxxisun-email',
                        default=None,
                        help='E-Mail to login on Maxxisun.app')
    parser.add_argument('--maxxisun-ccu',
                        default=None,
                        help='CCU to login on Maxxisun.app')
    parser.add_argument('--log-level',
                        default=30,
                        help='10-Debug 20-Info 30-Warning 40-Error 50-Critical')

    # Start up the server to expose the metrics.
    signal.signal(signal.SIGABRT, handler)
    e = Exporter(parser.parse_args())
    # Generate some requests.

    e.auth_to_API()

    while True:
        e.collect()
