import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import (
    InMemoryTaskStore,
)
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from dotenv import load_dotenv

from agent import FileAgent
from agent_executor import FileAgentExecutor

load_dotenv()

def main(host="localhost", port=10001):
    """启动CleverAgent Server"""
    # 1. 定义AgentSkill
    change_file_skill = AgentSkill(
        id='change_file',
        name='文件操作工具',
        description='对文件进行增删改查,以及查询文件夹目前有的文件',
        tags=['file', 'create file', 'delete file'],
        examples=[r'帮我创建一个叫test1.txt的文件, 里面写上1234',
                  r'帮我删除一个叫test1.txt的文件',
                  r'帮我查询这个文件夹目前的内容']
    )
    # 2. 定义AgentCard
    agent_card = AgentCard(
        name='File Agent',
        description='帮助进行文件的增删改查',
        url=f'http://{host}:{port}/',
        version='1.0.0',
        default_input_modes=FileAgent.SUPPORTED_CONTENT_TYPES,
        default_output_modes=FileAgent.SUPPORTED_CONTENT_TYPES,
        capabilities=AgentCapabilities(streaming=True, push_notifications=True),
        skills=[change_file_skill],
    )

    # 3. 配置服务器
    request_handler = DefaultRequestHandler(
        agent_executor=FileAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    server = A2AStarletteApplication(
        agent_card=agent_card,http_handler=request_handler
    )

    # 4. 启动服务器
    uvicorn.run(server.build(), host=host, port=port)

if __name__ == '__main__':
    main()
