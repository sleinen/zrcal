FROM gcr.io/google.com/cloudsdktool/cloud-sdk

WORKDIR /build

COPY requirements.txt .

RUN python3 -m pip install -U pycodestyle
RUN python3 -m pip install -U -r requirements.txt
