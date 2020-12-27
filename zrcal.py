# -*- mode: python; coding: utf-8 -*-
#
# This tool generates personalized calendars based on
# Open Government Data.
#
import datetime
import string
import urllib2
import wsgiref.handlers
import re
import csv
import os
import logging
import webapp2
from webapp2_extras import jinja2, i18n
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
import icalendar
from bs4 import BeautifulSoup


ZIPS = [8001, 8002, 8003, 8004, 8005, 8006, 8008,
        8032, 8037, 8038, 8041, 8044, 8045, 8046,
        8047, 8048, 8049, 8050, 8051, 8052, 8053,
        8055, 8057, 8064]

GA_ID = 'UA-33259788-1'
GOOGLE_AD_CLIENT = 'ca-pub-6118177449333262'


class Abfuhr(db.Model):
    zip = db.IntegerProperty(required=True)
    type = db.StringProperty(required=True)
    loc = db.StringProperty(required=False)
    date = db.DateProperty(required=True, indexed=True)

    def to_icalendar_event(self):
        event = icalendar.Event()
        params = {'language': 'de'}
        event.add('summary', self.type, parameters=params)
        if self.date and isinstance(self.date, datetime.date):
            event.add('dtstart', self.date)
        if self.loc:
            event.add('location', self.loc + ', ' + str(self.zip),
                   parameters=params)
        else:
            event.add('location', str(self.zip),
                   parameters=params)
        return event


class OGDZMetaPage(db.Model):
    type = db.StringProperty(required=True)
    url = db.StringProperty(required=True)
    fetch_date = db.DateTimeProperty(auto_now=True)
    data_url = db.StringProperty(required=False)
    contents = db.BlobProperty(required=True)

    @classmethod
    def get_meta_page(cls, type, url):
        meta = db.get(db.Key.from_path(cls.__name__, type))
        if meta:
            return meta.contents
        else:
            try:
                meta = cls(key_name=type,
                           type=type,
                           url=url,
                           contents=urllib2.urlopen(url).read())
                meta.put()
                return meta.contents
            except urllib2.HTTPError:
                logging.error("HTTP error opening URL {}".
                              format(url))
                return None


def meta_url(type):
    return 'https://data.stadt-zuerich.ch/dataset/erz_entsorgungskalender_%s' % (type)


type_to_id_2016 = dict({
    'papier':        '1fdff0f0-d477-4b2e-9997-d26ad36bf079',
    'kehricht':      '875e5ed1-edf4-4b37-bc9f-3c0b7f448155',
    'karton':        'f2701266-d5a6-4278-8a45-c726767a343e',
    'gartenabfall':  '0a54aaf9-3553-4302-a6ff-605889f6e62d',
    'eTram':         'a12a4f0d-48eb-4bf9-b252-dcc1bf429483',
    'cargotram':     '25280960-a847-4371-b7c3-0ad651ec8c39',
    'textilien':     '9c2e8678-9433-4400-96a2-a501e5071601',
    'sonderabfall':  '9dcf367d-5bd4-46a9-bee1-03fdf7bc2ac3',
    'sammelstellen': '50527dff-cc1e-403a-8c37-1a8faf731dfb',
})
type_to_id_2017 = dict({
    'papier':        '049cc13a-d8b1-4ab6-8ccb-1363c1a65026',
    'kehricht':      'c64a9a9a-e09c-4c88-896d-b9580163b704',
    'karton':        'b6a9f085-6434-4ba2-b262-9856a4173ace',
    'gartenabfall':  '12aa005e-f76f-4b42-a3c5-fd9b24e3824f',
    'eTram':         'bd648272-dd43-492a-8fff-86c0fe248ae9',
    'cargotram':     '176073cf-dcd6-4c77-b18a-fc89f955590a',
    'textilien':     '4d484de2-0e8d-49d4-94b4-afcacdeb5305',
    'sonderabfall':  'cfda766c-e263-479c-8f42-e26b0cf9c9da',
    'sammelstellen': 'c351476a-1101-4f3b-9e91-24c8d6498acb',
})
type_to_id_2018 = dict({
    'papier':        'c49b791a-cef8-45c9-9f2d-dd3e62e521c9',
    'kehricht':      '2d613f1a-f860-4684-800e-36fc127cd33b',
    'karton':        'd940b125-c8d5-47d9-93ab-1a3c91a65b34',
    # ?? 'gartenabfall':  'cee9cf76-3da3-44d3-bea5-71b3e72aa8f 6',
    'gartenabfall':   '70f2589d-4db6-443f-bc0b-9dc905f79388',
    'eTram':         'b7002774-18d6-48fc-970d-1c3a0f53351b',
    'cargotram':     '27bcc9a4-a0f4-49dc-902a-78496721817d',
    'textilien':     '3835230a-850b-42b6-868e-c3a4fb1a7401',
    'sonderabfall':  '0b8990d1-8732-45c3-b555-79548175870f',
    # 'sammelstellen': '9cc8d403-d13a-4631-84ca-6b76e785c6c6',
})
type_to_id_2019 = dict({
    'papier':        '87c71720-44a2-4d29-b9b6-961a17b540f6',
    'kehricht':      '29fcecbc-e2dd-44dc-9fb2-b24edd5f8c50',
    'karton':        '47c83f71-29d1-4790-a3de-b29c3de8c35a',
    'gartenabfall':  '5aa7697a-552e-42cc-a539-4309c5b5ef27',
    'eTram':         '387d8384-4432-4581-81b1-e4903143696c',
    'cargotram':     'd2082497-c4db-4e9c-b184-1b18f473abca',
    'textilien':     '30284fdf-a47c-4054-939a-a627de9ec350',
    'sonderabfall':  '53b143a9-5ca0-408a-82e7-e85fe4f8ece3',
    # 'sammelstellen': 'c18dba15-5f57-4a99-a406-92149a5cd508',
})
type_to_id_2020 = dict({
    'papier':        'eeca6200-7cc1-4f05-af13-fc262b830149',
    'kehricht':      '0d19477d-f7d2-4aec-a96b-5954d380cc79',
    'karton':        '6d28096a-1e04-43ef-8d18-0ce9464a7329',
    'gartenabfall':  'a0953059-f4e6-4fe5-8db3-a2ccbda884a6',
    'eTram':         '70aae2a6-e679-48f4-8e69-271adf77def6',
    'cargotram':     '6b139014-6e97-4316-95f7-2c14702540e7',
    'textilien':     '9f0efe69-f502-493f-8679-4e162d534439',
    'sonderabfall':  'ec7c2ce9-b27f-4c27-bbb8-c9e818d90b07',
    # 'sammelstellen': 'b283fb6a-1ad4-4472-bcf9-0d3f135778b7',
})
type_to_id_2021 = dict({
    'papier':        ['266fe85f-3ae0-466a-b6f5-2a8e663893cc', 'b2db05de-beac-437f-9876-a3d94c3270f0'],
    'kehricht':      ['ddc5c2fd-c730-4d55-a88c-69bbe6d5a37e', 'ded0fe8d-74cc-43dc-aeb0-39ec878e2dbc'],
    'karton':        ['e8be896b-8aea-40b7-b042-961273576cd3', '2ae3e825-5b5f-47fd-9838-035f9d625d0e'],
    'gartenabfall':  ['e785a87c-0233-47e9-9a1a-32034e82f519', '65c9778f-2d03-4750-839e-730f68b5d00d'],
    'eTram':         ['88a9bb1b-65db-4b30-a74a-188b0a61b3da', 'e73d06ee-caf0-4057-bc65-41ff99849c8e'],
    'cargotram':     ['43f4613a-f0c2-4036-8902-77a784bde746', 'fa30c8b4-0478-4c0d-a43d-a9a95bb27e70'],
    'textilien':     ['a47e92c9-8e0a-454d-8c4e-2e4d7f6c87b3', '00832eda-1436-4f54-af53-9e1f18fea4a7'],
    'sonderabfall':  ['2886fe2d-9acf-48c3-8414-d4ee6af7460a', '8b9bc1df-84fb-47b7-9d2b-b6a1bc1ccc62'],
    # 'sammelstellen': ['c6c008f4-67b0-4106-a6f1-a2a61c5f890b', '0d59fc55-08df-45ed-a740-a7c4d7b78c2e'],
})
type_to_id = type_to_id_2021

known_types = type_to_id.keys()
known_types.sort()


class BaseHandler(webapp2.RequestHandler):

    @webapp2.cached_property
    def jinja2(self):
        # Returns a Jinja2 renderer cached in the app registry.
        return jinja2.get_jinja2(app=self.app)

    def render_response(self, _template, **context):
        # Renders a template and writes the result to the response.
        rv = self.jinja2.render_template(_template, **context)
        self.response.write(rv)


class GetMeta(BaseHandler):
    def get(self):
        type = self.request.get('type')
        # self.response.charset = 'utf-8'
        url = meta_url(type)
        html = OGDZMetaPage.get_meta_page(type, url)
        if html is None:
            self.response.write("Error loading meta page</br>")
            self.response.write("URL: {}</br>".format(url))
        else:
            self.response.write("URL: {}</br>".format(url))
            html = html.decode('utf-8')
            soup = BeautifulSoup(html, "lxml")
            self.response.write("Title: " + soup.title.string + "<br />\n")
            self.response.write("Description: ")
            # self.response.write(soup.find(id='description'))
            self.response.write("Download: ")
            self.response.write(soup.find(id='dataset-resources')
                                .find_all('a'))


def type_to_csv_url(type):
    foo = 'bioabfall' if type == 'gartenabfall' else type
    id = type_to_id[type]
    if isinstance(id, list):
        return 'https://data.stadt-zuerich.ch/' \
            + 'dataset/%s/resource/%s/download/entsorgungskalender_%s.csv' \
            % (id[0], id[1], string.lower(foo))
    else:
        return 'https://data.stadt-zuerich.ch/' \
            + 'dataset/entsorgungskalender_%s/resource/%s/download/%s.csv' \
            % (type, id, string.lower(foo))


class MainPage(BaseHandler):
    def get(self):
        context = {'zips': ZIPS,
                   'ga_id': GA_ID,
                   'google_ad_client': GOOGLE_AD_CLIENT}
        self.render_response('index.html', **context)


def cal_add_name(cal, name, req):
    # draft-ietf-calext-extensions-01 defines NAME
    params = {'language': 'de'}
    cal.add('X-WR-CALNAME', name, parameters=params)
    params = {'language': 'de'}
    cal.add('NAME', name, parameters=params)


def cal_add_desc(cal, desc, req):
    # draft-ietf-calext-extensions-01 defines DESCRIPTION
    params = {'language': 'de'}
    cal.add('X-WR-CALDESC', desc, parameters=params)
    params = {'language': 'de'}
    cal.add('DESCRIPTION', desc, parameters=params)


class GetCal(BaseHandler):
    def get(self, zip=None, types=None):
        if types is None:
            if self.request.get('types'):
                types = self.request.get('types').split(' ')
            else:
                types = known_types
        else:
            types = types.split('+')
        if zip is None:
            zip = int(self.request.get('zip'))
        else:
            zip = int(zip)
        self.response.headers['Content-Type'] = \
            'text/calendar; charset="utf-8"'
        self.response.headers['Content-Disposition'] = \
            'attachment; filename=' + 'zrcal-' + str(zip) + '.ics'
        cal = icalendar.Calendar()
        cal.add('prodid', '-//zrcal//leinen.ch//')
        cal.add('version', '2.0')
        cal_add_name(cal, 'Entsorgung %d' % (zip), self.request)
        cal_add_desc(cal, ('Entsorgungskalender für PLZ %d.  '
                           + 'Erzeugt von http://zrcal.leinen.ch/ '
                           + 'basierend auf Open Government Data '
                           + 'der Stadt Zürich—https://data.stadt-zuerich.ch/')
                     % (zip), self.request)
        for ret in db.GqlQuery('SELECT * from Abfuhr '
                               'WHERE zip = :1 '
                               'ORDER BY date',
                               zip):
            if ret.type in types:
                cal.add_component(ret.to_icalendar_event())
        self.response.write(cal.to_ical())


class LoadCalendarPage(BaseHandler):
    def get(self):
        if self.request.get('types'):
            types = self.request.get('types').split(' ')
        else:
            if self.request.get('type'):
                types = [self.request.get('type')]
            else:
                types = known_types
        for type in types:
            try:
                parsed = ParsedAbholCSV(type)
                parsed.store()

                self.response.write("<a href=\"%s\">%s</a>: %s<br />\n"
                                    % (type_to_csv_url(type), type,
                                       parsed.size()))
            except KeyError:
                logging.error("Unknown URL for %s" % (type))
                self.response.write('Unknown URL for %s' % (type))


def utf_8_csv_reader(csv_data, dialect=csv.excel, **kwargs):
    csv_reader = csv.reader(csv_data,
                            dialect=dialect, **kwargs)

    for row in csv_reader:
        yield [unicode(cell, 'utf-8') for cell in row]


def month_for_name_de(name):
    try:
        return self.month_for_name_de_dict[name]
    except KeyError:
        logging.error("Unknown month %s (%s), assuming this means March."
                      % (name,
                         ":".join("{0:x}".format(ord(c)) for c in name)))
        return 3


def parse_date(date):

    m = re.match(r'^(\d+)-(\d\d)-(\d\d)$', date)
    if m:
        return datetime.date(int(m.group(1)),
                             int(m.group(2)), int(m.group(3)))
    m = re.match(r'^(..), (\d+)\. ([A-Z].+) (\d+)$', date)
    if m:
        return datetime.date(int(m.group(4)),
                             month_for_name_de(m.group(3)),
                             int(m.group(2)))
    else:
        logging.error("Unparseable date: " + date)


class ParsedAbholCSV:

    """A class representing a parsed CSV file"""

    def __init__(self, type, url=None, reader=None):

        self.month_for_name_de_dict = dict({
            u"Januar":	  1,
            u"Februar":	  2,
            u"März":	  3,
            u"April":	  4,
            u"Mai":	  5,
            u"Juni":	  6,
            u"Juli":	  7,
            u"August":	  8,
            u"September": 9,
            u"Oktober":	 10,
            u"November": 11,
            u"Dezember": 12,
        })

        self.type = type
        # Keep track of earliest and latest events in the CSV
        self.earliest_date = None
        self.latest_date = None
        self.models = []

        if url is None:
            url = type_to_csv_url(type)
        if reader is None:
            logging.warn("Trying to retrieve %s" % (url))
            reader = utf_8_csv_reader(urllib2.urlopen(url),
                                      dialect=csv.excel)

        header = reader.next()

        def note_date(date):
            if self.earliest_date is None or self.earliest_date > date:
                self.earliest_date = date
            if self.latest_date is None or self.latest_date < date:
                self.latest_date = date

        if len(header) == 2:
            for row in reader:
                if len(row) == 0:
                    pass        # The 2016 CSVs end with an empty line.
                else:
                    plz, date = row
                    d = parse_date(date)
                    if plz == '':
                        logging.warn("Missing PLZ in %s" % (url))
                    else:
                        self.models.append(
                            Abfuhr(zip=int(plz), type=type, date=d))
                        note_date(d)
        elif len(header) == 3:
            for row in reader:
                if len(row) == 0:
                    pass        # The 2016 CSVs end with an empty line.
                else:
                    plz, loc, date = row
                    d = parse_date(date)
                    self.models.append(
                        Abfuhr(zip=int(plz), type=type, loc=loc, date=d))
                    note_date(d)
        elif len(header) == 5:
            for row in reader:
                if len(row) == 0:
                    pass        # The 2016 CSVs end with an empty line.
                else:
                    plz, loc, oel, glas, metall = row
                    oel = oel == 'X'
                    glas = glas == 'X'
                    metall = metall == 'X'
                    # self.models.append(
                    #     Abfuhr(zip = int(plz), type = type, date = d))
        else:
            logging.error("URL %s for type %s" +
                          " has %d columns (%s) - cannot understand."
                          % (url, type, len(header), header))

    def store(self):
        db.delete(db.GqlQuery("SELECT * FROM Abfuhr WHERE " +
                              " type = :1 AND date >= :2 AND date <= :3",
                              self.type, self.earliest_date, self.latest_date))
        db.put(self.models)

    def size(self):
        return len(self.models)


config = {'webapp2_extras.jinja2': {
    'template_path': 'templates',
    'environment_args': {'extensions': ['jinja2.ext.i18n']}}}
app = webapp2.WSGIApplication([
        webapp2.Route('/<zip:\d{4}>', handler=GetCal, name='ical'),
        webapp2.Route('/<zip:\d{4}>/<types:.*>', handler=GetCal, name='ical'),
        ('/', MainPage),
        ('/load-calendar', LoadCalendarPage),
        ('/meta-page', GetMeta),
        ], debug=True, config=config)
