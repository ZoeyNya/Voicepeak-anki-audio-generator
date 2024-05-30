from aqt import gui_hooks
from aqt.browser import Browser
from aqt.qt import QAction, QMenu  # 确保QMenu已经被导入
from .voicepeak_gen import onVoicepeakOptionSelected

def on_browser_setup_menus(browser: Browser, menu: QMenu):
    action = QAction("生成 Voicepeak 语音", browser)
    action.triggered.connect(lambda: onVoicepeakOptionSelected(browser))
    menu.addAction(action)

gui_hooks.browser_will_show_context_menu.append(on_browser_setup_menus)