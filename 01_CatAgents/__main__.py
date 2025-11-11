import uvicorn   # ASGI服务器

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler  #默认请求处理
from a2a.server.tasks import InMemoryTaskStore    #记忆任务存储
from a2a.types import (AgentCapabilities, AgentCard, AgentSkill)  #A2A里的一些类
from agent_executor import CatAgentExecutor

if __name__ == "__main__":
    # 1.定义agentSkill
    skill = AgentSkill(
        id='miaow',
        name="猫叫",
        description="只是猫叫",
        tags=['miaow'],
        examples=['喵', '喵喵喵'],
    )
    # 支持agent skill的扩展
    extended_skill = AgentSkill(
        id='say_hello',
        name="说你好",
        description="可以说你好",
        tags=["say hello"],
        examples=['你好'],
    )

    # 2.定义agentCard
    public_agent_card = AgentCard(
        name='Cat Agent',
        description="只是一个CatAgent",
        url='http://localhost:8888/',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True), #支持流式消息
        skills=[skill],
        supports_authenticated_extended_card=True,
    )
    # 支持agent card的扩展
    specific_extended_agent_card = public_agent_card.model_copy(
        update={
            'name': "Cat Agent - Extended Edition",
            'description': 'Cat Agent可以向认证后的用户问好',
            'version': '1.0.2',
            'skills':[skill, extended_skill],
            # 其他没列出的会被继承
        }
    )

    # 3. 构建A2A服务器
    # 3.1 定义请求处理方法
    request_handle = DefaultRequestHandler(
        agent_executor=CatAgentExecutor(),  # 接入CatAgent
        task_store=InMemoryTaskStore(),  # 记忆任务
    )

    # 3.2 构建服务器
    server = A2AStarletteApplication(
        agent_card=public_agent_card,
        http_handler=request_handle,
        extended_agent_card=specific_extended_agent_card,
    )

    # 4 运行A2A服务器
    uvicorn.run(server.build, host='0.0.0.0', port=8888)