"""Module to show video, if the file format supports it.

"""
from logging import getLogger
from platform import system

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (QFrame,
                             QGroupBox,
                             QPushButton,
                             QVBoxLayout,
                             QWidget,
                             )

try:
    import vlc
except:
    vlc = False

from .settings import Config

lg = getLogger(__name__)


class ConfigVideo(Config):

    def __init__(self):
        super().__init__('video', None)

    def create_config(self):

        box0 = QGroupBox('Video')

        main_layout = QVBoxLayout()
        main_layout.addWidget(box0)

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
        self.config = ConfigVideo()

        self.cnt_video = 0
        self.n_video = 0
        self.mediaplayer = None

        self.idx_button = None

        if vlc:
            self.create_video()

    def create_video(self):
        """Create video widget."""

        self.instance = vlc.Instance()

        video_widget = QFrame()
        self.mediaplayer = self.instance.media_player_new()
        if system() == 'Linux':
            self.mediaplayer.set_xwindow(video_widget.winId())
        elif system() == 'Windows':
            self.mediaplayer.set_hwnd(video_widget.winId())
        elif system() == 'darwin':  # to test
            self.mediaplayer.set_nsobject(video_widget.winId())
        else:
            lg.warning('unsupported system for video widget')
            return

        self.medialistplayer = vlc.MediaListPlayer()
        self.medialistplayer.set_media_player(self.mediaplayer)
        event_manager = self.medialistplayer.event_manager()
        event_manager.event_attach(vlc.EventType.MediaListPlayerNextItemSet,
                                   self.next_video)

        self.idx_button = QPushButton()
        self.idx_button.setText('Start')
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

        useless?
        """
        if self.cnt_video == self.n_video:
            if tick >= self.end_diff:
                self.idx_button.setText('Start')
                self.video.stop()

    def check_if_finished(self):
        if self.cnt_video == self.n_video:
            if self.mediaplayer.get_time() > self.endsec * 1000:
                self.idx_button.setText('Stop')
                self.medialistplayer.stop()
                self.t.stop()

    def next_video(self, _):
        """Also runs when file is loaded, so index starts at 2."""
        self.cnt_video += 1
        lg.info('Update video to ' + str(self.cnt_video))

    def start_stop_video(self):
        """Start and stop the video, and change the button.
        """
        if self.parent.info.dataset is None:
            self.parent.statusBar().showMessage('No Dataset Loaded')
            return

        # & is added automatically by PyQt, it seems
        if 'Start' in self.idx_button.text().replace('&', ''):
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

        elif 'Stop' in self.idx_button.text():
            self.idx_button.setText('Start')
            self.medialistplayer.stop()
            self.t.stop()

    def update_video(self):
        """Read list of files, convert to video time, and add video to queue.
        """
        window_start = self.parent.value('window_start')
        window_length = self.parent.value('window_length')
        d = self.parent.info.dataset

        videos, begsec, endsec = d.read_videos(window_start,
                                               window_start + window_length)
        
        lg.debug(f'Video: {begsec} - {endsec}')
        self.endsec = endsec
        videos = [str(v) for v in videos]  # make sure it's a str (not path)
        medialist = vlc.MediaList(videos)
        self.medialistplayer.set_media_list(medialist)

        self.cnt_video = 0
        self.n_video = len(videos)

        self.t = QTimer()
        self.t.timeout.connect(self.check_if_finished)
        self.t.start(100)

        self.medialistplayer.play()
        self.mediaplayer.set_time(int(begsec * 1000))
