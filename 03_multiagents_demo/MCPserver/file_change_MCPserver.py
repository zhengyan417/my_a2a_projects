import os

from mcp.server.fastmcp import FastMCP
from pathlib import Path

mcp = FastMCP("File_manager")

@mcp.tool()
async def create_file(filename:str="default_text.txt", content:str="") -> str:
    """
    创建指定名称的文件,并且添加指定的内容

    Args:
        filename: 要创建的文件的名称
        content: 文件内容，默认为空
    """
    if filename==None :
        filename="default_text.txt"
    base_dir = Path(os.getenv('SECRET_MATERIALS_PATH'))
    base_dir.mkdir(parents=True, exist_ok=True)
    file_path = base_dir / filename
    try:
        # 使用 Path 对象的 write_text 方法
        file_path.write_text(content, encoding="utf-8")
        return f"文件 '{filename}' 创建成功，路径: {file_path}"
    except Exception as e:
        return f"文件创建失败: {e}"

@mcp.tool()
async def delete_file(filename: str) -> str:
    """
    删除指定位置的文件

    Args:
        filename: 文件名
    """
    base_dir = os.getenv('SECRET_MATERIALS_PATH')
    file_path = os.path.join(base_dir, filename)
    path = Path(file_path)
    if path.exists():
        path.unlink()
        return f"{file_path}文件删除成功"
    else:
        return f"{file_path}文件不存在"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")