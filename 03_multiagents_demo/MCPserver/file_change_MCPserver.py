import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pathlib import Path

mcp = FastMCP("File_manager")

load_dotenv()


def get_base_dir():
    """获取基础目录路径"""
    base_dir = Path(os.getenv('SECRET_MATERIALS_PATH'))
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


@mcp.tool()
async def create_file(filename: str = "default_text.txt", content: str = "") -> str:
    """
    创建指定名称的文件,并且添加指定的内容

    Args:
        filename: 要创建的文件的名称
        content: 文件内容，默认为空
    """
    if filename is None:
        filename = "default_text.txt"

    base_dir = get_base_dir()
    file_path = base_dir / filename

    try:
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
    base_dir = get_base_dir()
    file_path = base_dir / filename

    if file_path.exists():
        file_path.unlink()
        return f"{file_path}文件删除成功"
    else:
        return f"{file_path}文件不存在"


@mcp.tool()
async def read_file(filename: str) -> str:
    """
    读取指定文件的内容

    Args:
        filename: 要读取的文件名

    Returns:
        文件内容字符串，如果文件不存在或读取失败则返回错误信息
    """
    base_dir = get_base_dir()
    file_path = base_dir / filename

    try:
        if not file_path.exists():
            return f"文件 '{filename}' 不存在"

        content = file_path.read_text(encoding="utf-8")
        return f"文件 '{filename}' 的内容:\n{content}"
    except Exception as e:
        return f"读取文件失败: {e}"


@mcp.tool()
async def update_file(filename: str, content: str, append: bool = False) -> str:
    """
    更新指定文件的内容

    Args:
        filename: 要更新的文件名
        content: 新的内容
        append: 是否为追加模式，True表示追加内容，False表示覆盖内容（默认）

    Returns:
        操作结果信息
    """
    base_dir = get_base_dir()
    file_path = base_dir / filename

    try:
        if not file_path.exists():
            return f"文件 '{filename}' 不存在，无法更新"

        if append:
            # 追加模式
            with file_path.open('a', encoding='utf-8') as f:
                f.write(content)
            return f"文件 '{filename}' 内容追加成功"
        else:
            # 覆盖模式
            file_path.write_text(content, encoding="utf-8")
            return f"文件 '{filename}' 内容更新成功"
    except Exception as e:
        return f"更新文件失败: {e}"


@mcp.tool()
async def list_files() -> str:
    """
    列出目录中的所有文件

    Returns:
        文件列表字符串
    """
    base_dir = get_base_dir()

    try:
        files = list(base_dir.iterdir())
        if not files:
            return "目录为空"

        file_list = []
        for file in files:
            if file.is_file():
                file_list.append(f"- {file.name}")

        if not file_list:
            return "目录中没有文件"

        return "目录中的文件:\n" + "\n".join(file_list)
    except Exception as e:
        return f"列出文件失败: {e}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")