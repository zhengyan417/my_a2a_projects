import logging

from typing import Any
from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
)
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
    EXTENDED_AGENT_CARD_PATH,
)

async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    base_url = 'http://localhost:10000'

    async with httpx.AsyncClient() as httpx_client:
        # 1.初始化A2ACardResolver
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)

        # 2.获取AgentCard
        final_agent_card: AgentCard | None = None

        try:
            # 2.1 获取初版的agentCard
            logger.info(f"尝试从{base_url}{AGENT_CARD_WELL_KNOWN_PATH}获取初版AgentCard")
            _public_card = (await resolver.get_agent_card())  # resolver获取AgentCard
            logger.info("成功获取AgentCard:")
            logger.info(_public_card.model_dump_json(indent=2, exclude_none=True))
            final_agent_card = _public_card  # 第一个获得的agentCard

            # 2.2 获取高级的agentCard
            if _public_card.supports_authenticated_extended_card:
                try:
                    logger.info(f"\n尝试从{base_url}{AGENT_CARD_WELL_KNOWN_PATH}获取扩展的AgentCard")
                    # 定义令牌
                    auth_headers_dict = {
                        'Authorization': "Bearer dummy-token-for-extended-card"
                    }
                    # 尝试获取高级AgentCard
                    _extend_card = await resolver.get_agent_card(
                        relative_card_path=EXTENDED_AGENT_CARD_PATH,
                        http_kwargs={'headers': auth_headers_dict}
                    )
                    logger.info("成功获取扩展版AgentCard:")
                    logger.info(
                        _extend_card.model_dump_json(
                            indent=2, exclude_none=True
                        )
                    )
                    final_agent_card = _extend_card  # 第二个AgentCard
                except Exception as e_extended:
                    logger.warning(
                        f'无法获取扩展版agentCard:{e_extended},将使用公开的public card.',
                        exc_info=True,
                    )
            elif _public_card:
                logger.info("\n只有公共的Agent card.")
        except Exception as e:
            logger.error(
                f"获取AgentCard时出错:{e}",
                exc_info=True
            )
            raise RuntimeError(
                "无法获取AgentCard"
            ) from e

        # 3. 发送信息
        # 3.1 配置客户端
        client = A2AClient(httpx_client=httpx_client, agent_card=final_agent_card)
        logger.info("客户端初始化完成")

        # # 3.2 单轮测试
        # # 配置发送的信息
        # send_message_payload: dict[str, Any] = {
        #     'message': {
        #         'role': 'user',
        #         'parts': [
        #             {'kind': 'text', 'text': '帮我把"CBMeEHwsKzctOTs="这串字符串解密'}
        #         ],
        #         'messageId': uuid4().hex,
        #     },
        # }
        #
        # requests = SendMessageRequest(id=str(uuid4()), params=MessageSendParams(**send_message_payload))
        # # 开始传输
        # response = await client.send_message(requests)
        # print(response.model_dump(mode='json', exclude_none=True))


        # 3.2 多轮测试
        first_message: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {
                        'kind': 'text',
                        'text': '帮我解密一下这串字符串',
                    }
                ],
                'message_id': uuid4().hex,
            },
        }
        requests = SendMessageRequest(id=str(uuid4()), params=MessageSendParams(**first_message))

        # 获取回复
        response = await client.send_message(requests)
        print(response.model_dump(mode='json', exclude_none=True))

        # 得到taskid和context_id
        task_id = response.root.result.id
        context_id = response.root.result.context_id

        # 进行第二次发送
        second_message: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {
                        'kind': 'text',
                        'text': '这串字符串是"CBMeEHwsKzctOTs="',
                    }
                ],
                'message_id': uuid4().hex,
                'task_id': task_id,
                'context_id': context_id,
            },
        }
        second_requests = SendMessageRequest(id=str(uuid4()), params=MessageSendParams(**second_message))

        # 获得回应
        second_response = await client.send_message(second_requests)
        print(second_response.model_dump(mode='json', exclude_none=True))

if __name__ == '__main__':
    import asyncio

    asyncio.run(main())

'''
# 单轮测试回复
{
'id': 'f774fb26-a2b8-4c90-a73e-3042fcaee93a', 
'jsonrpc': '2.0', 
'result': {
    'artifacts': [
        {
            'artifactId': '433d28d2-376e-47c6-8ec9-f48b072e624e', 
            'name': 'conversion_result', 
            'parts': [{'kind': 'text', 'text': '解密结果：BUPT=beiyou'}]
        }
    ], 
    'contextId': '064befba-e056-418c-9e08-0ac4fbd083f0', 
    'history': [
        {
            'contextId': '064befba-e056-418c-9e08-0ac4fbd083f0', 
            'kind': 'message', 
            'messageId': '58f84035800745799b042c4aa06c7bdb', 
            'parts': [{'kind': 'text', 'text': '帮我把"ODM9MDcvPC03"这串字符串解密'}], 
            'role': 'user', 
            'taskId': '7e74460e-20f1-4e3d-9d68-3819816eae7b'
        }, 
    ], 
    'id': '7e74460e-20f1-4e3d-9d68-3819816eae7b', 
    'kind': 'task', 
    'status': {
        'state': 'completed', 
        'timestamp': '2025-10-31T13:35:04.888808+00:00'
    }
 }
}


# 多轮测试第一次回复    
 {
 'id': 'be824dda-689b-4f16-9ee2-a8436a0c93f6', 
 'jsonrpc': '2.0', 
 'result': 
    {
    'contextId': 'ca3dc7b5-cafc-4b51-b18e-3e9091d62761', 
    'history': 
        [
            {
                'contextId': 'ca3dc7b5-cafc-4b51-b18e-3e9091d62761', 
                'kind': 'message', #message类型
                'messageId': '06167206aefa4b3492c9885fbd35c524', 
                'parts': [{'kind': 'text', 'text': '帮我解密一下这串字符串'}], 
                'role': 'user', 
                'taskId': 'ca0a58b5-d146-4e1e-942b-182f209232b6'
            }, 
            {
                'contextId': 'ca3dc7b5-cafc-4b51-b18e-3e9091d62761', 
                'kind': 'message',  #message类型
                'messageId': '0f7c39ef-3779-476f-aba7-c7befa3a872d', 
                'parts': [{'kind': 'text', 'text': '正在破译中...'}], 
                'role': 'agent', 
                'taskId': 'ca0a58b5-d146-4e1e-942b-182f209232b6'
            }
        ], 
    'id': 'ca0a58b5-d146-4e1e-942b-182f209232b6', 
    'kind': 'task',  !!!task类型!!!
    'status': 
        {
        'message': 
            {
                'contextId': 'ca3dc7b5-cafc-4b51-b18e-3e9091d62761', 
                'kind': 'message',
                'messageId': '8cfad882-d5e5-4d64-9e55-a9f10b23ca93', 
                'parts': [{'kind': 'text', 'text': '您好！我很乐意帮您解密字符串，但是您还没有提供需要解密的密文内容。请您提供要解密的加密字符串，这样我就能使用解密工具为您服务了。'}], 
                'role': 'agent', 
                'taskId': 'ca0a58b5-d146-4e1e-942b-182f209232b6'
            }, 
        'state': 'input-required', 
        'timestamp': '2025-10-31T12:53:13.530856+00:00'
        }
    }
 }
 
# 多轮测试第二次回复
{
'id': 'b0341b7b-15ac-46f8-b88b-da422d9e5003', 
'jsonrpc': '2.0', 
'result': {
    'artifacts': [
        {
            'artifactId': 'fb9592ba-28ac-488a-99c5-335ff73ad21d', 
            'name': 'conversion_result', 
            'parts': [{'kind': 'text', 'text': '解密结果：BUPT=beiyou'}]}], 
            'contextId': 'ca3dc7b5-cafc-4b51-b18e-3e9091d62761', 
            'history': [
                {
                    'contextId': 'ca3dc7b5-cafc-4b51-b18e-3e9091d62761', 
                    'kind': 'message', 
                    'messageId': '06167206aefa4b3492c9885fbd35c524', 
                    'parts': [{'kind': 'text', 'text': '帮我解密一下这串字符串'}], 
                    'role': 'user', 
                    'taskId': 'ca0a58b5-d146-4e1e-942b-182f209232b6'
                }, 
                {
                    'contextId': 'ca3dc7b5-cafc-4b51-b18e-3e9091d62761', 
                    'kind': 'message', 
                    'messageId': '0f7c39ef-3779-476f-aba7-c7befa3a872d', 
                    'parts': [{'kind': 'text', 'text': '正在破译中...'}], 
                    'role': 'agent', 
                    'taskId': 'ca0a58b5-d146-4e1e-942b-182f209232b6'
                }, 
                {
                    'contextId': 'ca3dc7b5-cafc-4b51-b18e-3e9091d62761', 
                    'kind': 'message', 
                    'messageId': '8cfad882-d5e5-4d64-9e55-a9f10b23ca93', 
                    'parts': [{'kind': 'text', 'text': '您好！我很乐意帮您解密字符串，但是您还没有提供需要解密的密文内容。请您提供要解密的加密字符串，这样我就能使用解密工具为您服务了。'}], 
                    'role': 'agent', 
                    'taskId': 'ca0a58b5-d146-4e1e-942b-182f209232b6'
                }, 
                {
                    'contextId': 'ca3dc7b5-cafc-4b51-b18e-3e9091d62761', 
                    'kind': 'message', 
                    'messageId': '642a497f7792411898d83ce0ac84d12d', 
                    'parts': [{'kind': 'text', 'text': '这串字符串是"ODM9MDcvPC03"'}], 
                    'role': 'user', 
                    'taskId': 'ca0a58b5-d146-4e1e-942b-182f209232b6'
                }, 
                {
                    'contextId': 'ca3dc7b5-cafc-4b51-b18e-3e9091d62761', 
                    'kind': 'message', 
                    'messageId': 'c17982fd-4915-41fe-939b-018207a61eb4', 
                    'parts': [{'kind': 'text', 'text': '正在准备破译...'}], 
                    'role': 'agent', 
                    'taskId': 'ca0a58b5-d146-4e1e-942b-182f209232b6'
                }, 
                {
                    'contextId': 'ca3dc7b5-cafc-4b51-b18e-3e9091d62761', 
                    'kind': 'message', 
                    'messageId': 'bb52811b-b5ab-4e42-a4fa-716fa0543086', 
                    'parts': [{'kind': 'text', 'text': '正在破译中...'}], 
                    'role': 'agent', 
                    'taskId': 'ca0a58b5-d146-4e1e-942b-182f209232b6'
                }, 
                {
                    'contextId': 'ca3dc7b5-cafc-4b51-b18e-3e9091d62761', 
                    'kind': 'message', 
                    'messageId': '732c7c14-ae65-4cb5-b213-817060959aeb', 
                    'parts': [{'kind': 'text', 'text': '正在破译中...'}], 
                    'role': 'agent', 
                    'taskId': 'ca0a58b5-d146-4e1e-942b-182f209232b6'
                }
        ], 
        'id': 'ca0a58b5-d146-4e1e-942b-182f209232b6', 
        'kind': 'task', 
        'status': {
            'state': 'completed', 
            'timestamp': '2025-10-31T12:53:18.033336+00:00'
        }
    }
}
'''