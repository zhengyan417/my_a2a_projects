import logging
import os

import click
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from dotenv import load_dotenv
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from agent_executor import (
    SearchAgentExecutor,
)

from agent import (
    create_search_agent,
)


load_dotenv()

logging.basicConfig()

DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 10002


def main(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):

    skill = AgentSkill(
        id='search_manager',
        name='搜索工具',
        description='帮助获取天气、时间或者调用搜索引擎',
        tags=['search','weather','time'],
        examples=['北京的天气是多云'],
    )

    agent_card = AgentCard(
        name='Search_Agent',
        description='帮助搜索信息，比如搜索时间、天气或者调用搜索引擎',
        url=f"http://{host}:{port}",
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=False),
        skills=[skill],
    )

    adk_agent = create_search_agent()
    runner = Runner(
        app_name=agent_card.name,
        agent=adk_agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )
    agent_executor = SearchAgentExecutor(runner,agent_card)

    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=InMemoryTaskStore()
    )

    server = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )

    uvicorn.run(server.build(), host=host, port=port)

if __name__ == '__main__':
    main()
