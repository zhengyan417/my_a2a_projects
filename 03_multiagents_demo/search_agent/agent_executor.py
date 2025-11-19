import logging

from typing import  AsyncGenerator

from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue, Event
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCard,
    FilePart,
    FileWithBytes,
    FileWithUri,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils.errors import ServerError
from google.adk import Runner
from google.adk.sessions import Session
from google.genai import types


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

DEFAULT_USER_ID = 'self'

# Executor继承类
class SearchAgentExecutor(AgentExecutor):

    def __init__(self, runner: Runner, card: AgentCard):
        self.runner = runner
        self._card = card

    async def _process_request(
            self,
            new_message: types.Content,
            session_id: str,
            task_updater: TaskUpdater,
    ) -> None:
        # 1.更新或者插入会话id
        session_obj = await self._upsert_session(session_id)
        session_id = session_obj.id

        # 2. 运行智能体，处理请求
        async for event in self.runner.run_async(
                session_id=session_id,
                user_id=DEFAULT_USER_ID,
                new_message=new_message,
        ):
            # 2.1 请求结束
            if event.is_final_response():
                parts = [
                    convert_genai_part_to_a2a(part)
                    for part in event.content.parts
                    if (part.text or part.file_data or part.inline_data)
                ]
                logger.debug('Yielding final response: %s', parts)
                await task_updater.add_artifact(parts)
                await task_updater.update_status( # 更新任务状态：结束
                    TaskState.completed, final=True
                )
                break
            # 2.2 回应事件
            if not event.get_function_calls():
                logger.debug('Yielding update response')
                await task_updater.update_status( # 更新任务状态:工作中
                    TaskState.working,
                    message=task_updater.new_agent_message(
                        [
                            convert_genai_part_to_a2a(part)
                            for part in event.content.parts
                            if (
                                part.text
                                or part.file_data
                                or part.inline_data
                        )
                        ],
                    ),
                )
            else:
                logger.debug('Skipping event')

    # 核心方法，连接服务器时首先执行这个方法
    async def execute(
            self,
            context: RequestContext,
            event_queue: EventQueue,
    ):
        # 运行智能体直到任务完成或者暂停
        # 1. 实例化updater
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        # 2. 提交任务
        if not context.current_task:
            await updater.update_status(TaskState.submitted)
        await updater.update_status(TaskState.working)  # 任务状态：工作
        # 3. 处理请求
        await self._process_request(
            types.UserContent(
                parts=[
                    convert_a2a_part_to_genai(part)
                    for part in context.message.parts
                ],
            ),
            context.context_id,
            updater,
        )
        logger.debug('execute exiting')

    async def cancel(
            self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise ServerError(error=UnsupportedOperationError())

    async def _upsert_session(self, session_id: str) -> Session:
        """检索或者创建一个会话
        """
        session = await self.runner.session_service.get_session(
            app_name=self.runner.app_name,
            user_id=DEFAULT_USER_ID,
            session_id=session_id,
        )
        if session is None:
            session = await self.runner.session_service.create_session(
                app_name=self.runner.app_name,
                user_id=DEFAULT_USER_ID,
                session_id=session_id,
            )
        return session


def convert_a2a_part_to_genai(part: Part) -> types.Part:
    """Convert a single A2A Part type into a Google Gen AI Part type.

    Args:
        part: The A2A Part to convert

    Returns:
        The equivalent Google Gen AI Part

    Raises:
        ValueError: If the part type is not supported
    """
    part = part.root
    if isinstance(part, TextPart):
        return types.Part(text=part.text)
    if isinstance(part, FilePart):
        if isinstance(part.file, FileWithUri):
            return types.Part(
                file_data=types.FileData(
                    file_uri=part.file.uri, mime_type=part.file.mime_type
                )
            )
        if isinstance(part.file, FileWithBytes):
            return types.Part(
                inline_data=types.Blob(
                    data=part.file.bytes, mime_type=part.file.mime_type
                )
            )
        raise ValueError(f'Unsupported file type: {type(part.file)}')
    raise ValueError(f'Unsupported part type: {type(part)}')


def convert_genai_part_to_a2a(part: types.Part) -> Part:
    """Convert a single Google Gen AI Part type into an A2A Part type.

    Args:
        part: The Google Gen AI Part to convert

    Returns:
        The equivalent A2A Part

    Raises:
        ValueError: If the part type is not supported
    """
    if part.text:
        return TextPart(text=part.text)
    if part.file_data:
        return FilePart(
            file=FileWithUri(
                uri=part.file_data.file_uri,
                mime_type=part.file_data.mime_type,
            )
        )
    if part.inline_data:
        return Part(
            root=FilePart(
                file=FileWithBytes(
                    bytes=part.inline_data.data,  # type: ignore
                    mime_type=part.inline_data.mime_type,
                )
            )
        )
    raise ValueError(f'Unsupported part type: {part}')