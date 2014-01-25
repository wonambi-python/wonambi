from logging import getLogger
lg = getLogger(__name__)

from PySide.QtGui import (QPushButton,
                          QVBoxLayout,
                          QWidget,
                          )
from PySide.phonon import Phonon


def _convert_movie_to_relative_time(begsam, endsam, movie, s_freq):
    """Convert absolute time to the relative time of the single movie files.

    Parameters
    ----------
    begsam : int
        sample at the beginning.
    endsam : int
        sample at the end.
    movie : list of dict
        list of movies, with filename, start_sample, end_sample
    s_freq : int or float
        sampling frequency to convert samples into s.

    Returns
    -------
    all_movie : list of dict
        information in relative time about the movie files.

    """
    all_movie = []
    for m in movie:
        if begsam < m['start_sample']:
            if endsam > m['end_sample']:
                all_movie.append({'filename': m['filename'],
                                  'rel_start': 0,
                                  'rel_end': 0})
            elif endsam > m['start_sample'] and endsam < m['end_sample']:
                all_movie.append({'filename': m['filename'],
                                  'rel_start': 0,
                                  'rel_end': (m['end_sample'] -
                                              endsam) / s_freq})

        elif begsam > m['start_sample']:
            if begsam < m['end_sample'] and endsam > m['end_sample']:
                all_movie.append({'filename': m['filename'],
                                  'rel_start': (begsam -
                                                m['start_sample']) / s_freq,
                                  'rel_end': 0})
            elif endsam < m['end_sample']:
                all_movie.append({'filename': m['filename'],
                                  'rel_start': (begsam -
                                                m['start_sample']) / s_freq,
                                  'rel_end': (m['end_sample'] -
                                              endsam) / s_freq})
    return all_movie


class Video(QWidget):
    """Widget containing the movie, if available.

    Attributes
    ----------
    parent : instance of QMainWindow
        the main window.
    movie_info : list of dict
        information in relative time about the movie files.
    video : instance of MediaObject
        the video to show.
    widget : instance of VideoWidget
        the widget containing the video.
    button : instance of QPushButton
        button which starts and stops the video.

    """
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.movie_info = None

        self.widget = Phonon.VideoWidget()
        self.video = Phonon.MediaObject()
        Phonon.createPath(self.video, self.widget)
        self.button = QPushButton('Start')
        self.button.clicked.connect(self.start_stop)

        layout = QVBoxLayout()
        layout.addWidget(self.widget)
        layout.addWidget(self.button)
        self.setLayout(layout)

    def update_video(self):
        """Update the widget containing the video.

        TODO: it's probably best to use seconds instead of samples.

        """
        dataset = self.parent.info.dataset
        movies = dataset.header['orig']['movies']
        s_freq = dataset.header['orig']['movie_s_freq']
        overview = self.parent.overview
        begsam = overview.window_start * s_freq
        endsam = (overview.window_start + overview.window_length) * s_freq
        lg.info('Video.update_video: begsam: ' + str(begsam) + ' endsam: ' +
                str(endsam))
        movie_info = _convert_movie_to_relative_time(begsam, endsam, movies,
                                                     s_freq)
        self.movie_info = movie_info
        self.add_sources()

        # The signal is only emitted for the last source in the media queue
        self.video.setPrefinishMark(movie_info[-1]['rel_end'] * 1e3)
        self.video.prefinishMarkReached.connect(self.stop_movie)

    def add_sources(self):
        """Add sources to the queue.

        """
        self.video.clear()
        sources = []
        for m in self.movie_info:
            sources.append(Phonon.MediaSource(m['filename']))
        self.video.enqueue(sources)

    def start_stop(self):
        """Start and stop the video, and change the button.

        """
        if self.button.text() == 'Start':
            self.button.setText('Stop')
            self.update_video()
            self.video.play()
            self.video.seek(self.movie_info[0]['rel_start'] * 1e3)

        elif self.button.text() == 'Stop':
            self.button.setText('Start')
            self.video.stop()

    def stop_movie(self):
        """Signal called by prefinishMarkReached.

        TODO: this doesn't work, I don't know why. Check why, otherwise it
        defeats the purpose of prefinishMarkReached.

        """
        pass
        # self.video.stop()
