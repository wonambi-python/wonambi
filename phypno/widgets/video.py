from logging import getLogger
lg = getLogger(__name__)

from PySide.QtGui import (QPushButton,
                          QVBoxLayout,
                          QWidget,
                          )
from PySide.phonon import Phonon


def _convert_movie_to_relative_time(begsam, endsam, movie, s_freq):
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
    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.movie_info = None

        self.widget = Phonon.VideoWidget()
        self.video = Phonon.MediaObject()

        self.button = QPushButton('Start')
        self.button.clicked.connect(self.start_stop)
        Phonon.createPath(self.video, self.widget)

        layout = QVBoxLayout()
        layout.addWidget(self.widget)
        layout.addWidget(self.button)
        self.setLayout(layout)

    def load_video(self):
        dataset = self.parent.info.dataset
        movies = dataset.header['orig']['movies']
        s_freq = dataset.header['orig']['movie_s_freq']
        overview = self.parent.overview
        begsam = overview.window_start * s_freq
        endsam = (overview.window_start + overview.window_length) * s_freq
        lg.info('Video.load_video: begsam: ' + str(begsam) + ' endsam: ' +
                str(endsam))
        movie_info = _convert_movie_to_relative_time(begsam, endsam, movies,
                                                     s_freq)
        self.movie_info = movie_info
        self.add_sources()

        # The signal is only emitted for the last source in the media queue
        self.video.setPrefinishMark(movie_info[-1]['rel_end'] * 1e3)
        self.video.prefinishMarkReached.connect(self.stop_movie)

    def add_sources(self):
        self.video.clear()
        sources = []
        for m in self.movie_info:
            sources.append(Phonon.MediaSource(m['filename']))
        self.video.enqueue(sources)

    def start_stop(self):
        if self.button.text() == 'Start':
            self.button.setText('Stop')
            self.load_video()
            self.video.play()
            self.video.seek(self.movie_info[0]['rel_start'] * 1e3)

        elif self.button.text() == 'Stop':
            self.button.setText('Start')
            self.video.stop()

    def stop_movie(self):
        pass
        # self.video.stop()  this doesn't work, I don't know why
