"""explain sess behavior"""

from datetime import datetime
from urllib.parse import urljoin
from base64 import standard_b64encode
from getpass import getpass
import hashlib
from xml.etree import ElementTree

from numpy import array, fromstring, newaxis

try:
    import requests
except ImportError as import_err:
    requests = import_err  # import_err is local to except-statement

HOST = 'www.ieeg.org'
HTTP = 'https://'
URL_ID = '/services/timeseries/getIdByDataSnapshotName/'
URL_DETAILS = '/services/timeseries/getDataSnapshotTimeSeriesDetails/'
URL_DATA = '/services/timeseries/getUnscaledTimeSeriesSetBinaryRaw/'


SESS = None


class IEEG_org:

    def __init__(self, name):
        global SESS
        if SESS is None:
            SESS = Session()
        self._sess = SESS

        self.filename = name
        self._snapshot = self._sess.get_snapshot(name)
        xml = self._sess.get_dataset(self._snapshot)
        self._details = ElementTree.fromstring(xml).find('details')

    def return_hdr(self):
        chan_name = [chan.find('channelLabel').text for chan in self._details]
        factor = [float(chan.find('voltageConversionFactor').text) for chan in self._details]
        self._factor = array(factor)

        one_chan = self._details[0]
        subj_id = self.filename
        start_time = datetime.fromtimestamp(int(one_chan.find('startTime').text) / 1e6)
        s_freq = float(one_chan.find('sampleRate').text)
        self.s_freq = s_freq
        n_samples = int(one_chan.find('numberOfSamples').text)
        orig = self._details

        self._chan_id = array([chan.find('revisionId').text for chan in self._details])

        return subj_id, start_time, s_freq, chan_name, n_samples, orig

    def return_dat(self, chan, begsam, endsam):
        """order of chan is taken into account by ieeg.org server"""
        start = int(begsam / self.s_freq * 1000000)
        duration = int((endsam - begsam) / self.s_freq * 1000000)
        params = {'start': start, 'duration': duration}

        xml_str = _prepare_xml_str(self._chan_id[chan])
        r = self._sess.get_data(self._snapshot, params, xml_str)

        h = r.headers
        samples_per_row = set(h['samples-per-row'].split(','))
        if not len(samples_per_row) == 1:
            raise ValueError('Not all channels have equal length')
        conv = array([float(x) for x in h['voltage-conversion-factors-mv'].split(',')])

        dat = fromstring(r.content, dtype='>i4')
        n_smp = int(list(samples_per_row)[0])
        # TODO: should we use self._factor
        dat = dat.reshape(-1, n_smp) * conv[:, newaxis]

        return dat

    def return_markers(self):
        return []


class Session:
    def __init__(self, username=None, password=None, password_md5=None):
        if username is None:
            username = input('ieeg.org username:')
        self.username = username

        if password is None and password_md5 is None:
            password = getpass('ieeg.org password:')

        if password:
            self.password = md5(password)
        elif password_md5:
            self.password = password_md5

    def get_snapshot(self, name):
        return self._get_info(URL_ID + name)

    def get_dataset(self, snapshot):
        return self._get_info(URL_DETAILS + snapshot)

    def get_data(self, snapshot, params, xml_str):

        path = URL_DATA + snapshot
        dtime, sig = self._make_signature('POST', path, params, xml_str)
        headers = {'username': self.username,
                   'timestamp': dtime,
                   'signature': sig,
                   'Content-Type': 'application/xml'}
        url = urljoin(HTTP + HOST, path)
        r = requests.post(url, headers=headers, params=params, data=xml_str)
        return r

    def _get_info(self, path):
        dtime, sig = self._make_signature('GET', path)
        headers = {'username': self.username,
                   'timestamp': dtime,
                   'signature': sig,
                   'Content-Type': 'application/xml'}
        url = urljoin(HTTP + HOST, path)

        if isinstance(requests, BaseException):
            raise requests  # import error

        r = requests.get(url, headers=headers)
        return r.content.decode()

    def _make_signature(self, method, urlpath, params=None, xml_str=''):
        if params is None:
            params = {}
        dtime = datetime.now().isoformat()

        params_str = '&'.join(k + '=' + str(v) for k, v in params.items())

        xml_str = _sha256(xml_str)
        to_hash = (self.username, self.password, method, HOST, urlpath,
                   params_str, dtime, xml_str)
        return dtime, _sha256('\n'.join(to_hash))


def _prepare_xml_str(chan_id):
    XML_BEG = ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
               '<timeSeriesIdAndDChecks><timeSeriesIdAndDChecks>')
    XML_END = '</timeSeriesIdAndDChecks></timeSeriesIdAndDChecks>'
    XML_CHAN = ('<timeSeriesIdAndCheck><dataCheck>{}</dataCheck>'
                '<id>{}</id></timeSeriesIdAndCheck>')

    s = XML_BEG
    for i_chan in chan_id:
        s = s + XML_CHAN.format(i_chan, i_chan)
    s = s + XML_END

    return s


def md5(s):
    """ Returns MD5 hashed string """
    m = hashlib.md5(s.encode())
    return m.hexdigest()


def _sha256(s):
    m = hashlib.sha256(s.encode())
    return standard_b64encode(m.digest()).decode()
