# DICOM Metadata Generator
This metadata generator uses the IPTK web API to watch for new datasets through the */v3/logs/dataset_changes* endpoint. If a previously unseen dataset id is detected, the generator looks for DICOM data within the dataset by searching for *.dcm* files. If a DICOM file is found, all well-known metadata is extracted with the help of [pydicom](https://pydicom.github.io) and saved under metadata specification *32bdac29d951d9def51e3cee10c4f0e582f2a962*.

## Usage
<a href="https://hub.docker.com/r/iptk/generator-dicom/"><img src="https://img.shields.io/docker/build/iptk/generator-dicom.svg"></a>

Either use the *generator.py* script directly, which requires Python 3.6 and the pydicom, redis and requests packages, or use the provided Docker image.

## Configuration
The API endpoint can be specified through the *API_ENDPOINT* environment variable. It must not contain the */v3/* version specification and may contain a username and password to make authenticated calls. A valid endpoint looks like this: *http://user:pass@api.server.com*. If you pass a Redis host in the *REDIS_HOST* environment variable, processed dataset ids will be remembered across restarts.