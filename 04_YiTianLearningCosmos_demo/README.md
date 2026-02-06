# 依天学境demo
- 这个项目尝试引入多模态功能、RAG功能、本地大模型调用功能，实现一个能够辅助学生学习的多智能体系统
## 智能体介绍
1. 客户端智能体(ADK框架构建)
- 直接与用户对话，接收用户输入，同时调用合适的远程智能体进行对话，并返回结果给用户
2. 文件解析智能体(llama_index框架构建)
- 接收文件，解析文件，返回解析结果
3. 医生智能体(llama_index框架构建)
- 根据需求检索相关内容，整合内容后返回合适答案
4. 代码智能体(langchain框架构建)
- 接受需求，调用远程代码智能体进行代码生成，返回结果

## A2A服务器
### 启动服务器
1. 启动文件解析智能体A2A服务器
```bash
python 04_YiTianLearningCosmos_demo\file_parse_agent\__main__.py --host localhost --port 10001
```
2. 启动医生智能体A2A服务器
```bash
python 04_YiTianLearningCosmos_demo\docter_agent\__main__.py --host localhost --port 10003
```
3. 启动代码智能体A2A服务器
```bash
python 04_YiTianLearningCosmos_demo\code_agent\__main__.py --host localhost --port 10002
```

## A2A客户端
### 启动客户端
```bash
cd 04_YiTianLearningCosmos_demo\a2a_client
adk web --port 8030
```

## 测试对话
- 你这个多智能体系统有什么功能？
- 帮我生成懒线段树的模板代码，用python实现。给我完整代码实现，其他描述都不需要。
- 帮我解析一个文件，路径:C:\study\agent_communication\Projects\myA2AProjects\04_YiTianLearningCosmos_demo\file_parse_agent\attention.pdf