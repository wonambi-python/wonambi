"""Class to import ABF2.
Adapted from axonrawio.py in python-neo. Strongly simplified.
"""
from datetime import datetime, timedelta
from json import dump, load
from pathlib import Path
from numpy import c_, empty, float64, NaN, memmap, dtype
from os import SEEK_END, SEEK_SET
from struct import unpack, calcsize


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
            the json file
        """
        with self.filename.open('br') as f:
            orig = _read_header(f)
     
        info = orig


        version = info['fFileVersionNumber']

        # file format
        if info['nDataFormat'] == 0:
            sig_dtype = dtype('i2')
        elif info['nDataFormat'] == 1:
            sig_dtype = dtype('f4')

        nbchannel = info['sections']['ADCSection']['llNumEntries']
        head_offset = info['sections']['DataSection']['uBlockIndex'] * BLOCKSIZE
        totalsize = info['sections']['DataSection']['llNumEntries']  

        mode = info['protocol']['nOperationMode']

        assert mode == 3, 'Mode {} is not supported'.format(mode)

        # read sweep pos
        nbepisod = info['sections']['SynchArraySection']['llNumEntries']
        offset_episode = info['sections']['SynchArraySection']['uBlockIndex'] * BLOCKSIZE

        assert nbepisod == 0

        sampling_rate = 1.e6 / info['protocol']['fADCSequenceInterval']

        from numpy import array
        channel_ids = list(range(nbchannel))

        sig_channels =[]
        adc_nums = []
        for chan_index, chan_id in enumerate(channel_ids):
            ADCInfo = info['listADCInfo'][chan_id]
            name = ADCInfo['ADCChNames'].replace(b' ', b'')
            units = ADCInfo['ADCChUnits'].replace(b'\xb5', b'u').replace(b' ', b'').decode('utf-8')
            adc_num = ADCInfo['nADCNum']
            adc_nums.append(adc_num)

            gain = info['protocol']['fADCRange']
            gain /= info['listADCInfo'][chan_id]['fInstrumentScaleFactor']
            gain /= info['listADCInfo'][chan_id]['fSignalGain']
            gain /= info['listADCInfo'][chan_id]['fADCProgrammableGain']
            gain /= info['protocol']['lADCResolution']
            if info['listADCInfo'][chan_id]['nTelegraphEnable']:
                gain /= info['listADCInfo'][chan_id]['fTelegraphAdditGain']
            offset = info['listADCInfo'][chan_id]['fInstrumentOffset']
            offset -= info['listADCInfo'][chan_id]['fSignalOffset']
            sig_channels.append((name, chan_id, sampling_rate, sig_dtype, units, offset, gain))
            
            
        return (orig['subj_id'], start_time, orig['s_freq'], orig['chan_name'],
                orig['n_samples'], orig)

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
        for those values. It then converts the memmap to a normal numpy array,
        I think, and so it reads the data into memory. However, I'm not 100%
        sure that this is what happens.
        """
        data = memmap(self.filename, dtype=sig_dtype, mode='r', shape=(totalsize,), offset=head_offset)
        
        n_smp = self.memshape[1]
        dat = data[chan, max((begsam, 0)):min((endsam, n_smp))].astype(float64)

        if begsam < 0:

            pad = empty((dat.shape[0], 0 - begsam))
            pad.fill(NaN)
            dat = c_[pad, dat]

        if endsam >= n_smp:

            pad = empty((dat.shape[0], endsam - n_smp))
            pad.fill(NaN)
            dat = c_[dat, pad]

        return dat
    
    def return_markers(self):
        """I don't know if the ABF contains markers at all.
        """
        return []

def _read_header(fid):

    fid.seek(0, SEEK_SET)
    fFileSignature = fid.read(4)
    assert fFileSignature == b'ABF2'

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


    BLOCKSIZE = 512
    # strings sections
    # hack for reading channels names and units
    fid.seek(sections['StringsSection']['uBlockIndex'] * BLOCKSIZE)
    big_string = fid.read(sections['StringsSection']['uBytes'])
    goodstart=-1
    for key in [b'AXENGN', b'clampex', b'Clampex', b'CLAMPEX', b'axoscope', b'Clampfit']:
        #goodstart = big_string.lower().find(key)
        goodstart = big_string.find(key)
        if goodstart!=-1: break
    assert goodstart!=-1, 'This file does not contain clampex, axoscope or clampfit in the header'
    big_string = big_string[goodstart:]
    strings = big_string.split(b'\x00')



    # ADC sections
    header['listADCInfo'] = []
    for i in range(sections['ADCSection']['llNumEntries']):
        # read ADCInfo
        fid.seek(sections['ADCSection']['uBlockIndex'] *
                 BLOCKSIZE + sections['ADCSection']['uBytes'] * i)
        ADCInfo = {}
        for key, fmt in ADCInfoDescription:
            val = unpack(fmt, fid.read(calcsize(fmt)))
            if len(val) == 1:
                ADCInfo[key] = val[0]
            else:
                ADCInfo[key] = val
        ADCInfo['ADCChNames'] = strings[ADCInfo['lADCChannelNameIndex'] - 1]
        ADCInfo['ADCChUnits'] = strings[ADCInfo['lADCUnitsIndex'] - 1]
        header['listADCInfo'].append(ADCInfo)



    # protocol sections
    protocol = {}
    fid.seek(sections['ProtocolSection']['uBlockIndex'] * BLOCKSIZE)
    for key, fmt in protocolInfoDescription:
        val = unpack(fmt, fid.read(calcsize(fmt)))
        if len(val) == 1:
            protocol[key] = val[0]
        else:
            protocol[key] = val
    header['protocol'] = protocol
    header['sProtocolPath'] = strings[header['uProtocolPathIndex']-1]

    # tags
    listTag = []
    for i in range(sections['TagSection']['llNumEntries']):
        fid.seek(sections['TagSection']['uBlockIndex'] *
                 BLOCKSIZE + sections['TagSection']['uBytes'] * i)
        tag = {}
        for key, fmt in TagInfoDescription:
            val = unpack(fmt, fid.read(calcsize(fmt)))
            if len(val) == 1:
                tag[key] = val[0]
            else:
                tag[key] = val
        listTag.append(tag)

    header['listTag'] = listTag

    # DAC sections
    header['listDACInfo'] = []
    for i in range(sections['DACSection']['llNumEntries']):
        # read DACInfo
        fid.seek(sections['DACSection']['uBlockIndex'] *
                 BLOCKSIZE + sections['DACSection']['uBytes'] * i)
        DACInfo = {}
        for key, fmt in DACInfoDescription:
            val = unpack(fmt, fid.read(calcsize(fmt)))
            if len(val) == 1:
                DACInfo[key] = val[0]
            else:
                DACInfo[key] = val
        DACInfo['DACChNames'] = strings[DACInfo['lDACChannelNameIndex']
                                        - 1]
        DACInfo['DACChUnits'] = strings[
            DACInfo['lDACChannelUnitsIndex'] - 1]

        header['listDACInfo'].append(DACInfo)

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
        EpochInfoPerDAC = {}
        for key, fmt in EpochInfoPerDACDescription:
            val = unpack(fmt, fid.read(calcsize(fmt)))
            if len(val) == 1:
                EpochInfoPerDAC[key] = val[0]
            else:
                EpochInfoPerDAC[key] = val

        DACNum = EpochInfoPerDAC['nDACNum']
        EpochNum = EpochInfoPerDAC['nEpochNum']
        # Checking if the key exists, if not, the value is empty
        # so we have to create empty dict to populate
        if DACNum not in header['dictEpochInfoPerDAC']:
            header['dictEpochInfoPerDAC'][DACNum] = {}

        header['dictEpochInfoPerDAC'][DACNum][EpochNum] =\
            EpochInfoPerDAC
            
    return header    
    
    
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

EpochInfoDescription = [
    ('nEpochNum', 'h'),
    ('nDigitalValue', 'h'),
    ('nDigitalTrainValue', 'h'),
    ('nAlternateDigitalValue', 'h'),
    ('nAlternateDigitalTrainValue', 'h'),
    ('bEpochCompression', 'b'),
    ('sUnused', '21s'),
]
