"""Module to show video, if the file format supports it.

"""
from logging import getLogger
lg = getLogger(__name__)

from os.path import join
from subprocess import call

from PyQt4.QtGui import (QFormLayout,
                         QGroupBox,
                         QLabel,
                         QPushButton,
                         QVBoxLayout,
                         QWidget,
                         )
from PyQt4.phonon import Phonon

from ..ioeeg.ktlx import convert_sample_to_video_time, get_date_idx

from phypno.widgets.preferences import Config, FormInt, FormStr


class ConfigVideo(Config):

    def __init__(self, update_widget):
        super().__init__('video', update_widget)

    def create_config(self):

        box0 = QGroupBox('Video')

        box1 = QGroupBox('Fallback Video')
        fallback_text = QLabel('When the embedded video is not available, ' +
                               'it uses VLC as external window.')
        form_layout = QFormLayout()

        self.index['vlc_exe'] = FormStr()  # TODO: FormOpenFile
        self.index['vlc_width'] = FormInt()
        self.index['vlc_height'] = FormInt()

        form_layout = QFormLayout()
        form_layout.addRow('Path to VLC executable', self.index['vlc_exe'])
        form_layout.addRow('VLC width', self.index['vlc_width'])
        form_layout.addRow('VLC height', self.index['vlc_height'])

        fallback_layout = QVBoxLayout()
        fallback_layout.addWidget(fallback_text)
        fallback_layout.addLayout(form_layout)

        box1.setLayout(fallback_layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(box0)
        main_layout.addWidget(box1)
        main_layout.addStretch(1)

        self.setLayout(main_layout)


class Video(QWidget):
    """Widget containing the movie, if available.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    beg_diff : float
        time in ms of the beginning of the first video
    end_diff : float
        time in ms of the end of the last video
    cnt_video : int
        index of the current mediasource
    n_video : int
        total number of videos to play
    video : instance of MediaObject
        the video to show.
    idx_button : instance of QPushButton
        button which starts and stops the video.

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.config = ConfigVideo(self.update_video)

        self.beg_diff = 0
        self.end_diff = 0
        self.cnt_video = 0
        self.n_video = 0

        self.video = None
        self.idx_button = None

        availableMimeTypes = Phonon.BackendCapabilities.availableMimeTypes()
        lg.debug('Phonon MimeTypes: ' + ', '.join(availableMimeTypes))

        if availableMimeTypes:
            self.phonon = True
        else:
            self.phonon = False

        self.create_video()

    def create_video(self):
        """Create video widget."""

        if self.phonon:
            video_widget = Phonon.VideoWidget()
            self.video = Phonon.MediaObject()
            Phonon.createPath(self.video, video_widget)

            self.video.currentSourceChanged.connect(self.next_video)
            self.video.setTickInterval(100)
            self.video.tick.connect(self.stop_video)

        else:
            layout = QVBoxLayout()
            layout.addWidget(QLabel('Embedded video is not available'))
            layout.addWidget(QLabel('VLC will be used instead'))
            layout.addStretch(1)

            video_widget = QWidget()
            video_widget.setLayout(layout)

        self.idx_button = QPushButton('Start')
        self.idx_button.clicked.connect(self.start_stop_video)

        layout = QVBoxLayout()
        layout.addWidget(video_widget)
        layout.addWidget(self.idx_button)
        self.setLayout(layout)

    def stop_video(self, tick):
        """Stop video if tick is more than the end, only for last file.

        Parameters
        ----------
        tick : int
            time in ms from the beginning of the file

        Notes
        -----
        I cannot get prefinishmark to work, this implementation might not be
        as precise (according to the doc), but works fine. It checks that the
        file we are showing is the last one and it's after the time of
        interest.

        """
        if self.cnt_video == self.n_video:
            if tick >= self.end_diff:
                self.idx_button.setText('Start')
                self.video.stop()

    def next_video(self, _):
        """Also runs when file is loaded, so index starts at 2."""
        self.cnt_video += 1
        lg.info('Update video to ' + str(self.cnt_video))

    def start_stop_video(self):
        """Start and stop the video, and change the button.

        Notes
        -----
        It catches expection when video is not in index.

        If it uses VLC, it never changes the button to "STOP", because the
        video works in an external window.

        """
        if 'Start' in self.idx_button.text():
            try:
                self.update_video()
                # in case it has one indexerror once before
                self.idx_button.setText('Start')
            except IndexError as er:
                lg.debug(er)
                self.idx_button.setText('Not Available / Start')
                return
            except OSError as er:
                lg.debug(er)
                self.idx_button.setText('NO VIDEO for this dataset')
                return

            if self.phonon:
                self.idx_button.setText('Stop')
                self.video.play()
                self.video.seek(self.beg_diff)

        elif 'Stop' in self.idx_button.text():
            self.idx_button.setText('Start')
            self.video.stop()

    def update_video(self):
        """Read list of files, convert to video time, and add video to queue.

        Notes
        -----
        Implementation depends on a couple of functions in ioeeg.ktlx. I wish I
        could make it more general, but I don't have other examples and already
        this implementation is pretty complicated as it is.

        """
        d = self.parent.info.dataset

        window_start = self.parent.overview.config.value['window_start']
        window_length = self.parent.overview.config.value['window_length']

        s_freq = d.header['s_freq']
        orig = d.header['orig']

        beg_sam = window_start * s_freq
        end_sam = beg_sam + window_length * s_freq
        lg.info('Samples {}-{} (based on s_freq only)'.format(beg_sam,
                                                              end_sam))

        # time in
        beg_snc = convert_sample_to_video_time(beg_sam, s_freq, *orig['snc'])
        end_snc = convert_sample_to_video_time(end_sam, s_freq, *orig['snc'])
        beg_snc_str = beg_snc.strftime('%H:%M:%S')
        end_snc_str = end_snc.strftime('%H:%M:%S')
        lg.info('Time ' + beg_snc_str + '-' + end_snc_str +
                ' (based on s_freq only)')

        if orig['vtc'] is None:
            raise OSError('No VTC file (and presumably no avi files)')
        mpgfile, start_time, end_time = orig['vtc']

        beg_avi = get_date_idx(beg_snc, start_time, end_time)
        end_avi = get_date_idx(end_snc, start_time, end_time)
        if beg_avi is None or end_avi is None:
            raise IndexError('No video file for time range ' + beg_snc_str +
                             ' - ' + end_snc_str)

        lg.debug('First Video (#{}) {}'.format(beg_avi, mpgfile[beg_avi]))
        lg.debug('Last Video (#{}) {}'.format(end_avi, mpgfile[end_avi]))
        mpgfiles = mpgfile[beg_avi:end_avi + 1]
        full_mpgfiles = [join(d.filename, one_mpg) for one_mpg in mpgfiles]

        beg_diff = (beg_snc - start_time[beg_avi]).total_seconds()
        end_diff = (end_snc - start_time[end_avi]).total_seconds()
        lg.debug('First Video (#{}) starts at {}'.format(beg_avi, beg_diff))
        lg.debug('Last Video (#{}) ends at {}'.format(end_avi, end_diff))

        if self.phonon:
            self.beg_diff = beg_diff * 1e3
            self.end_diff = end_diff * 1e3

            self.video.clear()
            source = []
            for one_mpg in full_mpgfiles:
                source.append(Phonon.MediaSource(one_mpg))

            self.video.enqueue(source)

            self.cnt_video = 0
            self.n_video = len(full_mpgfiles) + 1

        else:
            vlc_exe = self.config.value['vlc_exe']
            vlc_width = self.config.value['vlc_width']
            vlc_height = self.config.value['vlc_height']

            vlc_cmd = '"' + vlc_exe + '" '
            vlc_cmd += '--no-video-title '

            # first file has start time
            vlc_cmd += '"file:///' + full_mpgfiles[0] + '" '
            vlc_cmd += ':start-time=' + str(beg_diff) + ' '

            for one_mpg in full_mpgfiles[1:]:
                vlc_cmd += '"file:///' + one_mpg + '" '

            vlc_cmd += ':stop-time=' + str(end_diff) + ' '
            vlc_cmd += '--width=' + str(vlc_width) + ' '
            vlc_cmd += '--height=' + str(vlc_height) + ' '
            vlc_cmd += '--autoscale '
            vlc_cmd += 'vlc://quit'
            lg.debug(vlc_cmd)
            call(vlc_cmd, shell=True)
