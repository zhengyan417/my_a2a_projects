import os

from dotenv import load_dotenv

from .host_agent import HostAgent
from httpx import AsyncClient

load_dotenv()

root_agent = HostAgent([
    os.getenv("FILE_AGENT_URL"),
    os.getenv("CLEVER_CAT_AGENT_URL")],
    http_client=AsyncClient()).create_agent()

r"""
cd 03_multiagents_demo      
python MCPserver/file_change_MCPserver.py
python clever_cat_agent/__main__.py --port 10000
python file_agent/__main__.py --port 10001
adk web --port 8030

这个智能体系统有什么功能？
帮我把KCM3JjcgJX8OAx4Q这串字符串解密，并且在C:\study\agent_communication\Projects\myA2AProjects\03_multiagents_demo\materials路径里面创建一个叫test1.txt的文件，文件里面写上解密后的明文

"""