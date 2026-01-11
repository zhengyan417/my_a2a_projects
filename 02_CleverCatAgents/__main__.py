import logging
import click
import httpx
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
)
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from dotenv import load_dotenv

from agent import CleverCatAgent
from agent_executor import CleverCatAgentExecutor

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10000)
def main(host, port):
    """启动CleverAgent Server"""
    # 1. 定义AgentSkill
    skill = AgentSkill(
        id='decode',
        name='解密工具',
        description='帮助将密文解密得到明文',
        tags=['decode', 'encode'],
        examples=['将"hfashjkfr"这串字符串解密']
    )
    # 2. 定义AgentCard
    agent_card = AgentCard(
        name='Clever Cat Agent',
        description='帮助进行密文的解密',
        url=f'http://{host}:{port}/',
        version='1.0.0',
        default_input_modes=CleverCatAgent.SUPPORTED_CONTENT_TYPES,
        default_output_modes=CleverCatAgent.SUPPORTED_CONTENT_TYPES,
        capabilities=AgentCapabilities(streaming=True, push_notifications=True),
        skills=[skill],
    )

    # 3. 配置服务器
    httpx_client = httpx.AsyncClient()
    push_config_store = InMemoryPushNotificationConfigStore()
    push_sender = BasePushNotificationSender(httpx_client=httpx_client, config_store=push_config_store)
    request_handler = DefaultRequestHandler(
        agent_executor=CleverCatAgentExecutor(),
        task_store=InMemoryTaskStore(),
        push_config_store=push_config_store,
        push_sender=push_sender,
    )
    server = A2AStarletteApplication(
        agent_card=agent_card,http_handler=request_handler
    )

    # 4. 启动服务器
    uvicorn.run(server.build(), host=host, port=port)

if __name__ == '__main__':
    main()