# -*- mode: python; coding: utf-8 -*-
#
# This tool generates personalized calendars based on
# Open Government Data.
#
from flask import Flask, request, Response, render_template, \
    send_file, send_from_directory
from flask_babel import Babel
import datetime
import string
from urllib.request import urlopen
from urllib.error import HTTPError
import re
import csv
import codecs
import os
import logging
from google.cloud import ndb
import icalendar


ZIPS = [8001, 8002, 8003, 8004, 8005, 8006, 8008,
        8032, 8037, 8038, 8041, 8044, 8045, 8046,
        8047, 8048, 8049, 8050, 8051, 8052, 8053,
        8055, 8057, 8064]

GA_ID = 'UA-33259788-1'
GOOGLE_AD_CLIENT = 'pub-6118177449333262'

app = Flask(__name__)
ds_client = ndb.Client()


def ndb_wsgi_middleware(wsgi_app):
    def middleware(environ, start_response):
        with ds_client.context():
            return wsgi_app(environ, start_response)

    return middleware


app.wsgi_app = ndb_wsgi_middleware(app.wsgi_app)  # Wrap the app in middleware.

babel = Babel(app)


class Abfuhr(ndb.Model):
    zip = ndb.IntegerProperty(required=True)
    type = ndb.StringProperty(required=True)
    loc = ndb.StringProperty(required=False)
    date = ndb.DateProperty(required=True, indexed=True)

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


KNOWN_TYPES = [
    'papier',
    'kehricht',
    'karton',
    'bioabfall',
    'eTram',
    'cargoTram',
    'sonderabfall',
    'mobiler_recyclinghof',     # starting in 2024
]


OGD_ROOT = 'https://data.stadt-zuerich.ch/'
OGD_TMPL = OGD_ROOT + 'dataset/erz_{}{}/download/{}{}_{}.csv'


def type_to_csv_url(type, year):
    e1 = "entsorgungskalender_"
    e2 = "" if type == "mobiler_recyclinghof" else "entsorgungskalender_"
    return OGD_TMPL.format(e1, type.lower(), e2, type, year)


@app.route('/')
def get_index():
    return render_template('index.html',
                           zips=ZIPS,
                           ga_id=GA_ID,
                           google_ad_client=GOOGLE_AD_CLIENT)


@app.route('/ads.txt')
def get_ads():
    return Response('google.com, {}, DIRECT, f08c47fec0942fa0\n'.format(
        GOOGLE_AD_CLIENT),
                    mimetype='text/plain')


@app.route('/css/<path:path>')
def get_css(path=None):
    return send_from_directory('css', path, mimetype='text/css')


@app.route('/robots.txt')
def get_robots(): return Response('#\n', mimetype='text/plain')


@app.route('/favicon.ico')
def get_favicon(path=None):
    return send_file('static/images/favicon.ico',
                     mimetype='image/vnd.microsoft.icon')


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


@app.route('/<int:zip>')
@app.route('/<int:zip>/<types>')
def get_cal(zip=None, types=None):
    if types is None:
        if request.args.get('types'):
            types = request.args.get('types').split(' ')
        else:
            types = KNOWN_TYPES
    else:
        types = types.split('+')
    if zip is None:
        zip = int(request.args.get('zip'))
    else:
        zip = int(zip)
    cal = icalendar.Calendar()
    cal.add('prodid', '-//zrcal//leinen.ch//')
    cal.add('version', '2.0')
    cal_add_name(cal, 'Entsorgung {}'.format(zip), request)
    cal_add_desc(cal, ('Entsorgungskalender für PLZ {}.  '
                       + 'Erzeugt von http://zrcal.leinen.ch/ '
                       + 'basierend auf Open Government Data '
                       + 'der Stadt Zürich—{}').format(
                           zip, OGD_ROOT),
                 request)
    for ret in Abfuhr.query() \
                     .filter(Abfuhr.zip == zip) \
                     .order(Abfuhr.date):  # .order(Abfuhr.date, Abfuhr.type):
        if ret.type in types:
            cal.add_component(ret.to_icalendar_event())
    return Response(cal.to_ical(),
                    content_type='text/calendar; charset="utf-8"',
                    headers={'Content-Disposition': 'attachment; filename='
                             + 'zrcal-' + str(zip) + '.ics'}
                    )


@app.route('/load-calendar')
def load_calendar():
    result = ''
    if request.args.get('types'):
        types = request.args.get('types').split(' ')
    else:
        if request.args.get('type'):
            types = [request.args.get('type')]
        else:
            types = KNOWN_TYPES
    if request.args.get('year'):
        year = int(request.args.get('year'))
    else:
        # Default the year to the year two months from now.
        # So when this is run in November or December, it will
        # use the predicted URLs for next year.
        year = (datetime.date.today() + datetime.timedelta(days=61)).year

    for type in types:
        try:
            parsed = ParsedAbholCSV(type, year)
            parsed.store()

            result = result + \
                '<a href="{}">{}</a>: {}<br />\n'.format(
                    type_to_csv_url(type, year), type, parsed.size())
        except KeyError:
            logging.error("Unknown URL for {} ({})".format(type, year))
            result = result + 'Unknown URL for {} ({})'.format(type, year)
        except HTTPError as e:
            logging.error("{} trying to get calendar for {} ({})".format(e, type, year))
            result = result + "{} trying to get calendar for {} ({})".format(e, type, year)
    return result


def utf_8_csv_reader(csv_data, dialect=csv.excel, **kwargs):
    return csv.reader(codecs.iterdecode(csv_data, 'utf-8'),
                      dialect=dialect, **kwargs)


def month_for_name_de(name):
    try:
        return self.month_for_name_de_dict[name]
    except KeyError:
        logging.error("Unknown month {} ({}), guessing March.".format(
            name,
            ":".join("{0:x}".format(ord(c)) for c in name)))
        return 3


def parse_date(date, yyyy_dd_mm_sometimes=False):

    m = re.match(r'^(\d+)-(\d\d)-(\d\d)$', date)
    if m:
        # In the year 2023, the official CSVs were apparently created
        # using a process that generated dates in YYYY-DD-MM (instead
        # of YYYY-MM-DD) format, but only in the cases where DD <= 12.
        # Let's fix this!
        #
        if int(m.group(1)) == 2023:
            yyyy_dd_mm_sometimes=True

        if yyyy_dd_mm_sometimes and int(m.group(3)) <= 12:
            return datetime.date(int(m.group(1)),
                                 int(m.group(3)), int(m.group(2)))
        else:
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

    def __init__(self, type, year, url=None, reader=None):

        self.month_for_name_de_dict = dict({
            u"Januar":    1,
            u"Februar":   2,
            u"März":      3,
            u"April":     4,
            u"Mai":       5,
            u"Juni":      6,
            u"Juli":      7,
            u"August":    8,
            u"September": 9,
            u"Oktober":  10,
            u"November": 11,
            u"Dezember": 12,
        })

        self.type = type
        # Keep track of earliest and latest events in the CSV
        self.earliest_date = None
        self.latest_date = None
        self.models = []

        if url is None:
            url = type_to_csv_url(type, year)
        if reader is None:
            logging.warn("Trying to retrieve {}".format(url))
            reader = utf_8_csv_reader(urlopen(url), dialect=csv.excel)

        header = reader.__next__()

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
                        logging.warn("Missing PLZ in {}".format(url))
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
            logging.error(("URL {} for type {}" +
                           " has {} columns ({}) - cannot understand.").format(
                               url, type, len(header), header))

    def store(self):
        ndb.delete_multi(
            Abfuhr.query()
            .filter(Abfuhr.type == self.type)
            .filter(Abfuhr.date >= self.earliest_date)
            .filter(Abfuhr.date <= self.latest_date)
            .fetch(keys_only=True))
        ndb.put_multi(self.models)

    def size(self):
        return len(self.models)
