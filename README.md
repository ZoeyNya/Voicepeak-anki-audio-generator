# Voicepeak-anki-audio-generator
用voicepeak给anki选中卡片的指定字段生成ogg音频
> 只在本机的anki上测试过：
> win11
> 版本 ⁨24.04.1 (ccd9ca1a)⁩
> Python 3.9.18 Qt 6.6.2 PyQt 6.6.1
## 使用须知：
- 要下载ffmpeg.exe，和仓库文件一起打包成zip，然后通过anki插件本地安装。
- voicepeak脚本中写的是默认安装地址：C:/Program Files/Voicepeak/voicepeak.exe。可自行修改
- voicepeak产生音频的效率不高，不是实时的，所以输入文字很长、选择卡片很多的话，要等很久……这时候可能anki会显示为卡住的状态
## 功能
1、在编辑界面选中多张卡片（单张卡片）时，会读取共有字段，可以选择一个字段作为tts的文本内容，一个字段作为输出音频的目标。
2、第一次加载插件时，会自动读取voicepeak的声库列表，这个过程可能也会比较久。
3、会自动加载上次选择的字段。
4、可以选择加载对应声库上次的参数调节值。
