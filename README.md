# zrcal - Zurich Recycling Calendar

A Web application that can mine Open Government Data published by the
City of Zurich on
[data.stadt-zuerich.ch](https://data.stadt-zuerich.ch/), in particular
the schedules for the collection of various types of waste.  Users can
then generate personalized calendars depending on where they live.
These calendars are in standard iCalendar format, and can be imported
in common calendar tools.

## INSTALLATION

This application can be deployed on Google App Engine under the Python
2.7 runtime.  Beyond what is offered by that environment, the
following libraries need to be uploaded:

- bs4 (BeautifulSoup)
- dateutil (required by icalendar)
- icalendar

This can be done by installing them in the `lib` subdirectory using
`pip install -t lib/ bs4`, etc.

Copyright (c) Simon Leinen, 2012 - 2018

This program is released as free software under the GNU Affero General
Public License.  See file `COPYING' for the licensing conditions.
