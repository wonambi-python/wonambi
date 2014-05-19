from . import *

from PySide.QtGui import QApplication

from phypno.scroll_data import MainWindow

ktlx_dir = join(data_dir, 'MGXX/eeg/raw/xltek',
                'MGXX_eeg_xltek_sessA_d03_06_38_05')
scores_file = join(data_dir, 'MGXX/doc/scores',
                   'MGXX_eeg_xltek_sessA_d03_06_38_05_scores.xml')

edf_file = join(data_dir, 'MGXX/eeg/conv/edf/sample.edf')

app = QApplication([])
# or %gui qt


def test_scroll_data_ktlx():
    lg.info('---\nfunction: ' + stack()[0][3])

    q = MainWindow()
    q.action_open_rec(ktlx_dir)

    # select some channels
    q.channels.highlight_channels(q.channels.idx_l0, ['GR1', 'GR2'])

    # click on "apply"
    q.channels.apply_changes()

    # move to the next page
    q.action['page_next'].trigger()

    q.stages.action_open_predefined_stages()

    # q.stages.update_stages(scores_file)

    # close window
    q.action['close_wndw'].trigger()


def test_scroll_data_edf():
    lg.info('---\nfunction: ' + stack()[0][3])

    q = MainWindow()
    q.action_open_rec(edf_file)
    q.info.dataset.header['s_freq'] = 512

    # select some channels
    q.channels.highlight_channels(q.channels.idx_l0, ['LOF1', 'LOF2'])

    # click on "apply"
    q.channels.apply_changes()

    # move to the next step
    q.action['step_next'].trigger()

    # move to the previous step
    q.action['step_prev'].trigger()

    # move to the next page
    q.action['page_next'].trigger()

    # move to the previous page
    q.action['page_prev'].trigger()

    # move 2 minutes in advance
    q.action_add_time(2 * 60)

    q.action_X_more()
    q.action_X_less()

    q.action_X_length(30)

    q.action_Y_more()
    q.action_Y_less()

    q.action_Y_ampl(10)

    q.action_Y_wider()
    q.action_Y_tighter()

    q.action_Y_dist(10)

    q.action_download(10)
    q.action_download(1000000)

    q.toggle_menu_window('Video', q.idx_docks['Video'])  # set visible
    q.toggle_menu_window('Video', q.idx_docks['Video'])  # set invisible

    q.open_preferences()
    q.preferences.hide()

    # close window
    q.action['close_wndw'].trigger()


def test_read_scores():
