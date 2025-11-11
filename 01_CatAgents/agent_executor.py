from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message

# 1. 定义Cat Agent类
class CatAgent:
    """Cat Agent"""

    async def invoke(self) -> str:
        return "喵喵喵"

# 2. 定义Cat Agent Executor类
class CatAgentExecutor(AgentExecutor):

    #2.1 初始化
    def __init__(self):
        self.agent = CatAgent()

    #2.2 定义execute函数(继承自AgentExecutor基类,必须实现)
    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        result = await self.agent.invoke()  # 调用CatAgent
        await event_queue.enqueue_event(new_agent_text_message(result))  #通过事件队列传输结果

    # 2.3 定义cancel函数(继承自AgentExecutor基类,必须实现)
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception('系统提示：CatAgent没有取消功能')