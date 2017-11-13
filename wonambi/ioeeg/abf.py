"""Class to import ABF2.
Adapted from axonrawio.py in python-neo. Strongly simplified.
"""
from datetime import datetime, timedelta
from numpy import c_, empty, float64, NaN, memmap, dtype, newaxis, array
from os import SEEK_SET
from struct import unpack, calcsize

from .utils import DEFAULT_DATETIME

BLOCKSIZE = 512


class Abf:
    """Class to read abf file.
    Only for ABF2, when the data has no gaps (no episodes).

    Parameters
    ----------
    filename : path to file
        the name of the filename with extension .won
    """
    def __init__(self, filename):
        self.filename = filename

    def return_hdr(self):
        """Return the header for further use.

        Returns
        -------
        subj_id : str
            subject identification code
        start_time : datetime
            start time of the dataset
        s_freq : float
            sampling frequency
        chan_name : list of str
            list of all the channels
        n_samples : int
            number of samples in the dataset
        orig : dict
            the full header
        """
        with self.filename.open('br') as f:
            orig = _read_header(f)

        assert orig['protocol']['nOperationMode'] == 3, 'Only continuous no-gap recordings are supported'
        assert orig['sections']['SynchArraySection']['llNumEntries'] == 0
        assert orig['sections']['SynchArraySection']['uBlockIndex'] == 0

        # file format
        if orig['nDataFormat'] == 0:
            self.dtype = dtype('i2')
        elif orig['nDataFormat'] == 1:
            self.dtype = dtype('f4')

        chan_name = []
        offset = []
        gain = []
        for ch in orig['listADCInfo']:
            chan_name.append(ch['ADCChNames'].decode('utf-8').strip())

            # compute the gain and offset
            ch_gain = orig['protocol']['lADCResolution'] / orig['protocol']['fADCRange']
            ch_gain *= (ch['fInstrumentScaleFactor'] *
                        ch['fSignalGain'] *
                        ch['fADCProgrammableGain'])
            if ch['nTelegraphEnable'] == 1:
                ch_gain *= ch['fTelegraphAdditGain']
            gain.append(1 / ch_gain)

            offset.append(ch['fInstrumentOffset'] -
                          ch['fSignalOffset'])

        self.offset = array(offset)[:, newaxis]
        self.gain = array(gain)[:, newaxis]
        self.head = orig['sections']['DataSection']['uBlockIndex'] * BLOCKSIZE
        self.n_chan = orig['sections']['ADCSection']['llNumEntries']
        assert self.n_chan == len(chan_name)
        self.n_samples = int(orig['sections']['DataSection']['llNumEntries'] /
                             self.n_chan)

        subj_id = self.filename.stem
        try:
            start_time = (datetime.strptime(str(orig['uFileStartDate']), '%Y%m%d') +
                          timedelta(seconds=orig['uFileStartTimeMS'] / 1000))
        except ValueError:  # no time given, use placeholder
            start_time = DEFAULT_DATETIME

        s_freq = 1.e6 / orig['protocol']['fADCSequenceInterval']

        return subj_id, start_time, s_freq, chan_name, self.n_samples, orig

    def return_dat(self, chan, begsam, endsam):
        """Return the data as 2D numpy.ndarray.

        Parameters
        ----------
        chan : int or list
            index (indices) of the channels to read
        begsam : int
            index of the first sample
        endsam : int
            index of the last sample

        Returns
        -------
        numpy.ndarray
            A 2d matrix, with dimension chan X samples. To save memory, the
            data are memory-mapped, and you cannot change the values on disk.

        Notes
        -----
        When asking for an interval outside the data boundaries, it returns NaN
        for those values.
        """
        data = memmap(self.filename, dtype=self.dtype, mode='r', order='F',
                      shape=(self.n_chan, self.n_samples), offset=self.head)

        dat = data[chan, max((begsam, 0)):min((endsam, self.n_samples))].astype(float64)
        dat = (dat + self.offset[chan, :]) * self.gain[chan, :]

        if begsam < 0:

            pad = empty((dat.shape[0], 0 - begsam))
            pad.fill(NaN)
            dat = c_[pad, dat]

        if endsam >= self.n_samples:

            pad = empty((dat.shape[0], endsam - self.n_samples))
            pad.fill(NaN)
            dat = c_[dat, pad]

        return dat

    def return_markers(self):
        """I don't know if the ABF contains markers at all.
        """
        return []


def _read_header(fid):
    """Based on neo/rawio/axonrawio.py, but I only kept of data with no-gaps
    and in one segment.
    """
    fid.seek(0, SEEK_SET)
    fFileSignature = fid.read(4)
    assert fFileSignature == b'ABF2', 'only format ABF2 is currently supported'

    header = {}
    for key, offset, fmt in headerDescriptionV2:
        fid.seek(0 + offset, SEEK_SET)
        val = unpack(fmt, fid.read(calcsize(fmt)))
        if len(val) == 1:
            header[key] = val[0]
        else:
            header[key] = val

    # sections
    sections = {}
    for s, sectionName in enumerate(sectionNames):
        fid.seek(76 + s * 16)
        uBlockIndex, uBytes, llNumEntries = unpack('IIl', fid.read(calcsize('IIl')))
        sections[sectionName] = {}
        sections[sectionName]['uBlockIndex'] = uBlockIndex
        sections[sectionName]['uBytes'] = uBytes
        sections[sectionName]['llNumEntries'] = llNumEntries
    header['sections'] = sections

    # strings sections
    # hack for reading channels names and units
    fid.seek(sections['StringsSection']['uBlockIndex'] * BLOCKSIZE)
    big_string = fid.read(sections['StringsSection']['uBytes'])
    goodstart = -1
    for key in [b'AXENGN', b'clampex', b'Clampex', b'CLAMPEX', b'axoscope', b'Clampfit']:
        goodstart = big_string.find(key)
        if goodstart != -1:
            break
    assert goodstart != -1, 'This file does not contain clampex, axoscope or clampfit in the header'
    big_string = big_string[goodstart:]
    strings = big_string.split(b'\x00')

    # ADC sections
    header['listADCInfo'] = []
    for i in range(sections['ADCSection']['llNumEntries']):
        # read ADCInfo
        fid.seek(sections['ADCSection']['uBlockIndex'] *
                 BLOCKSIZE + sections['ADCSection']['uBytes'] * i)
        ADCInfo = _read_info_as_dict(fid, ADCInfoDescription)
        ADCInfo['ADCChNames'] = strings[ADCInfo['lADCChannelNameIndex'] - 1]
        ADCInfo['ADCChUnits'] = strings[ADCInfo['lADCUnitsIndex'] - 1]
        header['listADCInfo'].append(ADCInfo)

    # protocol sections
    fid.seek(sections['ProtocolSection']['uBlockIndex'] * BLOCKSIZE)
    header['protocol'] = _read_info_as_dict(fid, protocolInfoDescription)
    header['sProtocolPath'] = strings[header['uProtocolPathIndex'] - 1]

    # DAC sections
    header['listDACInfo'] = []
    for i in range(sections['DACSection']['llNumEntries']):
        # read DACInfo
        fid.seek(sections['DACSection']['uBlockIndex'] *
                 BLOCKSIZE + sections['DACSection']['uBytes'] * i)
        DACInfo = _read_info_as_dict(fid, DACInfoDescription)
        DACInfo['DACChNames'] = strings[DACInfo['lDACChannelNameIndex'] - 1]
        DACInfo['DACChUnits'] = strings[
            DACInfo['lDACChannelUnitsIndex'] - 1]

        header['listDACInfo'].append(DACInfo)

    """ Not present in test file. No tests, no code.
    # tags
    listTag = []
    for i in range(sections['TagSection']['llNumEntries']):
        fid.seek(sections['TagSection']['uBlockIndex'] *
                 BLOCKSIZE + sections['TagSection']['uBytes'] * i)
        tag = _read_info_as_dict(fid, TagInfoDescription)
        listTag.append(tag)

    header['listTag'] = listTag

    # EpochPerDAC  sections
    # header['dictEpochInfoPerDAC'] is dict of dicts:
    #  - the first index is the DAC number
    #  - the second index is the epoch number
    # It has to be done like that because data may not exist
    # and may not be in sorted order
    header['dictEpochInfoPerDAC'] = {}
    for i in range(sections['EpochPerDACSection']['llNumEntries']):
        #  read DACInfo
        fid.seek(sections['EpochPerDACSection']['uBlockIndex'] *
                 BLOCKSIZE +
                 sections['EpochPerDACSection']['uBytes'] * i)
        EpochInfoPerDAC = _read_info_as_dict(fid, EpochInfoPerDACDescription)
        DACNum = EpochInfoPerDAC['nDACNum']
        EpochNum = EpochInfoPerDAC['nEpochNum']
        # Checking if the key exists, if not, the value is empty
        # so we have to create empty dict to populate
        if DACNum not in header['dictEpochInfoPerDAC']:
            header['dictEpochInfoPerDAC'][DACNum] = {}

        header['dictEpochInfoPerDAC'][DACNum][EpochNum] =\
            EpochInfoPerDAC
    """

    return header


def _read_info_as_dict(fid, values):
    """Convenience function to read info in axon data to a nicely organized
    dict.
    """
    output = {}
    for key, fmt in values:
        val = unpack(fmt, fid.read(calcsize(fmt)))
        if len(val) == 1:
            output[key] = val[0]
        else:
            output[key] = val
    return output


headerDescriptionV2 = [
    ('fFileSignature', 0, '4s'),
    ('fFileVersionNumber', 4, '4b'),
    ('uFileInfoSize', 8, 'I'),
    ('lActualEpisodes', 12, 'I'),
    ('uFileStartDate', 16, 'I'),
    ('uFileStartTimeMS', 20, 'I'),
    ('uStopwatchTime', 24, 'I'),
    ('nFileType', 28, 'H'),
    ('nDataFormat', 30, 'H'),
    ('nSimultaneousScan', 32, 'H'),
    ('nCRCEnable', 34, 'H'),
    ('uFileCRC', 36, 'I'),
    ('FileGUID', 40, 'I'),
    ('uCreatorVersion', 56, 'I'),
    ('uCreatorNameIndex', 60, 'I'),
    ('uModifierVersion', 64, 'I'),
    ('uModifierNameIndex', 68, 'I'),
    ('uProtocolPathIndex', 72, 'I'),
    ]


sectionNames = [
    'ProtocolSection',
    'ADCSection',
    'DACSection',
    'EpochSection',
    'ADCPerDACSection',
    'EpochPerDACSection',
    'UserListSection',
    'StatsRegionSection',
    'MathSection',
    'StringsSection',
    'DataSection',
    'TagSection',
    'ScopeSection',
    'DeltaSection',
    'VoiceTagSection',
    'SynchArraySection',
    'AnnotationSection',
    'StatsSection',
    ]


protocolInfoDescription = [
    ('nOperationMode', 'h'),
    ('fADCSequenceInterval', 'f'),
    ('bEnableFileCompression', 'b'),
    ('sUnused1', '3s'),
    ('uFileCompressionRatio', 'I'),
    ('fSynchTimeUnit', 'f'),
    ('fSecondsPerRun', 'f'),
    ('lNumSamplesPerEpisode', 'i'),
    ('lPreTriggerSamples', 'i'),
    ('lEpisodesPerRun', 'i'),
    ('lRunsPerTrial', 'i'),
    ('lNumberOfTrials', 'i'),
    ('nAveragingMode', 'h'),
    ('nUndoRunCount', 'h'),
    ('nFirstEpisodeInRun', 'h'),
    ('fTriggerThreshold', 'f'),
    ('nTriggerSource', 'h'),
    ('nTriggerAction', 'h'),
    ('nTriggerPolarity', 'h'),
    ('fScopeOutputInterval', 'f'),
    ('fEpisodeStartToStart', 'f'),
    ('fRunStartToStart', 'f'),
    ('lAverageCount', 'i'),
    ('fTrialStartToStart', 'f'),
    ('nAutoTriggerStrategy', 'h'),
    ('fFirstRunDelayS', 'f'),
    ('nChannelStatsStrategy', 'h'),
    ('lSamplesPerTrace', 'i'),
    ('lStartDisplayNum', 'i'),
    ('lFinishDisplayNum', 'i'),
    ('nShowPNRawData', 'h'),
    ('fStatisticsPeriod', 'f'),
    ('lStatisticsMeasurements', 'i'),
    ('nStatisticsSaveStrategy', 'h'),
    ('fADCRange', 'f'),
    ('fDACRange', 'f'),
    ('lADCResolution', 'i'),
    ('lDACResolution', 'i'),
    ('nExperimentType', 'h'),
    ('nManualInfoStrategy', 'h'),
    ('nCommentsEnable', 'h'),
    ('lFileCommentIndex', 'i'),
    ('nAutoAnalyseEnable', 'h'),
    ('nSignalType', 'h'),
    ('nDigitalEnable', 'h'),
    ('nActiveDACChannel', 'h'),
    ('nDigitalHolding', 'h'),
    ('nDigitalInterEpisode', 'h'),
    ('nDigitalDACChannel', 'h'),
    ('nDigitalTrainActiveLogic', 'h'),
    ('nStatsEnable', 'h'),
    ('nStatisticsClearStrategy', 'h'),
    ('nLevelHysteresis', 'h'),
    ('lTimeHysteresis', 'i'),
    ('nAllowExternalTags', 'h'),
    ('nAverageAlgorithm', 'h'),
    ('fAverageWeighting', 'f'),
    ('nUndoPromptStrategy', 'h'),
    ('nTrialTriggerSource', 'h'),
    ('nStatisticsDisplayStrategy', 'h'),
    ('nExternalTagType', 'h'),
    ('nScopeTriggerOut', 'h'),
    ('nLTPType', 'h'),
    ('nAlternateDACOutputState', 'h'),
    ('nAlternateDigitalOutputState', 'h'),
    ('fCellID', '3f'),
    ('nDigitizerADCs', 'h'),
    ('nDigitizerDACs', 'h'),
    ('nDigitizerTotalDigitalOuts', 'h'),
    ('nDigitizerSynchDigitalOuts', 'h'),
    ('nDigitizerType', 'h'),
    ]


ADCInfoDescription = [
    ('nADCNum', 'h'),
    ('nTelegraphEnable', 'h'),
    ('nTelegraphInstrument', 'h'),
    ('fTelegraphAdditGain', 'f'),
    ('fTelegraphFilter', 'f'),
    ('fTelegraphMembraneCap', 'f'),
    ('nTelegraphMode', 'h'),
    ('fTelegraphAccessResistance', 'f'),
    ('nADCPtoLChannelMap', 'h'),
    ('nADCSamplingSeq', 'h'),
    ('fADCProgrammableGain', 'f'),
    ('fADCDisplayAmplification', 'f'),
    ('fADCDisplayOffset', 'f'),
    ('fInstrumentScaleFactor', 'f'),
    ('fInstrumentOffset', 'f'),
    ('fSignalGain', 'f'),
    ('fSignalOffset', 'f'),
    ('fSignalLowpassFilter', 'f'),
    ('fSignalHighpassFilter', 'f'),
    ('nLowpassFilterType', 'b'),
    ('nHighpassFilterType', 'b'),
    ('fPostProcessLowpassFilter', 'f'),
    ('nPostProcessLowpassFilterType', 'c'),
    ('bEnabledDuringPN', 'b'),
    ('nStatsChannelPolarity', 'h'),
    ('lADCChannelNameIndex', 'i'),
    ('lADCUnitsIndex', 'i'),
    ]


TagInfoDescription = [
    ('lTagTime', 'i'),
    ('sComment', '56s'),
    ('nTagType', 'h'),
    ('nVoiceTagNumber_or_AnnotationIndex', 'h'),
    ]


DACInfoDescription = [
    ('nDACNum', 'h'),
    ('nTelegraphDACScaleFactorEnable', 'h'),
    ('fInstrumentHoldingLevel', 'f'),
    ('fDACScaleFactor', 'f'),
    ('fDACHoldingLevel', 'f'),
    ('fDACCalibrationFactor', 'f'),
    ('fDACCalibrationOffset', 'f'),
    ('lDACChannelNameIndex', 'i'),
    ('lDACChannelUnitsIndex', 'i'),
    ('lDACFilePtr', 'i'),
    ('lDACFileNumEpisodes', 'i'),
    ('nWaveformEnable', 'h'),
    ('nWaveformSource', 'h'),
    ('nInterEpisodeLevel', 'h'),
    ('fDACFileScale', 'f'),
    ('fDACFileOffset', 'f'),
    ('lDACFileEpisodeNum', 'i'),
    ('nDACFileADCNum', 'h'),
    ('nConditEnable', 'h'),
    ('lConditNumPulses', 'i'),
    ('fBaselineDuration', 'f'),
    ('fBaselineLevel', 'f'),
    ('fStepDuration', 'f'),
    ('fStepLevel', 'f'),
    ('fPostTrainPeriod', 'f'),
    ('fPostTrainLevel', 'f'),
    ('nMembTestEnable', 'h'),
    ('nLeakSubtractType', 'h'),
    ('nPNPolarity', 'h'),
    ('fPNHoldingLevel', 'f'),
    ('nPNNumADCChannels', 'h'),
    ('nPNPosition', 'h'),
    ('nPNNumPulses', 'h'),
    ('fPNSettlingTime', 'f'),
    ('fPNInterpulse', 'f'),
    ('nLTPUsageOfDAC', 'h'),
    ('nLTPPresynapticPulses', 'h'),
    ('lDACFilePathIndex', 'i'),
    ('fMembTestPreSettlingTimeMS', 'f'),
    ('fMembTestPostSettlingTimeMS', 'f'),
    ('nLeakSubtractADCIndex', 'h'),
    ('sUnused', '124s'),
    ]


EpochInfoPerDACDescription = [
    ('nEpochNum', 'h'),
    ('nDACNum', 'h'),
    ('nEpochType', 'h'),
    ('fEpochInitLevel', 'f'),
    ('fEpochLevelInc', 'f'),
    ('lEpochInitDuration', 'i'),
    ('lEpochDurationInc', 'i'),
    ('lEpochPulsePeriod', 'i'),
    ('lEpochPulseWidth', 'i'),
    ('sUnused', '18s'),
    ]
