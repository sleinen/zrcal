# -*- mode: python; coding: utf-8 -*-
#
# This tool generates personalized calendars based on
# Open Government Data.
#
from flask import Flask, request, Response, render_template
from flask_babel import Babel
import datetime
import string
from urllib.request import urlopen
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
GOOGLE_AD_CLIENT = 'ca-pub-6118177449333262'

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
    'papier':        ['266fe85f-3ae0-466a-b6f5-2a8e663893cc',
                      'b2db05de-beac-437f-9876-a3d94c3270f0'],
    'kehricht':      ['ddc5c2fd-c730-4d55-a88c-69bbe6d5a37e',
                      'ded0fe8d-74cc-43dc-aeb0-39ec878e2dbc'],
    'karton':        ['e8be896b-8aea-40b7-b042-961273576cd3',
                      '2ae3e825-5b5f-47fd-9838-035f9d625d0e'],
    'gartenabfall':  ['e785a87c-0233-47e9-9a1a-32034e82f519',
                      '65c9778f-2d03-4750-839e-730f68b5d00d'],
    'eTram':         ['88a9bb1b-65db-4b30-a74a-188b0a61b3da',
                      'e73d06ee-caf0-4057-bc65-41ff99849c8e'],
    'cargotram':     ['43f4613a-f0c2-4036-8902-77a784bde746',
                      'fa30c8b4-0478-4c0d-a43d-a9a95bb27e70'],
    'textilien':     ['a47e92c9-8e0a-454d-8c4e-2e4d7f6c87b3',
                      '00832eda-1436-4f54-af53-9e1f18fea4a7'],
    'sonderabfall':  ['2886fe2d-9acf-48c3-8414-d4ee6af7460a',
                      '8b9bc1df-84fb-47b7-9d2b-b6a1bc1ccc62'],
    # 'sammelstellen': ['c6c008f4-67b0-4106-a6f1-a2a61c5f890b',
    #                     '0d59fc55-08df-45ed-a740-a7c4d7b78c2e'],
})
type_to_id_2022 = dict({
    'papier':        {'year': 2022},
    'kehricht':      {'year': 2022},
    'karton':        {'year': 2022},
    'gartenabfall':  {'year': 2022},
    'eTram':         {'year': 2022},
    'cargoTram':     {'year': 2022},
    # 'textilien':     {'year': 2022}, # not found on 27 December 2021... maybe later?
    'sonderabfall':  {'year': 2022},
})

type_to_id = type_to_id_2022

known_types = sorted(type_to_id.keys())


OGD_ROOT = 'https://data.stadt-zuerich.ch/'
OGD_BASE = OGD_ROOT + 'dataset/'
OGD_TMPL_1 = OGD_BASE + 'entsorgungskalender_{}/resource/{}/download/{}.csv'
OGD_TMPL_2 = OGD_BASE + '{}/resource/{}/download/entsorgungskalender_{}.csv'
OGD_TMPL_3 = OGD_BASE + 'erz_entsorgungskalender_{}/download/entsorgungskalender_{}_{}.csv'


def type_to_csv_url(type):
    foo = 'bioabfall' if type == 'gartenabfall' else type
    id = type_to_id[type]
    if isinstance(id, list):
        return OGD_TMPL_2.format(
            id[0], id[1], foo.lower())
    elif isinstance(id, dict):
        return OGD_TMPL_3.format(
            foo.lower(), foo, id['year'])
    else:
        return OGD_TMPL_1.format(
            type, id, foo.lower())


@app.route('/')
def get_index():
    return render_template('index.html',
                           zips=ZIPS,
                           ga_id=GA_ID,
                           google_ad_client=GOOGLE_AD_CLIENT)


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
            types = known_types
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
            types = known_types
    for type in types:
        try:
            parsed = ParsedAbholCSV(type)
            parsed.store()

            result = result + \
                '<a href="{}">{}</a>: {}<br />\n'.format(
                    type_to_csv_url(type), type, parsed.size())
        except KeyError:
            logging.error("Unknown URL for {}".format(type))
            result = result + 'Unknown URL for {}'.format(type)
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
            url = type_to_csv_url(type)
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
