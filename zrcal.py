# -*- mode: python; coding: utf-8 -*-
###
### This tool generates personalized calendars based on Open
### Government Data.
###
import datetime
import urllib2
import wsgiref.handlers
import re
import csv
import webapp2
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
import icalendar
from bs4 import BeautifulSoup

class Abfuhr(db.Model):
    zip = db.IntegerProperty(required=True)
    type = db.StringProperty(required=True)
    loc = db.StringProperty(required=False)
    date = db.DateProperty(required=True, indexed=True)

    def to_icalendar_event(self):
        ev = icalendar.Event()
        ev.add('summary', self.type)
        if self.date and isinstance(self.date, datetime.date):
            ev.add('dtstart', self.date)
        if self.loc:
            ev.add('location', self.loc + ', ' + str(self.zip))
        else:
            ev.add('location', str(self.zip))
        return ev

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
            meta = cls(key_name = type,
                       type = type,
                       url = url,
                       contents = urllib2.urlopen(url).read())
            meta.put()
            return meta.contents

def meta_url(type):
    return 'http://data.stadt-zuerich.ch/portal/de/index/ogd/daten/entsorgungskalender_%s.html' % type

type_to_tag = dict({
        'papier':        'JsBezax',
        'kehricht':      'N88dzax',
        'karton':        'bkioKlI',
        'gartenabfall':  'EMV3p0n',
        'eTram':         'TYcmIjG',
        'cargotram':     'G6doKlI',
        'textilien':     'RzGSePc',
        'sonderabfall':  'aPGSePc',
        'sammelstellen': '9B9mIjG' })
known_types = type_to_tag.keys()
known_types.sort()

class GetMeta(webapp2.RequestHandler):
    def get(self):
        type = self.request.get('type')
        # self.response.charset = 'utf-8'
        url = meta_url(type)
        html = OGDZMetaPage.get_meta_page(type, url).decode('utf-8')
        soup = BeautifulSoup(html)
        self.response.out.write("Title: " + soup.title.string + "<br />\n")
        self.response.out.write("Description: ")
        # self.response.out.write(soup.find(id='description'))
        self.response.out.write("Download: ")
        self.response.out.write(soup.find(id='download').find_all('a'))

def type_to_csv_url(type):
    return 'http://data.stadt-zuerich.ch/ogd.%s.link' % type_to_tag[type]

month_for_name_de_dict = dict({
        'Januar':	 1,
        'Februar':	 2,
        'März':		 3,
        'April':	 4,
        'Mai':		 5,
        'Juni':		 6,
        'Juli':		 7,
        'August':	 8,
        'September':	 9,
        'Oktober':	10,
        'November':	11,
        'Dezember':	12,
})

def month_for_name_de(name):
    return month_for_name_de_dict[name]

class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.out.write('<html><body>')
        for type in known_types:
            self.response.out.write('<a href="%s">%s</a><br />'
                                    % (meta_url(type), type))
        self.response.out.write('</body></html>')

class GetCalPage(webapp2.RequestHandler):
    def get(self):
        zip = 8044
        self.response.out.write('<html><body>')
        for ret in db.GqlQuery('SELECT * from Abfuhr ' 'WHERE zip = :1 ', zip):
            self.response.out.write(str(ret.date) + ": " + str(ret.type)
                                    + '<br />')
        self.response.out.write('</body></html>')

class GetCal(webapp2.RequestHandler):
    def get(self, zip=None, types=None):
        if types == None:
            if self.request.get('types'):
                types = self.request.get('types').split(' ')
            else:
                types = known_types
        else:
            types = types.split('+')
        if zip == None:
            zip = int(self.request.get('zip'))
        else:
            zip = int(zip)
        self.response.headers['Content-Type'] = 'text/calendar'
        self.response.headers['Content-Disposition'] = 'attachment; filename=' + 'zrcal-' + str(zip) + '.ics'
        cal = icalendar.Calendar()
        cal.add('prodid', '-//zrcal//leinen.ch//')
        cal.add('version', '2.0')
        for ret in db.GqlQuery('SELECT * from Abfuhr '
                               'WHERE zip = :1 '
                               'ORDER BY date',
                               zip):
            if ret.type in types:
                cal.add_component(ret.to_icalendar_event())
        self.response.out.write(cal.to_ical())

class LoadCalendarPage(webapp2.RequestHandler):
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
                self.response.out.write('<a href="%s">%s</a>'
                                        % (type_to_csv_url(type), type))
                self.response.out.write('File: %s'
                                        % parse_abhol_csv(type))
            except KeyError:
                self.response.out.write('UNKNOWN URL FOR %s' % (type))

def iso_8859_1_csv_reader(csv_data, dialect=csv.excel, **kwargs):
    csv_reader = csv.reader(iso_8859_1_utf_8_transcoder(csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        yield [unicode(cell, 'utf-8') for cell in row]

def iso_8859_1_utf_8_transcoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.decode('iso-8859-1').encode('utf-8')

def parse_abhol_csv(type):
    url = type_to_csv_url(type)
    db.delete(db.GqlQuery("SELECT * FROM Abfuhr WHERE type = :1", type))
    r = iso_8859_1_csv_reader(urllib2.urlopen(url), dialect='excel', )
    header = r.next()
    if len(header) == 3:
        for row in r:
            plz, loc, date = row
            d = parse_date(date)
            a = Abfuhr(zip = int(plz), type = type, loc = loc, date = d)
            a.put()
    elif len(header) == 5:
        for row in r:
            plz, loc, oel, glas, metall = row
            oel = oel == 'X'
            glas = glas == 'X'
            metall = metall == 'X'
            # a = Abfuhr(zip = int(plz), type = type, date = d)
            # a.put()
    else:
        for row in r:
            plz, date = row
            d = parse_date(date)
            a = Abfuhr(zip = int(plz), type = type, date = d)
            a.put()
    return 'Done.'

def parse_date(date):
    m = re.match(r'^(..), (\d+)\. ([A-Z][a-z]+) (\d+)$', date)
    return datetime.date(int(m.group(4)), month_for_name_de(m.group(3)), int(m.group(2)))

app = webapp2.WSGIApplication([
        webapp2.Route('/<zip:\d{4}>', handler=GetCal, name='ical'),
        webapp2.Route('/<zip:\d{4}>/<types:.*>', handler=GetCal, name='ical'),
        ('/', MainPage),
        ('/load-calendar', LoadCalendarPage),
        ('/getcal', GetCalPage),
        ('/geticalendar', GetCal),
        ('/meta-page', GetMeta),
        ], debug=True)
