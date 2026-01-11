import os

from dotenv import load_dotenv

from .host_agent import HostAgent
from httpx import AsyncClient

load_dotenv() # 加载环境变量

root_agent = HostAgent([ # 创建智能体
    os.getenv("FILE_PARSE_AGENT_URL"), # 文件解析智能体
    ],
    http_client=AsyncClient()).create_agent() # 创建智能体