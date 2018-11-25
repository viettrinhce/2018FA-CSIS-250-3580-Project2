"""
GCCCD Software Sensor. House pricing at Grossmont areas.
__version__ = "2.3"
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
    """ Using the free database API from Attomdata.com. This sensor calculate the average house pricing arround Grossmont neiborhood. """
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
            prev = self._read_buffer()
            content = self._fetch_data()
            return 0 if prev and prev[0] and prev[0]['summary'] == content[0]['summary'] else 1
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
            try:
                zipcode_list = [value for key, value in self.props["elCajon_area_zipcode"].items()]
                random_zipcode = random.randint(0, len(zipcode_list) - 1)
                zipcode = zipcode_list[random_zipcode]
            except Exception as e:
                logging.error("except: " + str(e) + "-- Can't get zipcode, return 92020 as default")
                zipcode = 92020
            try:
                search_range_btm = random.randint(self.props["search_range_btm"], self.props["search_range_top"])
                offset_value = random.randint(self.props["search_range_offset_min"], self.props["search_range_offset_max"])
                search_range_top = search_range_btm+offset_value
            except Exception as e:
                logging.error("except: " + str(e) + "-- Can't search range, return 300k-500k as default")
                search_range_btm = 300000
                search_range_top = 500000
            # -- start fetching --
            if self._request_allowed():
                try:
                    conn = http.client.HTTPSConnection(self.__conn)
                    conn.request("GET", self.props['service_url']%(zipcode, search_range_btm, search_range_top),
                                                                                            headers=self.__headers)
                    res = conn.getresponse()
                except http.client.HTTPException as e:
                    logging.error("except: " + str(e) + "-- in _fetch_data() -- request fail")
                    return self._read_buffer()
                self.props['images_count'] += 1
                self.props['last_used'] = int(time.time())
                self._save_settings()
                if res is not None:
                    if res.status == 200:
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
                else:
                    content = self._read_buffer()
        except http.client.HTTPException as e:
            logging.error("except: " + str(e) + "-- in _fetch_data()")
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
            logging.error("except: " + str(e) + "-- in _time_convert()")
            timestamp = lastused
        return timestamp

    def get_featured_image(self):
        return os.path.join(os.path.dirname(__file__), 'images', self.props["featured_image"] + self.props["image_type"])

    def _get_image_value(self):
        """ Find all values of original image, font, directory"""
        try:
            image_value = {}
            font_directory = __class__._find_directory(self.props["font"])
            fname = os.path.join(font_directory, self.props["font"]) if font_directory is not None else None
            if fname is not None:
                image_value["font_directory"] = fname if os.path.isfile(fname) else None
            image_value["image_type"] = self.props["image_type"]
            image_value["original_image"] =  self.props["original_image"]
            image_value["average_image_dollar"] = self.props["average_image_dollar"]
            image_value["featured_image"] = self.props["featured_image"]
            im = os.path.join(os.path.dirname(__file__), 'images', image_value["original_image"] + image_value["image_type"] )
            image_value["width"], image_value["height"] = Image.open(im).size
            image_value["max_lat"] = self.props["max_lat"]
            image_value["min_lat"] = self.props["min_lat"]
            image_value["max_long"] = self.props["max_long"]
            image_value["min_long"] = self.props["min_long"]
            image_value["xScale"] = image_value["width"] / (image_value["max_long"] - image_value["min_long"])
            image_value["yScale"] = image_value["height"] / (image_value["max_lat"] - image_value["min_lat"])
            return image_value
        except Exception as e:
            logging.error("except: " + str(e) + "-- in _get_image_value()")
            return None

    @staticmethod
    def _find_directory(item):
        """Find directory of file"""
        try:
            direc = os.path.dirname(__file__)
            for root, dirs, files in os.walk(direc):
                for file in files:
                    if file == item:
                        return root
            return None
        except Exception as e:
            logging.error("except: " + str(e) + "-- in _find_directory()")
            return None

    @staticmethod
    def _draw_dollar(image_value, images_count, images_reset, xPix, yPix, size):
        """Draw  $ at local area"""
        try:
            direc = os.path.dirname(__file__)
            in_name = image_value["original_image"] + image_value["image_type"]
            out_name = image_value["average_image_dollar"] + image_value["image_type"]
            if image_value["font_directory"] is not None:
                im = os.path.join(direc, 'images', in_name) \
                    if images_count % images_reset == 0 else os.path.join(direc, 'images', out_name )
                img = Image.open(im)
                draw = ImageDraw.Draw(img)
                font_text = ImageFont.truetype(os.path.join(direc, image_value["font_directory"]), 16 + size * 10)
                draw.text((xPix, yPix), "$", font=font_text, fill=((255, int(255 / size), 0, 255)))
                img.save(os.path.join(direc, 'images', out_name))
        except Exception as e:
            logging.error("except: " + str(e) + "-- in _draw_dollar()")

    @staticmethod
    def _draw_at_address(image_value, draw_dollar, address, xPix, yPix, value, avg_value):
        """Draw total value at specific address"""
        try:
            direc = os.path.dirname(__file__)
            in_name = image_value["average_image_dollar"] + image_value["image_type"]
            out_name = image_value["featured_image"] + str(draw_dollar) + image_value["image_type"]
            try:
                if image_value["font_directory"] is not None:
                    im = os.path.join(direc, 'images', in_name)
                    img = Image.open(im)
                    draw = ImageDraw.Draw(img)
                    font = ImageFont.truetype(os.path.join(direc, image_value["font_directory"]), 16)
                    address_list = address.split(',')
                    draw.text((xPix + 10, yPix - 100), "   " + str(address_list[0]), font=font, fill="white")
                    draw.text((xPix + 10, yPix - 70), "   " + str(address_list[1]) + ", " + str(address_list[2]) + ".", font=font, fill="white")
                    draw.text((xPix + 10, yPix - 40), "   __Total Value    : " + str(value) + "$", font=font, fill="white")
                    draw.text((xPix + 10, yPix), "$ __Local average: " + str(avg_value) + "$", font=font, fill="white")
                    img.save(os.path.join(direc, 'images', out_name))
            except Exception as e:
                """ If can't draw at specific address, return the map with $ only, not the one with old address"""
                logging.error("except: " + str(e) + "-- in _draw_at_address()")
                im = os.path.join(direc, 'images', in_name)
                img = Image.open(im)
                img.save(os.path.join(direc, 'images', out_name))
        except Exception as e:
            logging.error("except: " + str(e) + "-- in _draw_at_address()")

    @staticmethod
    def _draw_avg_value(item, avg_value, images_count, images_reset, draw_dollar, image_value ):
        """Draw $ to the location found. Bigger value is represented bigger $"""
        try:
            address = item["address"]["oneLine"]
            lat = abs(float(item["location"]["latitude"]))
            long = abs(float(item["location"]["longitude"]))
            value = item["avm"]["amount"]["value"]
            if image_value is not None:
                if (lat <= image_value["max_lat"]) &  (lat >= image_value["min_lat"]) & \
                    (long <= image_value["max_long"]) & (long >= image_value["min_long"]):
                        xPix = int(abs(long - image_value["max_long"]) * image_value["xScale"])
                        yPix = int(abs(lat - image_value["max_lat"]) * image_value["yScale"])
                        size = int(str(avg_value)[0])
                        if(draw_dollar == 0):
                           __class__._draw_dollar(image_value, images_count, images_reset, xPix, yPix, size)
                        __class__._draw_at_address(image_value, draw_dollar, address, xPix, yPix, value, avg_value)
        except Exception as e:
            logging.error("except: " + str(e) + "-- in _draw_avg_value")

    @staticmethod
    def _get_average_value(data, date):
        """ calculate average value. """
        avg = 0
        try:
            if data is not None:
                for item in data: avg += item["avm"]["amount"]["value"]
                avg /= len(data)
                __class__._avg_dict[date] = int(avg)
                return __class__._avg_dict[date]
            return 0
        except Exception as e:
            logging.error("except: " + str(e) + "-- in get_average_value()")
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
                out_name = image_value["featured_image"] + str(draw_dollar) + image_value["image_type"]
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
                              'story': '**{} {}** built in _{}_\n Calculated value: **${:,}**,\n Range from: **${:,}**, To: ${:,}'.format(
                                  (item["summary"]["propsubtype"]).capitalize(),
                                  (item["summary"]["proptype"]).capitalize(),
                                  item["summary"]["yearbuilt"],
                                  item["avm"]["amount"]["value"],
                                  item["avm"]["amount"]["value"] - int(item["avm"]["amount"]["valueRange"]/2),
                                  item["avm"]["amount"]["value"] + int(item["avm"]["amount"]["valueRange"]/2)),
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
    for i in range(100):
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
