#! /usr/bin/env python3

import argparse
import datetime
import urllib.request
import json

import yaml
import gantt

class ColourWheel:
    """Class that will return an endless aount of colors from a color wheel based on C3VOC green (#28C3AB)

    Source: http://paletton.com/#uid=c3d0p3G0S0kprGteZQMkBLdvfCm-Rrp
    """

    colours = ['#28C3AB', '#28C3A9', '#386FC8', '#FFB534', '#FF8634', '#78E1D0', '#83A8E3', '#FFD488', '#FFB888',
               '#4AD1BA', '#5888D4', '#FFC35B', '#FF9D5B', '#04B799', '#1556BC', '#FFA506', '#FF6B06', '#008A73',
               '#DA8B00', '#DA5800']

    def __init__(self):
        self.list_iterator = iter(self.colours)

    def __iter__(self):
        return self

    def __next__(self):
        try:
            colour = next(self.list_iterator)

            return colour
        except:
            self.list_iterator = iter(self.colours)
            colour = next(self.list_iterator)

            return colour


class C3VOCCalendar:
    """A class representing the C3VOC calendar. It parses various data sources and then exports them as a GANTT chart in SVG form"""
    resources = {}
    calendar = {}

    def load_yaml_file(self, yaml_file_name):
        """Loads the requested YAML file and tries to parse it into a datastructure"""
        try:
            with open(yaml_file_name, 'r') as stream:
                try:
                    self.calendar = yaml.safe_load(stream)
                    return True
                except yaml.YAMLError as yaml_exception:
                    print(yaml_exception)
        except OSError as open_error:
            print(open_error)

        return False

    def load_json_url(self, json_url):
        """Downloads a json file from the supplied URL and reads into the format as defined by the YAML file loader"""
        try:
            with urllib.request.urlopen(json_url) as url:
                events = json.loads(url.read().decode())
                print(events)

                for source_name, source_event in events["voc_events"].items():

                    event_date = datetime.datetime.strptime(source_event["start_date"], "%Y-%m-%d").date()
                    today = datetime.date.today()
                    first_of_the_year = today.replace(month=1)
                    first_of_the_year = first_of_the_year.replace(day=1)

                    if event_date >= first_of_the_year:
                        event = dict()
                        event["start"] = event_date
                        event["end"] = datetime.datetime.strptime(source_event["end_date"], "%Y-%m-%d").date()

                        room_cases = []
                        audio_cases = []

                        for case in source_event["cases"]:
                            if case in ["1", "2", "3", "4", "5", "6", "7", "8"]:
                                room_cases.append("S" + case)
                            elif case[0] == "A":
                                audio_cases.append(case.upper())
                            else:
                                room_cases.append(case.upper())

                        event["room cases"] = room_cases
                        event["audio cases"] = audio_cases

                        self.calendar[source_name] = event

                if len(self.calendar) > 0:
                    print("Calendar = %s" % str(self.calendar))
                    return True

        except Exception as e:
            import traceback
            print("""Received an exception: %s\nTraceback: %s""" % (str(e), traceback.format_exc()))

        return False


    def is_resource_known(self, resource_name):
        return resource_name in self.resources

    def create_unique_gantt_resource(self, resource_name):
        if not self.is_resource_known(resource_name):
            resource = gantt.Resource(resource_name)
            self.resources[resource_name] = resource

    def create_resourses_from_event(self, event_details):
        """Create a unique Gantt resource for all resources in the event.

        This makes sure we only have 1 Gantt resource for all the occurences of a resource over all the events
        """
        if 'room cases' in event_details:
            for room_case in event_details['room cases']:
                self.create_unique_gantt_resource(room_case)

        if 'audio cases' in event_details:
            for audio_case in event_details['audio cases']:
                self.create_unique_gantt_resource(audio_case)

    def retrieve_resources_for_event(self, event_details):
        """Read the resources from the evernt details and return a list of the Gantt resources for the event"""

        necessary_resources = []

        if 'room cases' in event_details:
            for room_case in event_details['room cases']:
                resource = self.resources[room_case]
                necessary_resources.append(resource)

        if 'audio cases' in event_details:
            for audio_case in event_details['audio cases']:
                resource = self.resources[audio_case]
                necessary_resources.append(resource)

        return necessary_resources


    def create_event_as_gantt_task(self, event_name, event_details, colour):
        """Create a Gantt task  for the event and assign the resources"""

        # parse the start time into a datetime and find the length of the event in days
        start_date = event_details['start']
        end_date = event_details['end']
        duration = end_date - start_date

        days = duration.days

        # Retrieve a list of the resources assigned to this event
        resources = self.retrieve_resources_for_event(event_details)

        # Create the task
        task = gantt.Task(name = event_name,
                          start = start_date,
                          duration = days,
                          resources = resources,
                          color = colour)

        return task


    def create_calendar(self):
        """Iterate over the parsed YAML calendar file and add the "resources" to the project. An event is a task and
        the audio cases and room cases are resources
        """

        colours = ColourWheel()

        for event_name, event_details in self.calendar.items():
            # First gather the resources
            self.create_resourses_from_event(event_details)

            # Create the task and assign the resources
            event = self.create_event_as_gantt_task(event_name = event_name, event_details = event_details, colour = next(colours))

            # Add the task to the project
            self.gantt_project.add_task(event)

    def export_calendar(self, svg_name):
        """Create an SVG from Gantt project for the current year"""
        today = datetime.date.today()
        start_date = today
        start_date = start_date.replace(day = 1)
        start_date = start_date.replace(month = 1)

        end_date = today
        end_date = end_date.replace(month = 12)
        end_date = end_date.replace(day = 31)

        self.gantt_project.make_svg_for_resources(filename = svg_name,
                                                  today = today,
                                                  start = start_date,
                                                  end = end_date)


    def main(self, arguments):
        """The main application function, this is where it all starts properly"""
        generate_output = False

        if arguments.calendar_yaml_file:
            if self.load_yaml_file(arguments.calendar_yaml_file.strip()):
                generate_output = True
            else:
                print("""Failure while trying to load the YAML file, please check error message, fix the problem and try again""")

        elif arguments.calendar_json_url:
            if self.load_json_url(arguments.calendar_json_url.strip()):
                generate_output = True
            else:
                print("""Loading the JSON file from %s failed. Please check the supplied URL""" % (arguments.calendar_json_url))
        else:
            print("""The supplied combination of parameters is not sufficient to do something. Please review""")

        if generate_output:
            self.gantt_project = gantt.Project(name='C3VOC')

            self.create_calendar()
            self.export_calendar(arguments.calendar_svg_file.strip())

            return True

        return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", help="YAML file to use as source for the calendar", dest="calendar_yaml_file", action="store")
    parser.add_argument("-o", help="SVG file to use as output for the calendar", dest="calendar_svg_file", action="store")
    parser.add_argument("-u", help="URL to download JSON from", dest="calendar_json_url", action="store")
    args = parser.parse_args()

    calendar = C3VOCCalendar()
    result = calendar.main(args)

    exit(result)
