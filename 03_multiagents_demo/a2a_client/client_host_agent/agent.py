import os

from dotenv import load_dotenv

from .host_agent import HostAgent
from httpx import AsyncClient

load_dotenv()

root_agent = HostAgent([
    # 自行选择可用的a2a_server
    os.getenv("FILE_AGENT_URL"),
    os.getenv("CLEVER_CAT_AGENT_URL"),
    # os.getenv("SEARCH_AGENT_URL")
    ],
    http_client=AsyncClient()).create_agent()