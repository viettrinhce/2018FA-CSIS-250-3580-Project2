"""
GCCCD Software Sensor. House pricing at Grossmont areas.
__version__ = "1.1"
__author__ = "VietTrinh"
__email__ = "viettrinh.ce@gmail.com"
"""
import os
import json
import time
import logging
from PIL import Image,ImageFont,ImageDraw
from sensor import SensorX
import http.client
import random
import datetime
import calendar

# logging into current_dir/logs/{sensor_name}.log
logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(os.getcwd(), 'logs', 'housingsensor.log'),
    filemode='a',
    format='%(asctime)s - %(lineno)d - %(message)s')


class HousingSensor(SensorX):
    """ Simply reporting the current time, as reported by api.timezonedb.com
        FooSensor.json is the sensor's config file and FooSensor.buf is the history buffer """
    _udp = {}
    _count = 0
    _avg_dict = {}
    def __init__(self):
        """ calling the super this a file name, without extension, e.g. './housingsensor/HousingSensor' """
        super().__init__(os.path.join(os.path.dirname(__file__), self.__class__.__name__))
        self.__conn = self.props.get('conn')
        self.__url = self.props.get('service_url')
        self.__headers = {"accept":self.props.get('accept'),
                          "apikey":self.props.get('apikey')
                         }
        print("This sensor just woke up .. ready to call " + self.__conn + self.__url)
        logging.info("Sensor just woke up .. ready to be called")

    #
    #   Implementing the required methods
    #

    def has_updates(self, k):
        """ find out if there is content beyond k"""
        if self._request_allowed():
            content = self._fetch_data()
            if content is not None:
                if 0 < len(content) and content[0]['k'] != k:
                    return 1
        return 0

    def get_content(self, k):
        """ return content after k"""
        content = self.get_all()
        if content != None:
            return content if 0 < len(content) and content[0]['k'] != k else None

    def get_all(self):
        """ return fresh or cached content"""
        if self._request_allowed():
            return self._fetch_data()
        else:
            return self._read_buffer()

    def _fetch_data(self):
        """ json encoded response from webservice .. or none"""
        content = None
        zipcode = [92020,92019,92021,92071,92119, 91942]
        rzip = random.randint(0,5)
        minvalue = random.randint(1,80)*10000
        offsetvalue = random.randint(10,20)*10000
        try:
            if self._request_allowed():
                conn = http.client.HTTPSConnection(self.__conn)
                conn.request("GET", self.props['service_url']%(zipcode[rzip],minvalue,minvalue+offsetvalue),
                             headers=self.__headers)
                res = conn.getresponse()
                hd = res.getheaders()
                data = json.loads(res.read().decode("utf-8"))
                self.props['last_used'] = int(time.time())
                self._save_settings()
                lastused = self.props["last_used"]
                if res is not None and res.status == 200:
                    content = __class__._create_content(data,hd,lastused)
                    logging.info("successfully requested new content")
                    self._write_buffer(content)  # remember last service request(s) results.
                else:
                    logging.warning("response: {}".format(res.status))
                    content = None
        except http.client.HTTPException as e:
            logging.error("except: " + str(e))
            content = None
        return content

    @staticmethod
    def _time_convert(tm,lastused):
        """convert date to timestamp eg: Thu, 15 Nov 2018 00:54:52 GMT -> 1542243292"""
        try:
            tmp = tm.split(" ")
            tmp.pop(len(tmp) - 1)
            tmp.pop(0)
            tmp2 = ""
            for item in tmp: tmp2 += item
            tmp = ""
            for i in range(len(tmp2)):
                if tmp2[i] != ":": tmp += tmp2[i]
            date = datetime.datetime.strptime(tmp, "%d%b%Y%H%M%S")
            timestamp = calendar.timegm(date.timetuple())
        except Exception as e:
            logging.error("except: " + str(e))
            timestamp = lastused
        return timestamp

    def get_featured_image(self):
        """Return directory to the image file. Not a weblink"""
        return os.path.join(os.path.dirname(__file__)) + '/housing-out.jpg'

    @staticmethod
    def _draw_avg_value(lat,long,avg_value):
        """Draw $ to the location found. Bigger value is represented bigger $"""
        try:
            im = "el cajon.jpg" if __class__._count <= 1 else 'housing-out.jpg'
            img = Image.open(im)
            if (lat <= 32.860) & (lat >= 32.740) & (long <= 117.106) & (long >= 116.806):
                xPix = int(abs(long - 117.106) * 4860)
                yPix = int(abs(lat - 32.860) * 5780)
                size = int(avg_value/100000)
                draw = ImageDraw.Draw(img)
                fonttext = ImageFont.truetype("arial.ttf", 16+size*10)
                draw.text((xPix, yPix), "$", font=fonttext, fill=(255, 255, 255, 5))
                font = ImageFont.truetype("arial.ttf", 20)
                yPix = yPix - size * 5
                draw.text((xPix, yPix), "____" + str(avg_value) +"$" +"__" , font=font, fill="orange")
                img.save('housing-out.jpg')
        except Exception as e:
            logging.error("except: " + str(e))

    @staticmethod
    def _get_average_value(data,date):
        avg = 0
        if data is not None:
            for item in data:
                avg += item["avm"]["amount"]["value"]
            avg /= len(data)
            __class__._avg_dict[date] = int(avg)
            return __class__._avg_dict[date]
        return 0

    @staticmethod
    def _create_content(data, hd, lastused):
        """ convert the json response from the web-service into a list of dictionaries that meets our needs. """
        content = []
        try:
            maxlong = maxlat = 1000
            __class__._count += 1
            timestamp = __class__._time_convert(hd[1][1], lastused)
            for item in data["property"]:
                tpm_record = {'k': int(timestamp),
                              'date': hd[1][1],
                              'id': item["identifier"]["obPropId"],
                              'caption': 'House pricing at - {}'.format(item["address"]["oneLine"]),
                              'summary': 'Property: type - {} subtype - {} yearbuilt - {} Calculated value - {}$ value range - {}$'.format(
                                  item["summary"]["proptype"],
                                  item["summary"]["propsubtype"],
                                  item["summary"]["yearbuilt"],
                                  item["avm"]["amount"]["value"],
                                  item["avm"]["amount"]["valueRange"])
                              }
                content.append(tpm_record)
                lat = abs(float(item["location"]["latitude"]))
                long = abs(float(item["location"]["longitude"]))
                if maxlat > lat: maxlat = lat
                if maxlong > long: maxlong = long
            avg_value = __class__._get_average_value(data["property"], hd[1][1])
            __class__._draw_avg_value(maxlat,maxlong, avg_value)
        except Exception as e:
            logging.error("except: " + str(e))
            content = None
        return content

if __name__ == "__main__":
    """ let's play """
    sensor = HousingSensor()
    for i in range(15):
        print(sensor.get_all())
        time.sleep(1)  # let's relax for short while

    n = 0
    for i in range(15):
        if sensor.has_updates(n):
            ld = sensor.get_content(n)  # list of dictionaries
            print(ld)
            n = ld[0]['k']
        time.sleep(1)  # let's relax for short while
        print("sleeping ...")
