from . import *

from PySide.QtGui import QApplication

from phypno.scroll_data import MainWindow

ktlx_dir = join(data_dir, 'MGXX/eeg/raw/xltek',
                'MGXX_eeg_xltek_sessA_d03_06_38_05')

app = QApplication([])


def test_scroll_data():
    lg.info('---\nfunction: ' + stack()[0][3])

    q = MainWindow()
    q.action_open_rec(ktlx_dir)

    # select some channels
    q.channels.highlight_channels(q.channels.idx_l0, ['GR1', 'GR2'])

    # click on "apply"
    q.channels.apply_changes()

    # move to the next page
    q.action['page_prev'].trigger()

    # close window
    q.action['close_wndw'].trigger()
