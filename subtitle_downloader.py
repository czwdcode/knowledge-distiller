import json,os
import yt_dlp

def load_config(config_path):
    """
    从指定路径读取并解析JSON配置文件。
    格式：
    {
    "urls": [],
    "audio_path": "./audio",
    "srt_path": "./srt",
    "cookiefile": "",
    "subtitle_langs": [
        "en",
        "zh-Hans"
    ],
    "max_retries": 3,
    "timeout": 30
    }
    
    参数:
        config_path (str): 配置文件的路径，例如 'config.json'
    
    返回:
        dict: 包含配置信息的字典。
    
    异常:
        如果文件不存在或JSON格式无效，程序将直接退出并打印错误信息。
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"配置从 '{config_path}' 加载成功。")
        return config
    except FileNotFoundError:
        print(f"错误：在路径 '{config_path}' 未找到配置文件。")
        exit(1)
    except json.JSONDecodeError:
        print(f"错误：文件 '{config_path}' 不是有效的JSON格式。")
        exit(1)


def get_video_info(url, preferred_languages, config):
    """
    获取指定URL的视频信息，并检测配置列表中第一个可用的字幕语言。
    
    参数:
        url (str): 目标视频的URL。
        preferred_languages (list): 用户偏好的语言代码列表，如 ['zh', 'en', 'ai-zh']
        config (dict): 配置字典，用于获取cookiefile等参数
    
    返回:
        tuple: (info_dict, selected_lang)
               info_dict: 包含视频信息的字典
               selected_lang: 从preferred_languages中找到的第一个可用语言，如无匹配则为None
    """
    # 配置yt-dlp仅提取信息，不下载任何文件
    ydl_opts = {
        'quiet': True,         # 减少控制台输出
        'no_warnings': True,   # 不显示警告
        'listsubtitles': True,
    }
    
    # 添加cookiefile参数（如果需要）
    if 'cookiefile' in config:
        ydl_opts['cookiefile'] = config['cookiefile']
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            # print(info)
            
            # 获取视频的所有字幕（手动+自动）
            all_subtitles = {}
            
            # 合并手动字幕
            subtitles = info.get('subtitles', {})
            if subtitles:
                all_subtitles.update(subtitles)
            
            # 合并自动生成的字幕
            auto_captions = info.get('automatic_captions', {})
            if auto_captions:
                all_subtitles.update(auto_captions)
            
            # 在偏好语言列表中查找第一个可用的语言
            selected_lang = None
            for lang in preferred_languages:
                if lang in all_subtitles:
                    selected_lang = lang
                    break
            
            return info, selected_lang
            
    except Exception as e:
        # 捕获所有异常，例如网络错误、不支持的URL、视频不存在等
        print(f"获取视频信息时出错 (URL: {url}): {e}")
        return None, None
    
def generate_download_options(config, selected_lang):
    """
    根据配置文件中的全局设置和选择的字幕语言，生成最终的下载选项。
    核心逻辑：如果有选中的字幕语言，则只下载该语言字幕；如果没有，则下载最差音质音频。

    参数:
        config (dict): 从 load_config() 加载的配置字典。
        selected_lang (str|None): 从偏好列表中匹配到的第一个可用语言代码，如无则为None。

    返回:
        dict: 用于 yt_dlp.YoutubeDL() 的选项字典。
    """
    # 1. 设置基础选项（从配置文件读取或使用默认值）
    ydl_opts = {
        'quiet': config.get('quiet', False),
        'no_warnings': config.get('no_warnings', True),
    }

    # 2. 根据是否有选中的字幕语言决定下载内容
    if selected_lang:
        # 有匹配字幕语言的情况：下载该语言字幕
        # 添加cookiefile参数（仅字幕下载需要）
        if 'cookiefile' in config:
            ydl_opts['cookiefile'] = config['cookiefile']
        filename = os.path.join(config.get('srt_path'), config.get('output_template', '%(title)s [%(id)s].%(ext)s'))
        ydl_opts.update({
            'outtmpl': filename,
            'writesubtitles': True,          # 写入字幕文件
            'writeautomaticsub': True,       # 写入自动生成的字幕
            'subtitleslangs': [selected_lang],  # 只使用匹配到的语言
            'skip_download': True,           # 关键：跳过音视频流下载
            'postprocessors': [],            # 确保没有音频提取后处理器
        })
        print(f"    配置：检测到匹配字幕，将下载 '{selected_lang}' 语言的字幕文件。")
    else:
        # 无匹配字幕的情况：下载最差音质音频
        # 注意：音频下载不需要cookiefile参数
        filename = os.path.join(config.get('audio_path'), config.get('output_template', '%(title)s [%(id)s].%(ext)s'))
        ydl_opts.update({
            'outtmpl': filename,
            'format': 'worstaudio/worst',      # 选择最差音质格式
            'writesubtitles': False,         # 不下载字幕
            'writeautomaticsub': False,
        })
        print("    配置：未检测到匹配的字幕，将下载最差音质音频。")

    return ydl_opts

def download_item(url, ydl_opts):
    """
    使用给定的下载选项，对单个URL执行下载操作。

    参数:
        url (str): 要下载的视频URL。
        ydl_opts (dict): 由 generate_download_options() 生成的下载选项。

    返回:
        bool: 如果下载成功（或按配置成功跳过）返回True，否则返回False。
    """
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 调用download方法执行下载流程
            # 注意：如果 ydl_opts 中设置了 'skip_download': True，则此处不会下载音视频流
            ydl.download([url])
        print(f"    处理完成: {url}")
        return True
    except Exception as e:
        # 捕获下载过程中的异常，例如网络错误、格式不可用、后处理器错误等
        print(f"    下载失败 (URL: {url}): {e}")
        return False
    
def is_collection(url):
    """
    判断给定的URL是否为合集
    包含/favlist或/lists路径的URL视为合集
    """
    collection_keywords = ['/favlist', '/lists']
    
    # 检查URL是否包含任一合集关键词
    for keyword in collection_keywords:
        if keyword in url:
            return True
    return False


def extract_videos_from_collection(url):
    """
    从合集URL中提取所有视频地址
    """
    video_urls = []
    
    ydl_opts = {
        'extract_flat': True,
        'simulate':True,
        'quiet': True,
        'no_warnings': False,
        'ignoreerrors': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 提取合集信息
            info = ydl.extract_info(url, download=False)
            print(info)
            
            # 检查是否为合集（播放列表）
            if 'entries' in info:
                # 遍历合集中的每个条目
                for entry in info['entries']:
                    if entry and 'url' in entry:
                        video_urls.append(entry['url'])
                    elif entry and 'webpage_url' in entry:
                        video_urls.append(entry['webpage_url'])
            elif 'webpage_url' in info:
                # 如果是单个视频但被识别为合集结构
                video_urls.append(info['webpage_url'])
                
    except Exception as e:
        print(f"提取合集 '{url}' 时发生错误: {e}")
        raise
    
    return video_urls

def main():
    """
    程序的主函数，协调整个下载流程：
    1. 加载配置文件
    2. 遍历配置中的URL列表
    3. 对每个URL，获取其信息并检测偏好语言列表中的第一个可用字幕
    4. 根据检测到的匹配语言生成对应的下载选项
    5. 使用生成的选项执行下载
    """
    # 1. 加载配置
    config = load_config('config.json')
    
    # 从配置中获取目标URL列表
    target_urls = config.get('urls', [])
    if not target_urls:
        print("配置中未找到 'urls' 列表或列表为空。程序退出。")
        return
    # 处理URL列表，区分合集和单视频
    processed_urls = []
    for url in target_urls:
        if is_collection(url):  # 判断是否为合集
            try:
                video_list = extract_videos_from_collection(url)  # 从合集提取视频列表
                processed_urls.extend(video_list)
                print(f"合集 URL '{url}' 已处理，提取到 {len(video_list)} 个视频")
            except Exception as e:
                print(f"处理合集 '{url}' 时出错: {e}")
                continue
        else:  # 单视频地址
            processed_urls.append(url)

    # 使用处理后的URL列表继续后续操作
    print(f"共获取到 {len(processed_urls)} 个待处理视频")
    # 获取用户偏好的语言列表
    preferred_languages = config.get('subtitle_langs', ['en'])
    print(f"偏好语言顺序: {preferred_languages}")
    
    
    # 2. 遍历每个URL
    for idx, url in enumerate(processed_urls, 1):
        print(f"\n[{idx}/{len(processed_urls)}] 处理URL: {url}")
        
        # 3. 获取视频信息，检测偏好列表中第一个可用的字幕语言
        print(f"  步骤1: 正在获取视频信息并检测字幕(偏好语言: {preferred_languages})...")
        video_info, selected_lang = get_video_info(url, preferred_languages, config)  # 传入config
        
        if video_info is None:
            print(f"  警告: 无法获取视频信息，跳过此URL。")
            continue
        
        if selected_lang:
            print(f"  步骤2: 字幕检测完成。匹配到语言: {selected_lang}")
        else:
            print(f"  步骤2: 字幕检测完成。未找到偏好语言列表中的字幕")
        
        # 4. 根据匹配到的语言生成下载选项
        print("  步骤3: 生成下载选项...")
        ydl_opts = generate_download_options(config, selected_lang)
        
        # 5. 执行下载
        print("  步骤4: 开始下载...")
        success = download_item(url, ydl_opts)
        
        if not success:
            print(f"  警告: URL处理过程中可能出现问题: {url}")
    
    print("\n所有任务处理完毕。")

# 程序的执行入口
if __name__ == "__main__":
    main()