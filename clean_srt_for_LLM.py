import json
import os

def load_config(config_path):
    """
    读取并解析 config.json 配置文件。
    预期配置包含:
      - "srt_path": 输入 .srt 文件的路径
      - "out_path": 输出文本文件的路径
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 简单校验必要字段是否存在
    if "srt_path" not in config or "out_path" not in config:
        raise ValueError("配置文件中必须包含 'srt_path' 和 'out_path' 字段")
    
    return config



def get_srt_files(srt_path):
    """
    遍历指定文件夹，找出所有 .srt 格式的文件。
    返回包含完整文件路径的列表。
    """
    srt_files = []
    
    # 遍历文件夹中的所有文件
    for filename in os.listdir(srt_path):
        if filename.endswith('.srt'):
            # 拼接完整路径并加入列表
            full_path = os.path.join(srt_path, filename)
            srt_files.append(full_path)
    
    return srt_files

def parse_srt(srt_content):
    """
    解析 .srt 格式的字幕内容。
    输入：完整的字幕文件字符串内容。
    输出：列表，每个元素是一个字典 {'index': 序号, 'time': 时间戳, 'text': 字幕文本}。
    """
    subtitles = []
    
    # 按空行分割成不同的字幕块
    blocks = srt_content.strip().split('\n\n')
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
            
        try:
            index = int(lines[0])
            time_stamp = lines[1]
            # 字幕文本可能有多行，将第3行及之后的所有行合并
            text = '\n'.join(lines[2:])
            
            subtitles.append({
                'index': index,
                'time': time_stamp,
                'text': text
            })
        except (ValueError, IndexError):
            # 跳过格式不正确的块
            continue
            
    return subtitles

def format_for_llm(subtitles):
    """
    将解析后的字幕列表转换为适合大模型阅读的纯文本。
    策略：移除时间戳和序号，仅保留文本内容，并按顺序用换行符连接。
    """
    text_lines = []
    
    for item in subtitles:
        # 只提取文本部分
        text_lines.append(item['text'])
    
    # 将所有文本段落用换行符连接，形成清晰的段落结构
    return '\n'.join(text_lines)



def save_output(text, output_folder, filename):
    """
    将处理后的文本保存到指定文件夹。
    参数:
      text: 要保存的文本内容
      output_folder: 配置中指定的输出文件夹路径
      filename: 具体的输出文件名 (例如 'result.txt')
    """
    # 确保输出文件夹存在，不存在则创建
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # 拼接完整的文件路径
    full_path = os.path.join(output_folder, filename)
    
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(text)
    
    print(f"文件已保存至: {full_path}")


def main():
    """
    主函数：协调所有步骤。
    1. 读取配置获取输入文件夹和输出文件夹。
    2. 查找文件夹内所有 .srt 文件。
    3. 遍历每个文件：解析 -> 格式化 -> 立即保存（文件名同原文件，后缀改为 .txt）。
    """
    # 获取脚本所在目录
    script_dir = os.path.dirname(__file__)
    # 1. 加载配置
    config = load_config('config.json')
    srt_path = os.path.join(script_dir,config["srt_path"])
    out_path = os.path.join(script_dir,config['out_path'])
    
    # 2. 获取所有 .srt 文件
    srt_files = get_srt_files(srt_path)
    
    if not srt_files:
        print(f"在文件夹 '{srt_path}' 中未找到任何 .srt 文件。")
        return

    print(f"找到 {len(srt_files)} 个字幕文件，开始逐个处理...")
    
    # 3. 遍历处理每个文件
    for file_path in srt_files:
        print(f"正在处理: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析字幕
            subtitles = parse_srt(content)
            # 格式化为大模型可用文本
            clean_text = format_for_llm(subtitles)
            
            # 构造输出文件名：保持原文件名主体，将 .srt 替换为 .txt
            original_filename = os.path.basename(file_path)
            if original_filename.endswith('.srt'):
                new_filename = original_filename[:-4] + '.txt'
            else:
                new_filename = original_filename + '.txt'
            
            # 立即保存当前文件的处理结果
            save_output(clean_text, out_path, new_filename)
            
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")
            continue
    
    print("所有任务完成！")

if __name__ == "__main__":
    main()