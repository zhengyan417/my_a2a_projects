import os

from dotenv import load_dotenv

from .host_agent import HostAgent
from httpx import AsyncClient

load_dotenv()

root_agent = HostAgent([
    os.getenv("FILE_AGENT_URL"),
    os.getenv("CLEVER_CAT_AGENT_URL")],
    http_client=AsyncClient()).create_agent()