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

- dateutil (required by icalendar)
- icalendar

This can be done by installing them in the `lib` subdirectory using
`pip install -t lib/ bs4`, etc.

Copyright (c) Simon Leinen, 2012 - 2020

This program is released as free software under the GNU Affero General
Public License.  See file `COPYING' for the licensing conditions.

## Development Hints

These notes are mainly for reminding myself how to develop zrcal.  I
only look at the code about once a year, when new calendars are
published, and it always takes me some time to get started again.

### Update Development Tools

```bash
gcloud components update
```

### Start Development Server

```bash
dev_appserver app.yaml
```

Now you can see the Web UI under http://localhost:8080, and the local
datastore under
[http://localhost:8000/datastore](http://localhost:8000/datastore).

### Load Some Data

Surf to `http://localhost:8080/load-calendar`

Ideally, this will take a long time, and eventually show a summary of
the data that has been loaded.  Or you get an error message, in which
case you need to fix/update the code.  Maybe it's because the nice
folks at Zurich Open Government Data have changed the URL format
again.

### Play Around a Bit

In particular, load a random recycling calendar,
e.g. `http://localhost:8080/8006`.  If the result looks correct, and
includes the recently loaded dates, it is likely that the application
mostly works.

## Deploy

```bash
gcloud app deploy
```

Confirm that you would like to upload the latest source code as the
"default" application.  The upload process takes a while, but then the
new code should become active pretty much instantly.

You should be able to (re)load the latest data by probing
[http://zrcal.leinen.ch/load-calendar](http://zrcal.leinen.ch/load-calendar).
