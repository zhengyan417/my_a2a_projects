# 文件管理多智能体系统
- 这个多智能体系统集成了MCP、A2A协议，采用langchain和ADK框架制作完成。
- 这个多智能体系统可以对Top_secret_materials文件进行管理，由规划智能体直接接收用户输入并且将任务进行分解，之后规划智能体通过A2A协议与文件智能体
、聪明猫智能体或者搜索智能体进行任务的指派。
- Top_secret_materials文件夹里面存储的内容都是密文，所以你必须依靠这个多智能体系统才可以正常管理这个文件.
- 文件智能体可以对Top_secret_materials里面的文件进行增删改查以及查询这个文件夹里面目前有的文件。
- 聪明猫智能体可以对密文进行加密或者对明文进行解密。
- 搜索智能体可以获取当前时间、天气，以及调用搜索引擎。

# 运行指令
**请先配置好虚拟环境和.env**  


### 在五个终端中依次进行以下操作和运行以下指令
#### MCPserver  
```bash
python 03_multiagents_demo/MCPserver/file_change_MCPserver.py
```

#### A2Aserver-1  
```bash
python 03_multiagents_demo/clever_cat_agent/__main__.py --port 10000
```

#### A2Aserver-2
```bash
python 03_multiagents_demo/file_agent/__main__.py --port 10001
```

#### A2Aserver-3(**目前该server存在bug，在没有修复前不建议运行**)
```bash
python 03_multiagents_demo/search_agent/__main__.py --port 10002
```

#### A2Aclient   
1. 
- **修改03_multiagents_demo/a2a_client/client_host_agent/agent.py里已经启动的远程的a2a_server**
2. 
```bash
cd 03_multiagents_demo/a2a_client    
adk web --port 8030
```

### 示例用户输入
1. 智能体介绍
- 这个智能体系统有什么功能？
2. 测试单一智能体是否能正常运行
- 目前文件夹里面有什么文件？
- 帮我加密beiyouBUPT这个字符串
- 帮我查询当前的时间
3. 测试多个智能体协同工作
- 帮我创建一个叫test3,txt的文本文件，里面写上YiTianLearningCosmos的加密后的字符串，以确保文件的安全性,同时在文件末尾添加当前时间。
4. 测试输入不完整的task能否正常处理
- 帮我创建一个叫test4.txt的文本文件，里面写上我目前居住城市的天气，注意要加密
- 忘了说了，我现在居住在BeiJing
