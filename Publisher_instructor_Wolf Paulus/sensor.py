"""
Sensor is an Abstract base classes for a GCCCD Software Sensor
The basic idea of a software sensor is that it can be asked to fetch data from an external Web Service.
The sensor then turns the data into useful information, e.g. telling which city has the nicest weather next weekend.

The sensor may require credentials to access the 3rd party web service; those need to be stored in a JSON file and
read during startup. Also all other configuration data, like location, zip-codes, GPS Coordinates must not be hardcoded,
but loaded from a JSON file.
The sensor must transparently protect itself from being asked to report information too frequently. I.e., the sensor is
responsible for working inside the limits, prescribed by the 3rd party web service, but without becoming unresponsive.
"""
__version__ = "1.1"
__author__ = "Wolf Paulus"
__email__ = "wolf.paulus@gcccd.edu"

from abc import ABC, abstractmethod
import json
import logging
import time


# noinspection PyMethodMayBeStatic
class Sensor(ABC):
    def __init__(self):
        self.props = {}

    def __str__(self):
        return self.__class__.__name__

    @abstractmethod
    def has_updates(self, k):
        """ returns the number of new 'records' that the sensor can provide,
        where k is an identifier previously issued by this sensor."""
        return 0

    @abstractmethod
    def get_content(self, k):
        """ A list of dictionaries: all the new records, since k, newest one last
        E.g.
        [{'k'       : 0  a unique records identifier
          'date'    : string representation of datetime.datetime
          'caption' : 'Grossmont–Cuyamaca Community College District up to 255 characters'
          'summary' : 'Grossmont–Cuyamaca Community College District is a California community college district'
          'story'   : (optional, either plaintext or markdown) 'The Grossmont–Cuyamaca Community College District is ..'
          'img'     : (optional link to a jpg or png) 'https://upload.wikimedia.org/wikipedia/.../logo.png'
          'origin'  : (optional link to the source) 'https://en.wikipedia.org/wiki/...'
        }]
        """
        return [{}]

    @abstractmethod
    def get_all(self):
        """ A list containing all available records oldest first. """
        return [{}]

    def get_featured_image(self):
        """ optional background image for this sensors content"""
        return None


class SensorX(Sensor):
    """ This base class offers a few commonly used features, but requires that the sensor maintains its configuration
    in __class__.__name__.json
    Moreover, the config needs to have a property named 'request_delta' for the minimum number of seconds between
    request and 'last_used', to store the int(time.time()) time-stamp of the last request."""

    def __init__(self, file_name):
        """ read sensor settings from config file into self.props """
        super().__init__()
        self.file_name = file_name
        with open(file_name + '.json') as json_text:
            self.props = json.load(json_text)
        logging.info(self.__class__.__name__ + " just woke up .. ready to be called")

    def _request_allowed(self):
        """ check if it's OK to call the 3rd party web-service again, or if we rathe rwait a little longer """
        return not self.props['offline'] and int(time.time()) - self.props['last_used'] > self.props['request_delta']

    def _save_settings(self):
        """ save (updated) config settings to disk """
        with open(self.file_name + '.json', 'w') as outfile:
            json.dump(self.props, outfile)

    def _write_buffer(self, content):
        """ keep a copy of the list of dictionaries on file """
        try:
            with open(self.file_name + '.buf', 'w') as textfile:
                json.dump(content, textfile)
            logging.info("content cached")
        except (Exception, OSError, ValueError) as e:
            logging.error("buffer: " + str(e))
            return None

    def _read_buffer(self):
        """ read list of dictionaries from file"""
        try:
            with open(self.file_name + '.buf') as textfile:
                return json.load(textfile)
        except (Exception, OSError, ValueError) as e:
            logging.error("buffer: " + str(e))
            return None

    def get_featured_image(self):
        """ needs to be overridden if inheriting from SensorX provides a featured image """
        return None

    def has_updates(self, k):
        """ needs to be implemented by class inheriting from SensorX """
        pass

    def get_content(self, k):
        """ needs to be implemented by class inheriting from SensorX """
        pass

    def get_all(self):
        """ needs to be implemented by class inheriting from SensorX """
        pass
