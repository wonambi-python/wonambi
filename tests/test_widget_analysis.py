from wonambi.scroll_data import MainWindow

from .test_scroll_data import (channel_make_group,
                               find_in_qt,
                               find_in_qt_by_idx,
                               screenshot,
                               )

from .paths import (annot_psg_path,
                    gui_file,
                    GUI_PATH,
                    )

def test_widget_analysis_dialog(qtbot):
    
    w = MainWindow()
    qtbot.addWidget(w)

    w.info.open_dataset(str(gui_file))
    channel_make_group(w)
    w.channels.button_apply.click()
    w.notes.update_notes(annot_psg_path)
    
    w.notes.action['analyze']
    ad = w.analysis_dialog
    ad.grab().save(str(GUI_PATH / 'analysis_01_dialog.png'))
    
    ad.button_clicked(ad.idx_cancel)
