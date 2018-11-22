"""
GCCCD Software Sensor. House pricing at Grossmont areas.
__version__ = "2.0"
__author__ = "VietTrinh"
__email__ = "viettrinh.ce@gmail.com"
"""
import os
import json
import time
import logging
from PIL import Image, ImageFont, ImageDraw
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
    _avg_dict = {}
    def __init__(self):
        """ calling the super this a file name, without extension, e.g. './housingsensor/HousingSensor' """
        super().__init__(os.path.join(os.path.dirname(__file__), self.__class__.__name__))
        self.__conn = self.props.get('conn')
        self.__url = self.props.get('service_url')
        self.__headers = {"accept":self.props.get('accept'),
                          "apikey":self.props.get('apikey')
                         }
        self.image_value = __class__._get_image_value(self)
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
        try:
            content = None
            zipcode = [value for key, value in self.props["elCajon_area_zipcode"].items()]
            random_zipcode = random.randint(0, len(zipcode) - 1)
            search_range_btm = random.randint(self.props["search_range_btm"], self.props["search_range_top"])
            offset_value = random.randint(self.props["search_range_offset_min"], self.props["search_range_offset_max"])
            # -- start fetching --
            if self._request_allowed():
                conn = http.client.HTTPSConnection(self.__conn)
                conn.request("GET", self.props['service_url']%(zipcode[random_zipcode],
                                                               search_range_btm,search_range_btm+offset_value),
                             headers=self.__headers)
                res = conn.getresponse()
                self.props['images_count'] += 1
                self.props['last_used'] = int(time.time())
                self._save_settings()
                if res is not None and res.status == 200:
                    content = __class__._create_content(json.loads(res.read().decode("utf-8")),
                                                        res.getheaders(),
                                                        self.props["last_used"],
                                                        self.props['images_count'],
                                                        self.props['images_reset'],
                                                        self.image_value)
                    logging.info("successfully requested new content")
                    self._write_buffer(content)  # remember last service request(s) results.
                else:
                    logging.warning("response: {}".format(res.status))
                    content = self._read_buffer()
        except http.client.HTTPException as e:
            logging.error("except: " + str(e))
            content = self._read_buffer()
        return content

    @staticmethod
    def _time_convert(date_time,lastused):
        """convert date to timestamp eg: Thu, 15 Nov 2018 00:54:52 GMT -> 1542243292"""
        try:
            time = ""
            for x in range(5, 25):
                if (date_time[x] != ":") & (date_time[x] != " "):
                    time += date_time[x]
            date = datetime.datetime.strptime(time, "%d%b%Y%H%M%S")
            timestamp = calendar.timegm(date.timetuple())
        except Exception as e:
            logging.error("except: " + str(e))
            timestamp = lastused
        return timestamp

    def get_featured_image(self):
        return os.path.join(os.path.dirname(__file__), 'images', self.props["featured_image"])

    def _get_image_value(self):
        try:
            image_value = {}
            featured_image = self.props["featured_image"]
            im = os.path.join(os.path.dirname(__file__), 'images', featured_image)
            img = Image.open(im)
            image_value["width"], image_value["height"] = img.size
            image_value["max_lat"] = self.props["max_lat"]
            image_value["min_lat"] = self.props["min_lat"]
            image_value["max_long"] = self.props["max_long"]
            image_value["min_long"] = self.props["min_long"]
            image_value["xScale"] = image_value["width"] / (image_value["max_long"] - image_value["min_long"])
            image_value["yScale"] = image_value["height"] / (image_value["max_lat"] - image_value["min_lat"])
            return image_value
        except Exception as e:
            logging.error("except: " + str(e))
            return None


    @staticmethod
    def _draw_avg_value(item, avg_value, images_count, images_reset, draw_dollar, image_value ):
        """Draw $ to the location found. Bigger value is represented bigger $"""
        try:
            address = item["address"]["oneLine"]
            lat = abs(float(item["location"]["latitude"]))
            long = abs(float(item["location"]["longitude"]))
            value = item["avm"]["amount"]["value"]
            if image_value is not None:
                direc = os.path.dirname(__file__)
                if (lat <= image_value["max_lat"]) &  (lat >= image_value["min_lat"]) & \
                    (long <= image_value["max_long"]) & (long >= image_value["min_long"]):
                        xPix = int(abs(long - image_value["max_long"]) * image_value["xScale"])
                        yPix = int(abs(lat - image_value["max_lat"]) * image_value["yScale"])
                        size = int(str(avg_value)[0])
                        if(draw_dollar == 0):
                            try:
                                im = os.path.join(direc, 'images/el cajon.jpg') \
                                    if images_count % images_reset == 0 else os.path.join(direc, 'images/housing-in.jpg')
                                img = Image.open(im)
                                draw = ImageDraw.Draw(img)
                                font_text = ImageFont.truetype("arial.ttf", 16+size*10)
                                draw.text((xPix, yPix), "$", font=font_text, fill=((255, int(255/size), 0, 255)))
                                img.save(os.path.join(direc, 'images/housing-in.jpg'))
                            except Exception as e:
                                logging.error("except: " + str(e) + "--- Can't draw housing-in.jpg")
                        # end  draw housing-in.jpg
                        # start draw housing-out.jppg
                        try:
                            out_name = 'housing-out' + str(draw_dollar) + '.jpg'
                            im =  os.path.join(direc, 'images/housing-in.jpg')
                            img = Image.open(im)
                            draw = ImageDraw.Draw(img)
                            font = ImageFont.truetype("arial.ttf", 16)
                            address_list = address.split(',')
                            draw.text((xPix + 10, yPix - 100), "   " + str(address_list[0]) , font=font,  fill="white")
                            draw.text((xPix + 10, yPix - 70), "   " + str(address_list[1]) + ", " + str(address_list[2]) + ".", font=font,  fill="white")
                            draw.text((xPix + 10, yPix - 40), "   __Total Value    : " + str(value) +"$", font=font,  fill="white")
                            draw.text((xPix + 10, yPix ),        "$ __Local average: " + str(avg_value) + "$", font=font, fill="white")
                            img.save(os.path.join(direc, 'images', out_name))
                        except Exception as e:
                            logging.error("except: " + str(e) + "--- Can't draw housing-out.jpg")
        except Exception as e:
            logging.error("except: " + str(e))

    @staticmethod
    def _get_average_value(data,date):
        avg = 0
        if data is not None:
            for item in data: avg += item["avm"]["amount"]["value"]
            avg /= len(data)
            __class__._avg_dict[date] = int(avg)
            return __class__._avg_dict[date]
        return 0

    @staticmethod
    def _create_content(data, header, last_used, images_count, images_reset, image_value):
        """ convert the json response from the web-service into a list of dictionaries that meets our needs. """
        content = []
        try:
            draw_dollar = 0
            timestamp = __class__._time_convert(header[1][1], last_used)
            avg_value = __class__._get_average_value(data["property"], header[1][1])
            for item in data["property"]:
                out_name = 'housing-out' + str(draw_dollar) + '.jpg'
                __class__._draw_avg_value(item, avg_value, images_count, images_reset, draw_dollar, image_value)
                tpm_record = {'k': int(timestamp),
                              'date': header[1][1],
                              'id': item["identifier"]["obPropId"],
                              'caption': 'House pricing at - {}'.format(item["address"]["oneLine"]),
                              'summary': 'Property: \n\t__Type: {} || Subtype: {} || Yearbuilt: {} \n\t__Calculated value: {}$ || Value range: {}$'.format(
                                  item["summary"]["proptype"],
                                  item["summary"]["propsubtype"],
                                  item["summary"]["yearbuilt"],
                                  item["avm"]["amount"]["value"],
                                  item["avm"]["amount"]["valueRange"]),
                              'img': os.path.join(os.path.dirname(__file__), 'images', out_name)
                              }
                content.append(tpm_record)
                draw_dollar += 1
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
