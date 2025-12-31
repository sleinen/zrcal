# zrcal - Zurich Recycling Calendar

A Web application that can mine Open Government Data published by the
City of Zurich on
[data.stadt-zuerich.ch](https://data.stadt-zuerich.ch/), in particular
the schedules for the collection of various types of waste.  Users can
then generate personalized calendars depending on where they live.
These calendars are in standard iCalendar format, and can be imported
in common calendar tools.

## INSTALLATION

This application can be deployed on Google App Engine.  See below for
instructions.

Copyright (c) Simon Leinen, 2012 - 2025

This program is released as free software under the GNU Affero General
Public License.  See file `COPYING' for the licensing conditions.

## Development Hints

These notes are mainly for reminding myself how to develop zrcal.  I
only look at the code about once a year, when new calendars are
published, and it always takes me some time to get started again.

### Update Development Tools

```bash
gcloud components install app-engine-python app-engine-python-extras cloud-datastore-emulator
gcloud components update
```

### Create venv (Python 3.x)

```bash
python3 -m venv venv_py3
source venv_py3/bin/activate
pip install -U -r requirements.txt
```

### Start Local Datastore Emulator

```bash
gcloud beta emulators datastore start
eval $(gcloud beta emulators datastore env-init)
```

#### Alternatively: Authenticate to Datastore Service

You can omit these steps and set the `GOOGLE_APPLICATION_CREDENTIALS`
environment variable instead (see
[instructions](https://cloud.google.com/datastore/docs/reference/libraries#command-line))
to let the development application access the live datastore.  This is
a bit dangerous in that operations that modify the datastore
(e.g. `/load-calendar`) will affect the live application.

### Start Development Server

```bash
FLASK_APP=main FLASK_DEBUG=1 flask run
```

Now you can see the Web UI under http://localhost:5000.

### Load Some Data

Surf to `http://localhost:5000/load-calendar`

Ideally, this will take a long time, and eventually show a summary of
the data that has been loaded.  Or you get an error message, in which
case you need to fix/update the code.  Maybe it's because the nice
folks at Zurich Open Government Data have changed the URL format
again.

If you get a Python backtrace showing a certificate validation error
(i.e. containing `ssl.SSLCertVerificationError:`), you can retry with
`?insecure=1` appended to the URL.

### Play Around a Bit

In particular, load a random recycling calendar,
e.g. `http://localhost:5000/8006`.  If the result looks correct, and
includes the recently loaded dates, it is likely that the application
mostly works.

## Deploy

```bash
gcloud app deploy
```

Confirm that you would like to upload the latest source code as the
"default" application.  The upload process takes a while, but then the
new code should become active pretty much instantly.

You should be able to (re)load the latest data by probing the
`/load-calendar` path under
[http://zrcal.leinen.ch/](http://zrcal.leinen.ch/).
