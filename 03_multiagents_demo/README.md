# 文件管理多智能体系统
- 这个多智能体系统集成了MCP、A2A协议，采用langchain和ADK框架制作完成。
- 这个多智能体系统可以对Top_secret_materials文件进行管理，由规划智能体直接接收用户输入并且将任务进行分解，之后规划智能体通过A2A协议与文件智能体
或者聪明猫智能体进行任务的指派。
- Top_secret_materials文件夹里面存储的内容都是密文，所以你必须依靠这个多智能体系统才可以正常管理这个文件.
- 文件智能体可以对Top_secret_materials里面的文件进行增删改查以及查询这个文件夹里面目前有的文件。
- 聪明猫智能体可以对密文进行加密或者对明文进行解密。

# 运行指令
**请先配置好虚拟环境和.env**  

这个项目我准备了两个client，可以自行选择运行哪个client。

- MCPserver  
```bash
cd 03_multiagents_demo   
python MCPserver/file_change_MCPserver.py
```

- A2Aserver-1  
```bash
cd 03_multiagents_demo   
python clever_cat_agent/__main__.py --port 10000
```

- A2Aserver-2
```bash
cd 03_multiagents_demo   
python file_agent/__main__.py --port 10001
```

- A2Aclient   
```bash
cd 03_multiagents_demo   
adk web --port 8030
```

### 示例用户输入
- 这个智能体系统有什么功能？
- 目前文件夹里面有什么文件？
- 帮我查询init_file.txt里面的内容，注意要先把内容解密，不要直接给我密文
- 帮我创建一个叫test1.txt的文本文件，里面写上1234。
- 明文是beiyouBUPT,帮我加密。
- 帮我创建一个叫test3,txt的文本文件，里面写上YiTianLearningCosmos的加密后的字符串，以确保文件的安全性。
- 帮我创建一个叫test4.txt的文本文件，里面写上加密后的字符串：
- 未加密的明文是my_a2a_projects
