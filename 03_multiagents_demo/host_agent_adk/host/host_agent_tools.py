import os
def read_text_file(filename:str):
    """
    从固定目录读取文件

    Args:
        filename (str): 文件名，如 "test.txt"

    Returns:
        str: 文件内容
    """
    base_dir = os.getenv('SECRET_MATERIALS_PATH')
    file_path = os.path.join(base_dir, filename)
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            return f"{filename}文件查询成功，里面的密文是: {content}"
    except Exception as e:
        return f"{filename}文件不存在"
