from logging import getLogger
lg = getLogger(__name__)

from os.path import join

from PyQt4.QtGui import (QPushButton,
                          QVBoxLayout,
                          QWidget,
                          )
from PyQt4.phonon import Phonon

from ..ioeeg.ktlx import convert_sample_to_video_time, get_date_idx


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

        self.beg_diff = 0
        self.end_diff = 0
        self.cnt_video = 0
        self.n_video = 0

        self.video = None
        self.idx_button = None
        self.create_video()

    def create_video(self):
        """Create video widget."""
        video_widget = Phonon.VideoWidget()
        self.video = Phonon.MediaObject()
        Phonon.createPath(self.video, video_widget)

        self.idx_button = QPushButton('Start')
        self.idx_button.clicked.connect(self.start_stop_video)

        self.video.currentSourceChanged.connect(self.next_video)
        self.video.setTickInterval(100)
        self.video.tick.connect(self.stop_video)

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

        """
        if 'Start' in self.idx_button.text():
            try:
                self.update_video()
            except IndexError as er:
                lg.debug(er)
                self.idx_button.setText('Not Available / Start')
                return
            except OSError as er:
                lg.debug(er)
                self.idx_button.setText('NO VIDEO for this dataset')
                return

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

        window_start = self.parent.overview.window_start
        window_length = self.parent.overview.window_length

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
        selected_mpgfile = mpgfile[beg_avi:end_avi + 1]

        beg_diff = (beg_snc - start_time[beg_avi]).total_seconds()
        end_diff = (end_snc - start_time[end_avi]).total_seconds()
        lg.debug('First Video (#{}) starts at {}'.format(beg_avi, beg_diff))
        lg.debug('Last Video (#{}) ends at {}'.format(end_avi, end_diff))

        self.beg_diff = beg_diff * 1e3
        self.end_diff = end_diff * 1e3

        self.video.clear()
        source = []
        for one_mpg in selected_mpgfile:
            source.append(Phonon.MediaSource(join(d.filename, one_mpg)))

        self.video.enqueue(source)

        self.cnt_video = 0
        self.n_video = len(selected_mpgfile) + 1
