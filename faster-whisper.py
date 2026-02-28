import json
from faster_whisper import WhisperModel
import os

def load_config(config_path):
    """
    读取并解析 config.json 文件。
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"错误：找不到配置文件 '{config_path}'。")
        return None
    except json.JSONDecodeError:
        print(f"错误：配置文件 '{config_path}' 不是有效的 JSON 格式。")
        return None
    


def ensure_directories(srt_dir, out_dir):
    """
    检查并创建 SRT 输出目录和通用输出目录。
    """
    try:
        os.makedirs(srt_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)
        print(f"✅ 确保目录存在: SRT='{srt_dir}', 输出='{out_dir}'")
    except Exception as e:
        print(f"错误：无法创建目录。{e}")
        return False
    return True



def initialize_model(model_path):
    """
    根据模型路径加载本地 Whisper 模型。
    固定使用 cuda 设备和 float32 计算类型。
    """
    try:
        # 加载模型
        model = WhisperModel(model_path, device="cuda", compute_type="float32")
        print(f"✅ 成功加载模型: {model_path}")
        return model
    except Exception as e:
        print(f"错误：无法加载模型 '{model_path}'。{e}")
        return None
    

def transcribe_audio(model, audio_file):
    """
    使用 Whisper 模型对音频文件进行转录。
    使用固定的 VAD 参数和中文提示词。
    """

    # 固定的转录参数
    prompt_text = """
    你好，这是一个包含逗号、句号等标点符号的中文语句。
    """

    vad_parameters = {
        # 播客专用调优
        "min_speech_duration_ms": 300,      # 略高于默认，过滤短促呼吸/杂音
        "min_silence_duration_ms": 1800,     # 关键：播客对话停顿较短，设为800-1200ms
        "speech_pad_ms": 600,               # 适当填充，避免切掉词首
        "threshold": 0.45,                  # 稍宽松，确保捕捉所有对话
    }

    try:
        segments, info = model.transcribe(
            audio_file,
            language="zh",  # 指定中文，提升识别精度
            word_timestamps=True,  # 启用词级时间戳
            initial_prompt=prompt_text,
            vad_filter=True,
            vad_parameters=vad_parameters,
            beam_size=5,
            temperature=0.0,
        )
        print(f"✅ 转录完成。检测到的语言：{info.language}")
        return segments, info
    except Exception as e:
        print(f"错误：转录失败。{e}")
        return None, None
    
def format_srt_time(seconds):
    """
    将秒数转换为 SRT 时间格式 (HH:MM:SS,mmm)。
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(segments, audio_file, srt_dir):
    """
    处理转录结果，生成 SRT 字幕文件并保存到指定目录。
    """
    if not segments:
        print("警告：没有可供生成 SRT 的分段数据。")
        return

    # 初始化变量
    srt_content = []  # 用于存储每一段字幕的字符串
    segment_index = 1  # SRT 序号从 1 开始

    print("开始处理分段文本并生成字幕...")

    for segment in segments:
        # 1. 打印调试信息
        print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")

        # 2. 文本清洗 (用于 SRT)
        segment_text = segment.text
        segment_text = segment_text.replace('...', '…').replace('..', '。')

        # 3. 构建 SRT 片段
        srt_entry = (
            f"{segment_index}\n"
            f"{format_srt_time(segment.start)} --> {format_srt_time(segment.end)}\n"
            f"{segment_text.strip()}\n\n"
        )
        srt_content.append(srt_entry)

        segment_index += 1

    # --- 保存文件 2: SRT 字幕文件 ---
    full_name = os.path.basename(audio_file)
    output_srt_file = os.path.join(srt_dir, os.path.splitext(full_name)[0] + ".srt")
    try:
        with open(output_srt_file, 'w', encoding='utf-8') as f:
            f.write("".join(srt_content))
        print(f"✅ 已生成字幕文件：{output_srt_file}")
    except Exception as e:
        print(f"错误：无法保存 SRT 文件。{e}")



def main():
    """
    程序入口。
    """
    # 获取脚本所在目录
    script_dir = os.path.dirname(__file__)
    config_path = "config.json"
    

    # 1. 加载配置
    config = load_config(config_path)
    if not config:
        print("终止：无法加载配置。")
        return

    srt_path = os.path.join(script_dir,config["srt_path"])
    audio_path = os.path.join(script_dir,config["audio_path"])
    model_path = config["model_path"]
    audio_file = os.path.join(audio_path, "output.wav")

    # 2. 确保目录存在
    if not ensure_directories(srt_path, audio_path):
        print("终止：无法确保目录存在。")
        return

    # 3. 初始化模型
    model = initialize_model(model_path)
    if not model:
        print("终止：无法初始化模型。")
        return

    # 4. 执行转录
    segments, info = transcribe_audio(model, audio_file)
    if not segments:
        print("终止：转录失败。")
        return
    
    print("检测到的语言：%s" % info.language)

    # 5. 生成 SRT 字幕
    generate_srt(segments, audio_file, srt_path)

if __name__ == "__main__":
    main()