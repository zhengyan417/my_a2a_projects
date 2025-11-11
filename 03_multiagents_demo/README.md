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
- 若选择client_host_agent  
```bash
cd 03_multiagents_demo   
adk web --port 8030
```  
- 若选择host_agent_adk  
```bash
cd 03_multiagents_demo/host_agent_adk   
adk web --port 8030
```

### 示例用户输入
- 这个智能体系统有什么功能？
- 帮我创建一个叫test1.txt的文本文件，里面写上1234。
- 明文是beiyouBUPT,帮我加密。
- 帮我创建一个叫test3,txt的文本文件，里面写上YiTianLearningCosmos的加密后的字符串，以确保文件的安全性。
- 帮我创建一个叫test4.txt的文本文件，里面写上加密后的字符串：
- 未加密的明文是my_a2a_projects
