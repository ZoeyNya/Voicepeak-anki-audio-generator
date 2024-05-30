from aqt.utils import showInfo, showWarning
from aqt.qt import *
from aqt import mw
import subprocess
import os
import uuid
from aqt import gui_hooks
from aqt.sound import av_player
from aqt.qt import QMessageBox
from aqt.qt import QProgressBar
import json
import html
import re

# 设置cache文件路径
cache_file_path = os.path.join(os.path.dirname(__file__), 'voicepeak_cache.json')

def update_voicepeak_cache():
    try:
        # 如果缓存文件不存在，先告知用户需要等待
        if not os.path.exists(cache_file_path):
            QMessageBox.information(None, "请等待", "第一次运行需要一些时间来加载缓存，请耐心等待。")
            
        # 接下来是检查是否需要更新缓存的逻辑
        cache_data = {}
        if os.path.exists(cache_file_path):
            with open(cache_file_path, 'r') as cache_file:
                cache_data = json.load(cache_file)

        # 获取最新的narrator list, 并检查是否需要更新缓存文件
        narrators = get_voicepeak_narrators()
        updated = False   

        # 检查获取到的narrators 是否有更新或为首次缓存
        if set(narrators) != set(cache_data.get('narrators', [])):
            cache_data['narrators'] = narrators
            cache_data['emotions'] = {}
            updated = True

        # 为每个narrator更新emotion list（如果需要）
        for narrator in narrators:
            if not updated:
                # 如果narrators未更新，跳过已有emotions的重新获取
                if narrator in cache_data['emotions']:
                    continue
            cache_data['emotions'][narrator] = get_voicepeak_emotions(narrator)

        # 更新缓存文件
        with open(cache_file_path, 'w') as cache_file:
            json.dump(cache_data, cache_file)
            
    except Exception as e:
        showWarning(f"更新Voicepeak缓存时出错: {str(e)}")

# 缓存字段函数
def save_field_selection(input_field, output_field):
    config = {
        'input_field': input_field,
        'output_field': output_field,
    }
    config_path = os.path.join(os.path.dirname(__file__), 'field_selection_config.json')
    with open(config_path, 'w') as config_file:
        json.dump(config, config_file)

def load_field_selection():
    config_path = os.path.join(os.path.dirname(__file__), 'field_selection_config.json')
    if not os.path.exists(config_path):
        return None, None  # 如果配置文件不存在，返回None
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    return config.get('input_field'), config.get('output_field')

def play_audio(file_path):
    if os.path.exists(file_path):
        av_player.play_file(file_path)

# 获取Voicepeak的讲述者列表
def get_voicepeak_narrators():
    command = ["C:/Program Files/Voicepeak/voicepeak.exe", "--list-narrator"]
    result = subprocess.run(command, capture_output=True, text=True)
    return result.stdout.strip().split('\n')

# 获取特定讲述者的情感列表
def get_voicepeak_emotions(narrator):
    command = ["C:/Program Files/Voicepeak/voicepeak.exe", "--list-emotion", narrator]
    result = subprocess.run(command, capture_output=True, text=True)
    return result.stdout.strip().split('\n')

# 生成语音文件
def generate_voicepeak_audio(script, narrator, emotions, pitch, speed, media_path, uuid_str):
    wav_file_name = f"voicepeak_{uuid_str}.wav"
    output_path = os.path.join(media_path, wav_file_name)

    command = [
        "C:/Program Files/Voicepeak/voicepeak.exe",
        "--say", script,
        "--narrator", narrator,
        "--out", output_path
    ]
    # 添加情感表达
    if emotions:
        command += ["--emotion", ','.join([f"{emotion}={value}" for emotion, value in emotions.items() if value != 0])]
    # 如果有值则添加音调
    if pitch != 0:
        command += ["--pitch", str(pitch)]
    # 如果有值则添加速度
    if speed != 100:
        command += ["--speed", str(speed)]
    # 调用Voicepeak生成.wav音频
    subprocess.run(command, capture_output=True)

    # 确保.wav文件已经生成
    if not os.path.isfile(output_path):
        error_msg = f"Voicepeak failed to generate the .wav file at: {output_path}"
        showWarning(error_msg)  # 通过Anki的警告框显示错误信息
        raise Exception(error_msg)  # 抛出异常

    # .wav文件存在，继续执行FFmpeg转换为.ogg文件的逻辑...
    # 获取ffmpeg.exe的路径（假设它在插件文件夹内）
    ffmpeg_path = os.path.join(os.path.dirname(__file__), 'ffmpeg.exe')

    # 定义输出OGG文件路径
    ogg_file_name = f"voicepeak_{uuid_str}.ogg"
    ogg_output_path = os.path.join(media_path, ogg_file_name)  # 确保使用生成的UUID作为文件名
    
    # 获取ffmpeg.exe的路径（假设它在插件文件夹内）
    ffmpeg_path = os.path.join(os.path.dirname(__file__), 'ffmpeg.exe')

    # 使用ffmpeg进行转码
    ffmpeg_command = [
        ffmpeg_path,  # 修改为插件文件夹内的ffmpeg路径
        "-i", output_path,  # 输入文件
        "-acodec", "libopus",  # 使用Opus编码
        "-b:a", "32k",  # 设置比特率为32kbit/s
        "-ar", "24000",  # 设置采样率为24000Hz
        "-y",  # 覆盖输出文件
        ogg_output_path  # 输出文件
    ]
    # 执行ffmpeg命令
    result = subprocess.run(ffmpeg_command, capture_output=True, text=True)

    # 检查FFmpeg命令是否执行成功
    if result.returncode != 0:
        error_msg = f"FFmpeg conversion failed: {result.stderr}"
        showWarning(error_msg)
        raise Exception(error_msg)

    # 删除原wav文件，保留ogg文件
    os.remove(output_path)

    # 返回OGG文件名称
    return ogg_file_name

# 获取共有字段
def get_common_fields(selected_notes):
    common_fields = set()
    first = True

    for note_id in selected_notes:
        note = mw.col.get_note(note_id)
        if first:
            common_fields = set(note.keys())
        else:
            common_fields &= set(note.keys())
        first = False

    return common_fields

# 创建对话框类
class VoicePeakDialog(QDialog):
    
    def __init__(self, selected_notes, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generate Voicepeak Audio")
        self.layout = QVBoxLayout(self)
        
        # Narrators section
        self.narrator_label = QLabel("声库")
        self.narrator_combo = QComboBox()
        self.layout.addWidget(self.narrator_label)
        self.layout.addWidget(self.narrator_combo)
        
        # 更新缓存前先初始化narrator_combo
        update_voicepeak_cache()
        
        # Emotions section 和其他UI部分...
        
        with open(cache_file_path, 'r') as cache_file:
            cache_data = json.load(cache_file)
        # 使用缓存数据填充narrator_combo...

        for narrator in cache_data['narrators']:
            self.narrator_combo.addItem(narrator)
        
        self.selected_notes = selected_notes

        # 获取共有字段
        self.common_fields = get_common_fields(self.selected_notes)

        # 添加一个下拉菜单供用户选择放置音频的字段
        self.audio_field_label = QLabel("输出音频字段:")  # 确保这个label是在这里被创建的
        self.audio_field_combo = QComboBox()
        for field in self.common_fields:
            self.audio_field_combo.addItem(field)
        self.layout.addWidget(self.audio_field_label)
        self.layout.addWidget(self.audio_field_combo)

        # 添加一个按钮用于生成预览
        self.preview_button = QPushButton("预览效果")
        self.preview_button.clicked.connect(self.preview_audio)
        self.layout.addWidget(self.preview_button)

        # 添加一个下拉菜单供用户从共有字段中选择TTS内容字段
        self.field_label = QLabel("输入内容字段:")
        self.field_combo = QComboBox()
        for field in self.common_fields:  # 使用self.common_fields
            self.field_combo.addItem(field)
        self.layout.addWidget(self.field_label)
        self.layout.addWidget(self.field_combo)

        # Emotions section
        self.emotions_label = QLabel("情绪调节")
        self.emotions_grid = QGridLayout()
        self.emotions_inputs = {}
        self.layout.addWidget(self.emotions_label)
        self.layout.addLayout(self.emotions_grid)
        
        # Speed & Pitch section
        self.speed_label = QLabel("速度:")
        self.speed_input = QLineEdit("100")
        self.pitch_label = QLabel("音调:")
        self.pitch_input = QLineEdit("0")
        self.speed_pitch_layout = QHBoxLayout()
        self.speed_pitch_layout.addWidget(self.speed_label)
        self.speed_pitch_layout.addWidget(self.speed_input)
        self.speed_pitch_layout.addWidget(self.pitch_label)
        self.speed_pitch_layout.addWidget(self.pitch_input)
        self.layout.addLayout(self.speed_pitch_layout)

        # 上次的用户设置.按钮和事件连接
        self.load_settings_button = QPushButton("加载上次设置")
        self.load_settings_button.clicked.connect(self.load_narrator_settings)
        self.layout.addWidget(self.load_settings_button)
        
        # Buttons section
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.generate_audio)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)
        
        # Connect change event to populate emotions
        self.narrator_combo.currentIndexChanged.connect(self.populate_emotions)

        # 加载字段选择
        loaded_input_field, loaded_output_field = load_field_selection()

        # 设置TTS内容字段的默认选择
        if loaded_input_field and loaded_input_field in self.common_fields:
            input_field_index = self.field_combo.findText(loaded_input_field)
            self.field_combo.setCurrentIndex(input_field_index)

        # 设置输出音频字段的默认选择
        if loaded_output_field and loaded_output_field in self.common_fields:
            output_field_index = self.audio_field_combo.findText(loaded_output_field)
            self.audio_field_combo.setCurrentIndex(output_field_index)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMaximum(len(self.selected_notes))  # 最大值设置为选中笔记的数量
        self.layout.addWidget(self.progress_bar)

    def load_narrator_settings(self):
        narrator = self.narrator_combo.currentText()
        settings_path = os.path.join(os.path.dirname(__file__), 'narrator_settings.json')
        try:
            if not os.path.exists(settings_path):
                return
            with open(settings_path, 'r') as settings_file:
                settings_data = json.load(settings_file)
            narrator_settings = settings_data.get(narrator)
            if narrator_settings:
                # 加载并设置emotion值
                for emotion, entry in self.emotions_inputs.items():
                    entry.setText(str(narrator_settings['emotions'].get(emotion, 0)))
                # 加载并设置pitch和speed值
                self.pitch_input.setText(str(narrator_settings['pitch']))
                self.speed_input.setText(str(narrator_settings['speed']))
        except Exception as e:
            showWarning(f"加载narrator设置时出错: {str(e)}")

    def save_narrator_settings(self, narrator, emotions, pitch, speed):
        settings_path = os.path.join(os.path.dirname(__file__), 'narrator_settings.json')
        try:
            # 加载已有设置
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as settings_file:
                    settings_data = json.load(settings_file)
            else:
                settings_data = {}
            # 更新设置
            settings_data[narrator] = {
                'emotions': emotions,
                'pitch': pitch,
                'speed': speed
            }
            # 保存设置
            with open(settings_path, 'w') as settings_file:
                json.dump(settings_data, settings_file)
        except Exception as e:
            showWarning(f"保存narrator设置时出错: {str(e)}")

    def populate_emotions(self):
        narrator = self.narrator_combo.currentText()

        # 加载缓存数据
        with open(cache_file_path, 'r') as cache_file:
            cache_data = json.load(cache_file)

        # 使用缓存中的emotions信息
        emotions = cache_data['emotions'][narrator]
            
        # Clear previous emotions
        while self.emotions_grid.count():
            item = self.emotions_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add new emotions
        self.emotions_inputs = {}
        for i, emotion in enumerate(emotions):
            label = QLabel(f"{emotion}:")
            entry = QLineEdit("0")
            self.emotions_inputs[emotion] = entry
            self.emotions_grid.addWidget(label, i, 0)
            self.emotions_grid.addWidget(entry, i, 1)

    def preview_audio(self):
        try:
            narrator = self.narrator_combo.currentText()
            emotions = {emotion: int(input.text()) for emotion, input in self.emotions_inputs.items()}
            pitch = int(self.pitch_input.text())
            speed = int(self.speed_input.text())
            script = "私は小波です。はじめまして。"
            
            # 预览文件保存在当前插件目录下
            addon_path = os.path.dirname(__file__)
            preview_path = os.path.join(addon_path, "preview.wav")

             # 直接调用Voicepeak生成预览音频，不进行OGG转换
            preview_command = [
                "C:/Program Files/Voicepeak/voicepeak.exe",
                "--say", script,
                "--narrator", narrator,
                "--emotion", ','.join([f"{emotion}={value}" for emotion, value in emotions.items() if value != 0]),
                "--pitch", str(pitch),
                "--speed", str(speed),
                "--out", preview_path,
                "-y"  # 确保覆盖已有文件
            ]
            subprocess.run(preview_command, capture_output=True)
            
            # 播放预览音频
            play_audio(preview_path)
        except Exception as e:
            showWarning(str(e))          

    def generate_audio(self):
        field_name = self.field_combo.currentText()
        audio_field_name = self.audio_field_combo.currentText()
        media_path = mw.col.media.dir()

        narrator = self.narrator_combo.currentText()
        emotions = {emotion: int(input_field.text()) for emotion, input_field in self.emotions_inputs.items()}
        pitch = int(self.pitch_input.text())
        speed = int(self.speed_input.text())

        successful_count = 0
        for note_id in self.selected_notes:
            try:
                note = mw.col.get_note(note_id)
                text_content = note[field_name].strip()
                text_content = html.unescape(text_content)  # 将 HTML 实体转换回正常的字符。
                text_content = re.sub(r'<[^>]+>', '', text_content)      # 移除HTML标签

                if not text_content:
                    continue  # 如果选择的字段没有内容，则跳过

                # 如果音频字段已有内容，询问用户是否覆盖
                if note[audio_field_name]:
                    res = QMessageBox.question(
                        self,
                        "Overwrite Audio",
                        f"The note with ID '{note_id}' already has audio in the '{audio_field_name}' field. Do you want to overwrite it?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )

                    # 然后在判断语句中应该这样比较：
                    if res == QMessageBox.StandardButton.No:
                        continue  # 如果用户选择不覆盖，则跳过这个笔记

                # 使用UUID生成唯一的字符串
                uuid_str = str(uuid.uuid4())
                file_name = f"voicepeak_{uuid_str}.wav"  # 这里定义的是WAV文件名，但实际使用的将是OGG文件
                output_path = os.path.join(media_path, file_name)  # 这里定义的是WAV文件路径，但实际使用的将是OGG文件

                # 调用generate_voicepeak_audio并获取OGG文件路径
                ogg_file_path = generate_voicepeak_audio(text_content, narrator, emotions, pitch, speed, media_path, uuid_str)
                note[audio_field_name] = f'[sound:{os.path.basename(ogg_file_path)}]'  # 只使用文件名更新字段
                note.flush()
                successful_count += 1
                self.progress_bar.setValue(successful_count)  # 更新进度条的值

            except Exception as e:
                # 如果处理中出现错误，展示错误信息，并继续处理下一个笔记
                showWarning(f"Error! note ID {note_id} 生成音频错误: {e}")

        if successful_count:
            # 如果至少一个音频文件已生成，则刷新Anki界面更新显示音频
            mw.reset()
            showInfo(f"{successful_count} 个音频文件成功生成。")
        else:
            # 如果没有文件生成，告知用户
            showWarning("没有生成音频文件。请检查笔记的内容。")

        # 成功生成音频后保存字段选择
        save_field_selection(self.field_combo.currentText(), self.audio_field_combo.currentText())

        self.accept()

        self.save_narrator_settings(
            narrator,
            {emotion: int(input_field.text()) for emotion, input_field in self.emotions_inputs.items()},
            int(self.pitch_input.text()),
            int(self.speed_input.text())
        )

def onVoicepeakOptionSelected(browser):
    selected_notes = browser.selectedNotes()
    if not selected_notes:
        showInfo("没有选中任何笔记。")
        return

    try:
        dialog = VoicePeakDialog(selected_notes, browser)
        dialog.exec()  # 注意：这里的exec需根据PyQt版本可能需要改成exec_()
    except Exception as e:
        showInfo(f"发生错误: {str(e)}")