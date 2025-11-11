import logging

from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.utils.errors import ServerError
from a2a.utils import new_task, new_agent_text_message
from a2a.types import (
    InternalError,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)

from agent import CleverCatAgent
from a2a.server.agent_execution import AgentExecutor, RequestContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CleverCatAgentExecutor(AgentExecutor):

    # 1.创建CleverCatAgent
    def __init__(self):
        self.agent = CleverCatAgent()

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        query = context.get_user_input() # 获得用户请求
        task = context.current_task  # 获得当前的任务
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)  # 如果当前没有任务，创建新的任务

        updater = TaskUpdater(event_queue, task.id, task.context_id)
        # 流式调用
        try:
            async for item in self.agent.stream(query, task.context_id):
                is_task_complete = item['is_task_complete']
                require_user_input = item['require_user_input']

                # 任务正在处理中
                if not is_task_complete and not require_user_input:
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(
                            item['content'],
                            task.context_id,
                            task.id,
                        ),
                    )
                # 需要用户额外输入
                elif require_user_input:
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(
                            item['content'],
                            task.context_id,
                            task.id,
                        ),
                        final=True,
                    )
                # 任务执行完成
                else:
                    await updater.add_artifact(
                        [Part(root=TextPart(text=item['content']))],
                        name='conversion_result',
                    )
                    await updater.complete()
                    break

        except Exception as e:
            logger.error(f"在流式调用时出现了错误：{e}")
            raise ServerError(error=InternalError()) from e

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise ServerError(error=UnsupportedOperationError())

