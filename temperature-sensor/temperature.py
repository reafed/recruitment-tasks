import datetime
import time
import requests

class temperature:

    def __init__(self, fileName, frequency, resolution, maxTemperature, minTemperature, api_endpoint, altApi_endpoint):
        #Have this to make the code more diverse
        self.file = open(fileName, "r")
        self.frequency = frequency / 1000 #Frequency in ms, is converted to seconds
        self.resolution = 2**resolution
        self.maxTemperature = maxTemperature
        self.minTemperature = minTemperature

        #Calculating variables
        self.range = maxTemperature - minTemperature 
        self.step = self.range / self.resolution #Steps pr degree in adc
        self.lastrun = time.perf_counter() - self.frequency

        #Api adresses
        self.api_endpoint = api_endpoint
        self.altApi_endpoint = altApi_endpoint

    def getTemperature(self):
        #Gets the temperature from the txt file
        elapsedTime = time.perf_counter() - self.lastrun
        if elapsedTime >= self.frequency: #This makes sure the code can't run faster than the frequency
            adc = self.file.readline()
            temperature = float(adc) * self.step + self.minTemperature #Uses minTemperature as the offset
            self.lastrun = time.perf_counter()
            return temperature

    def hasNext(self):
        #Checks if there is a next line in the txt file
        curPos = self.file.tell()
        next = bool(self.file.readline())
        self.file.seek(curPos)
        return next

    def readTemperature(self):
        #Class that reads through the entire txt file and sends values to the endpoint

        #Initializing the variables needed
        timer = time.perf_counter()
        timestamp = datetime.datetime.utcnow().isoformat()
        values = list()
        storedData = list()
        failedData = dict()
        httpError = False
        dataSent = 1

        print("Starting...\n")

        #Loops the code for each line in the txt file
        while self.hasNext():
            #Checks if the elapsed time is big enough to send the data
            if time.perf_counter() - timer <= 120:
                temp = self.getTemperature()
                if temp:
                    #Only appends real vaules
                    values.append(temp)

            else:
                print("\nPackage: ", dataSent, "\n")
                dataSent += 1

                #Adds the data as a dict, a dict can be changed into a JSON easily
                TemperatureMeasurment = {
                    "time": {
                        "start": timestamp, #Start date and time in ISO8601 format for the measurment
                        "end": datetime.datetime.utcnow().isoformat() #End date and time in ISO8601 format for the measurment
                    },
                    "min": round(min(values), 2), #Minimum observed temperature
                    "max": round(max(values), 2), #Maximum observed temperature
                    "avg": round(sum(values) / len(values), 2) #Average temperature
                }

                values.clear() #Clears the values for the next run
                timer = time.perf_counter() #Resets the timer
                timestamp = datetime.datetime.utcnow().isoformat() #Makes a new timestamp

                #Checks if there is an error and tries send the data
                if httpError:
                    print("Sending prevoius data: ", failedData, " to enpoint ", self.api_endpoint, "...")

                    try:
                        r = requests.post(self.api_endpoint, json=failedData)
                        r.raise_for_status()

                    except requests.exceptions.HTTPError:
                        #If this failes it sends the stored data to the alternative endpoint
                        print("Failed to send previous data, status code: ", r.status_code, "\n")
                        print("Sending stored data to endpoint: ", self.altApi_endpoint)

                        while(True):
                            #Tries too send the stored data
                            try:
                                r = requests.post(self.altApi_endpoint, json=storedData)
                                r.raise_for_status()

                            except requests.exceptions.HTTPError:
                                #Makes sure the data is sent to the alternative api if the status code is 500
                                if r.status_code == 500:
                                    print("Failed to send stored data, Trying again")
                                    continue

                                else:
                                    # if the status code is something else it will write out the status code
                                    print("Somthing vent Wrong, Status code: ", r.status_code, "\n")
                            else:
                                print("Successfully sent stored data\n")
                                httpError = False
                                break
                    else:
                        print("Successfully sent previous data\n")
                        httpError = False

                try:
                    print("Sending data: ", TemperatureMeasurment, " to endpoint: ", self.api_endpoint, "...")

                    r = requests.post(self.api_endpoint, json = TemperatureMeasurment)
                    r.raise_for_status()

                except requests.exceptions.HTTPError:
                    #Stores the failed data and send the status code
                    print("Failed to send data, status code: ", r.status_code, "\n")

                    failedData = TemperatureMeasurment
                    httpError = True

                else:
                    print("Succsessfully sent data\n")

                finally:
                    #Stores the last 10 TemperatureMeasurments
                    if len(storedData) <= 10:
                        storedData.append(TemperatureMeasurment)

                    else:
                        #Makes sure the list of stored data always is 10
                        storedData.pop(0)
                        storedData.append(TemperatureMeasurment)

        self.file.close()
            

if __name__ == '__main__':

    temp = temperature("temperature.txt", 100, 12, 50, -50, "http://localhost:5000/api/temperature", "http://localhost:5000/api/temperature/missing")
    temp.readTemperature()