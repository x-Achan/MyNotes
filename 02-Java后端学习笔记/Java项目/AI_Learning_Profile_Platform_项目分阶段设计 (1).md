# AI Learning Profile Platform 项目分阶段设计 v0.1

> 项目中文名：AI 学习档案与简历分析平台  
> 项目英文名：AI Learning Profile Platform  
> 当前定位：面向个人学习成长、Java 后端实习能力建设、AI 应用实践与未来 Agent 能力拓展的综合型 Java 后端项目。

---

## 1. 项目背景

对于当前的软件工程研究生而言，学习任务往往同时包含 Java 后端就业、LeetCode 算法、科研论文、深度学习实验、AI / Agent 工具使用等多条主线。传统的学习记录方式容易出现以下问题：

1. 学习资料分散在 Obsidian、GitHub、博客、聊天记录、实验日志中。
2. AI 工具无法快速理解用户的真实技术画像。
3. 学习计划容易过于宏大，缺少阶段任务和验收标准。
4. 科研实验记录不规范，AI 修改代码后难以复盘。
5. 简历项目缺少真实需求背景，容易变成模板化 CRUD 项目。

因此，本项目希望构建一个面向个人成长的 AI 学习档案平台，通过 Java 后端能力实现用户系统、个人技术画像管理、学习记录管理、科研实验记录、AI 分析与后续 Agent 工作流。

---

## 2. 项目一句话定位

一个面向学生和技术学习者的 AI 学习档案管理平台，支持维护个人技术画像、学习记录、刷题记录、科研实验记录，并接入大模型 API 生成学习建议、简历分析、阶段任务规划和长期成长复盘。

---

## 3. 项目核心价值

### 3.1 对个人学习的价值

本项目不是单纯为了简历而做，而是可以真实服务自己的学习系统：

- 管理个人 AI 技术画像
- 管理 Java 学习进度
- 管理 LeetCode 刷题记录
- 管理科研实验记录
- 管理 AI 工具协作记录
- 生成阶段任务建议
- 辅助简历优化与项目表达

### 3.2 对 Java 后端实习的价值

项目可以覆盖 Java 后端实习常见核心技术：

- Spring Boot
- MySQL
- MyBatis-Plus
- Redis
- JWT / Sa-Token
- 统一返回结果
- 全局异常处理
- 参数校验
- 接口文档
- 文件上传
- AI API 调用
- 异步任务
- 接口限流
- Docker 部署

### 3.3 对 AI / Agent 能力的价值

项目后期可以逐步接入 AI 和 Agent 能力：

- 大模型 API 调用
- Prompt 模板管理
- 用户画像分析
- 学习计划生成
- 简历分析
- 实验记录总结
- 简单任务规划 Agent
- 未来个人知识库 / RAG 扩展

---

## 4. 项目不做什么

为了避免项目一开始过大，当前阶段不做以下内容：

1. 不一开始做复杂微服务架构。
2. 不一开始做完整高并发系统。
3. 不一开始做复杂 Agent 框架。
4. 不一开始做复杂前端。
5. 不一开始做 Spring 源码级研究。
6. 不一开始接入太多模型供应商。
7. 不为了炫技堆技术，而是按阶段增加能力。

项目的核心原则是：

> 先完成可运行的 Java 后端闭环，再逐步叠加 AI、Redis、工程优化和 Agent 能力。

---

## 5. 技术栈规划

### 5.1 第一阶段技术栈

用于完成最小后端闭环：

- Java 17 或 Java 21
- Spring Boot
- Spring Web
- Maven
- Git / GitHub
- Apifox / Postman

### 5.2 第二阶段技术栈

用于完成数据库和用户系统：

- MySQL
- MyBatis-Plus
- Lombok
- Spring Validation
- 全局异常处理
- 统一响应结构

### 5.3 第三阶段技术栈

用于登录鉴权与真实项目化：

- JWT 或 Sa-Token
- 密码加密 BCrypt
- 拦截器 / 过滤器
- 用户权限校验

### 5.4 第四阶段技术栈

用于 AI 应用能力：

- 大模型 API，例如智谱、通义、OpenAI、DeepSeek 等
- RestTemplate / WebClient / OpenFeign
- Prompt 模板管理
- AI 调用日志记录
- AI 分析结果持久化

### 5.5 第五阶段技术栈

用于工程优化和进阶能力：

- Redis
- 缓存过期时间
- 接口限流
- 防重复提交
- 异步任务
- Docker
- 日志系统

### 5.6 未来可扩展技术栈

后期根据能力再考虑：

- 消息队列 RabbitMQ / Kafka
- Elasticsearch
- RAG 知识库
- LangChain4j / Spring AI
- 分布式任务调度
- 微服务架构
- 监控与链路追踪

---

## 6. 项目整体模块设计

### 6.1 用户中心模块

基础功能：

- 用户注册
- 用户登录
- 用户登出
- 查询当前用户信息
- 修改用户信息
- 修改密码
- 登录态校验
- 权限校验

核心意义：

这是所有后端项目的基础模块，也是 Java 实习面试中最容易被问到的模块。

---

### 6.2 个人技术画像模块

功能：

- 创建个人技术画像
- 编辑个人技术画像
- 查询个人技术画像
- 按模块管理技术能力
- 记录能力评分
- 记录阶段目标
- 记录能力变化历史

建议画像模块包括：

- 基本信息
- Java 技术栈
- LeetCode 算法能力
- 科研 / 深度学习能力
- AI 工具使用情况
- 当前阶段目标
- 项目经历
- 实习目标

核心意义：

这个模块直接来自个人真实需求，可以体现业务建模能力，也可以为后续 AI 分析提供数据基础。

---

### 6.3 学习记录模块

功能：

- 新增学习记录
- 查询学习记录
- 按类型筛选学习记录
- 按日期筛选学习记录
- 按标签筛选学习记录
- 学习记录归档

学习记录类型：

- Java 学习
- Spring Boot 学习
- MySQL 学习
- Redis 学习
- LeetCode 刷题
- 深度学习理论
- 科研代码阅读
- 科研实验记录
- AI 工具使用记录

核心意义：

这个模块可以体现复杂条件查询、分页查询、标签系统、用户数据隔离等后端能力。

---

### 6.4 LeetCode 刷题记录模块

功能：

- 记录题号、题名、难度、题型
- 记录是否独立完成
- 记录题解思路
- 记录 Java 代码
- 记录易错点
- 记录复习次数
- 记录掌握程度

字段建议：

- 题号
- 题名
- 难度
- 题型
- 标签
- 初次完成日期
- 是否独立完成
- 掌握程度
- 核心思路
- 易错点
- 相似题

核心意义：

这个模块可以服务真实算法学习，同时后期可以让 AI 分析薄弱题型。

---

### 6.5 科研实验记录模块

功能：

- 新增实验记录
- 记录实验编号
- 记录模型结构
- 记录数据集
- 记录配置文件
- 记录训练命令
- 记录代码版本
- 记录 loss 和 mAP
- 记录可视化结果路径
- 记录 AI 修改代码内容
- 记录实验结论和下一步动作

字段建议：

- 实验编号
- 实验名称
- 数据集
- 模型
- 代码仓库
- Git 分支
- Commit ID
- 训练命令
- 配置文件
- 是否使用预训练权重
- 训练轮数
- mAP
- loss 变化
- 可视化结果
- 实验结论
- 下一步计划

核心意义：

这个模块可以和科研主线强绑定，并体现项目的个性化价值。

---

### 6.6 AI 协作记录模块

功能：

- 记录使用的 AI 工具
- 记录 Prompt
- 记录 AI 修改的文件
- 记录修改原因
- 记录验证结果
- 标记是否采纳

AI 工具类型：

- ChatGPT
- Claude Code
- Codex
- Cursor
- Copilot
- 其他

核心意义：

这是一个非常贴合当前 AI 辅助学习和科研代码开发的模块。它可以体现你对 AI 工程化协作的理解，而不是只会调用模型 API。

---

### 6.7 简历分析模块

功能：

- 上传简历文本或 PDF
- 提取简历内容
- 分析技术栈覆盖情况
- 分析项目表达问题
- 根据目标岗位给出优化建议
- 保存历史分析记录

第一版可以不做复杂 PDF 解析，先支持用户粘贴简历文本。

后续再扩展：

- PDF 上传
- 简历解析
- 岗位 JD 匹配
- 简历评分
- 项目亮点生成

---

### 6.8 AI 阶段任务规划模块

功能：

- 读取用户技术画像
- 读取最近学习记录
- 读取刷题记录
- 读取科研实验记录
- 调用大模型生成阶段任务建议
- 将建议保存为任务看板

输出内容：

- 当前阶段判断
- Java 主线任务
- 算法主线任务
- 科研主线任务
- AI 工具使用建议
- 每项任务的验收标准

这是后期 Agent 雏形的核心模块。

---

## 7. 分阶段开发路线

## 阶段 0：项目初始化与 Spring Boot 入门

### 目标

完成最小 Spring Boot 后端项目，建立工程基础。

### 功能

- 创建 Spring Boot 项目
- 编写 `/hello` 接口
- 配置 Maven
- 项目上传 GitHub
- 编写基础 README

### 学习重点

- Spring Initializr
- Maven 项目结构
- Controller 基础
- Spring Boot 启动流程
- Git 提交规范

### 验收标准

- 项目能正常启动
- 浏览器访问 `localhost:8080/hello` 能返回字符串
- GitHub 上有完整代码
- README 中写清楚如何启动项目

---

## 阶段 1：用户中心基础版

### 目标

完成标准后端项目的基础用户模块。

### 功能

- 用户注册
- 用户登录
- 用户信息查询
- 用户信息修改
- 用户删除
- 用户列表分页查询

### 学习重点

- Controller / Service / Mapper / Entity 分层
- MySQL 表设计
- MyBatis-Plus CRUD
- 统一返回结果
- 全局异常处理
- 参数校验

### 验收标准

- 能设计 `user` 表
- 能通过接口完成用户 CRUD
- 能用 Apifox / Postman 测试接口
- 能讲清楚项目分层结构
- 能讲清楚 Entity、Mapper、Service、Controller 的关系

---

## 阶段 2：登录鉴权版

### 目标

让项目具备真实登录态和权限校验能力。

### 功能

- 密码加密存储
- 登录后返回 token
- 查询当前登录用户
- 未登录请求拦截
- 用户登出
- 基础权限校验

### 技术选择

可以选择：

- JWT
- Sa-Token

对于当前阶段，Sa-Token 上手更快；JWT 更适合理解 token 原理。可以先用 JWT 或 Sa-Token 任选其一，不要两个都做。

### 验收标准

- 密码不能明文存储
- 登录后能获取 token
- 携带 token 才能访问用户信息接口
- 未登录访问受保护接口会被拒绝
- 能解释 token 的作用

---

## 阶段 3：个人技术画像管理版

### 目标

把当前个人 AI 技术画像产品化，形成项目特色。

### 功能

- 创建个人技术画像
- 编辑个人技术画像
- 查询个人技术画像
- 技术模块管理
- 技能项管理
- 能力评分记录
- 阶段目标记录

### 建议表设计

- `profile`：个人画像主表
- `skill_module`：技术模块表
- `skill_item`：技能项表
- `stage_goal`：阶段目标表
- `profile_version`：画像版本记录表，可后续添加

### 验收标准

- 一个用户可以维护自己的技术画像
- 技术画像可以分模块展示
- 每个技能项可以记录评分和说明
- 可以保存当前阶段目标
- 接口支持增删改查和分页查询

---

## 阶段 4：学习记录与刷题记录版

### 目标

让平台成为真正可用的学习档案系统。

### 功能

- 新增学习记录
- 查询学习记录
- 按类型筛选
- 按标签筛选
- 记录 LeetCode 题目
- 记录掌握程度
- 记录错题和复习次数

### 建议表设计

- `learning_record`：学习记录表
- `leetcode_record`：刷题记录表
- `tag`：标签表
- `record_tag_relation`：记录与标签关系表

### 验收标准

- 可以记录 Java 学习、算法刷题、科研实验等不同类型内容
- 可以按类型、标签、日期查询
- 可以查看刷题掌握情况
- 可以统计不同题型数量

---

## 阶段 5：科研实验记录版

### 目标

服务科研主线，规范记录实验过程。

### 功能

- 新增实验记录
- 记录实验配置
- 记录训练命令
- 记录代码版本
- 记录指标结果
- 记录 AI 修改代码过程
- 记录下一步实验计划

### 建议表设计

- `experiment_record`：实验记录主表
- `experiment_metric`：实验指标表
- `ai_code_change_record`：AI 代码修改记录表

### 验收标准

- 每次实验可以完整记录配置、命令、指标、结论
- 可以查询历史实验
- 可以对比不同实验的 mAP / loss
- 可以记录 Claude Code / Codex 对代码的修改

---

## 阶段 6：AI 模型调用版

### 目标

让平台具备 AI 分析能力。

### 功能

- AI 分析个人画像
- AI 生成阶段学习建议
- AI 分析刷题薄弱点
- AI 分析科研实验记录
- AI 分析简历文本
- 保存 AI 分析历史

### 学习重点

- 模型 API 调用
- Prompt 设计
- 请求封装
- 响应解析
- 异常处理
- 调用日志记录

### 建议表设计

- `ai_prompt_template`：Prompt 模板表
- `ai_call_log`：AI 调用日志表
- `ai_analysis_result`：AI 分析结果表

### 验收标准

- 后端可以成功调用一个大模型 API
- 可以把用户画像发送给模型分析
- 可以保存 AI 返回结果
- 可以查看历史 AI 分析记录
- 模型调用失败时有异常处理

---

## 阶段 7：Redis 与工程优化版

### 目标

提升项目工程质量，补充实习面试高频技术点。

### 功能

- 登录 token 缓存
- 用户信息缓存
- AI 分析结果缓存
- 接口限流
- 防重复提交
- 验证码缓存

### 学习重点

- RedisTemplate / StringRedisTemplate
- 缓存过期时间
- 缓存穿透
- 缓存击穿
- 缓存雪崩
- 简单限流设计

### 验收标准

- Redis 成功接入项目
- 登录态可以存入 Redis
- AI 分析结果可以缓存
- 高频接口可以做简单限流
- 能讲清楚缓存常见问题

---

## 阶段 8：Agent 雏形版

### 目标

形成一个简单的学习规划 Agent 工作流。

### 工作流

1. 读取用户画像
2. 读取最近学习记录
3. 读取最近刷题记录
4. 读取最近科研实验记录
5. 判断当前阶段薄弱点
6. 生成下一阶段任务建议
7. 写入任务看板

### 功能

- 任务生成
- 任务状态管理
- 任务验收标准生成
- 阶段复盘生成

### 建议表设计

- `task_board`：任务看板表
- `task_item`：任务项表
- `agent_run_log`：Agent 运行日志表

### 验收标准

- 可以基于用户画像生成任务建议
- 可以把任务建议保存为任务看板
- 每个任务有验收标准
- 可以记录 Agent 的输入、输出和运行历史

---

## 8. 建议项目目录结构

```text
ai-learning-profile-backend/
├── src/
│   ├── main/
│   │   ├── java/
│   │   │   └── com/achan/learningprofile/
│   │   │       ├── common/
│   │   │       │   ├── result/
│   │   │       │   ├── exception/
│   │   │       │   └── constant/
│   │   │       ├── config/
│   │   │       ├── controller/
│   │   │       ├── service/
│   │   │       │   └── impl/
│   │   │       ├── mapper/
│   │   │       ├── model/
│   │   │       │   ├── entity/
│   │   │       │   ├── dto/
│   │   │       │   └── vo/
│   │   │       ├── ai/
│   │   │       ├── auth/
│   │   │       └── LearningProfileApplication.java
│   │   └── resources/
│   │       ├── mapper/
│   │       ├── application.yml
│   │       └── application-dev.yml
│   └── test/
├── docs/
│   ├── 项目设计文档.md
│   ├── 数据库设计.md
│   ├── 接口文档.md
│   ├── 阶段开发记录.md
│   └── AI协作记录.md
├── README.md
└── pom.xml
```

---

## 9. 数据库初步设计

### 9.1 user 用户表

```sql
CREATE TABLE user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(64) NOT NULL,
    password VARCHAR(255) NOT NULL,
    nickname VARCHAR(64),
    email VARCHAR(128),
    role VARCHAR(32) DEFAULT 'user',
    status TINYINT DEFAULT 1,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT DEFAULT 0
);
```

### 9.2 profile 技术画像主表

```sql
CREATE TABLE profile (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    title VARCHAR(128) NOT NULL,
    summary TEXT,
    current_stage VARCHAR(128),
    main_goal TEXT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT DEFAULT 0
);
```

### 9.3 skill_module 技术模块表

```sql
CREATE TABLE skill_module (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    profile_id BIGINT NOT NULL,
    module_name VARCHAR(64) NOT NULL,
    description TEXT,
    sort_order INT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT DEFAULT 0
);
```

### 9.4 skill_item 技能项表

```sql
CREATE TABLE skill_item (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    module_id BIGINT NOT NULL,
    skill_name VARCHAR(64) NOT NULL,
    score INT DEFAULT 0,
    description TEXT,
    evidence TEXT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT DEFAULT 0
);
```

### 9.5 learning_record 学习记录表

```sql
CREATE TABLE learning_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    title VARCHAR(128) NOT NULL,
    record_type VARCHAR(64) NOT NULL,
    content TEXT,
    summary TEXT,
    record_date DATE,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT DEFAULT 0
);
```

### 9.6 ai_call_log AI 调用日志表

```sql
CREATE TABLE ai_call_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    model_name VARCHAR(64),
    prompt_type VARCHAR(64),
    prompt_content TEXT,
    response_content TEXT,
    status VARCHAR(32),
    error_message TEXT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 10. 接口设计示例

### 10.1 用户接口

```text
POST   /api/user/register      用户注册
POST   /api/user/login         用户登录
POST   /api/user/logout        用户登出
GET    /api/user/current       查询当前用户
PUT    /api/user/profile       修改用户信息
GET    /api/user/page          分页查询用户
```

### 10.2 技术画像接口

```text
POST   /api/profile            创建画像
GET    /api/profile/current    查询当前用户画像
PUT    /api/profile/{id}       更新画像
DELETE /api/profile/{id}       删除画像
GET    /api/profile/history    查询画像历史版本
```

### 10.3 技能模块接口

```text
POST   /api/skill/module       创建技能模块
GET    /api/skill/module/list  查询技能模块
PUT    /api/skill/module/{id}  更新技能模块
DELETE /api/skill/module/{id}  删除技能模块
```

### 10.4 学习记录接口

```text
POST   /api/record             创建学习记录
GET    /api/record/page        分页查询学习记录
GET    /api/record/{id}        查询学习记录详情
PUT    /api/record/{id}        更新学习记录
DELETE /api/record/{id}        删除学习记录
```

### 10.5 AI 分析接口

```text
POST   /api/ai/analyze/profile     AI 分析个人画像
POST   /api/ai/analyze/resume      AI 分析简历
POST   /api/ai/plan/stage          AI 生成阶段任务计划
GET    /api/ai/history             查询 AI 分析历史
```

---

## 11. 每个阶段的学习重点与面试价值

| 阶段 | 学习重点 | 面试价值 |
|---|---|---|
| 阶段 0 | Spring Boot 基础、Maven、Git | 能证明会创建并运行后端项目 |
| 阶段 1 | CRUD、分层结构、MyBatis-Plus | Java 后端基础核心 |
| 阶段 2 | 登录鉴权、token、拦截器 | 几乎所有后端项目都会问 |
| 阶段 3 | 业务建模、表设计、画像管理 | 项目个性化亮点 |
| 阶段 4 | 条件查询、分页、标签系统 | 复杂业务查询能力 |
| 阶段 5 | 科研实验记录、指标管理 | 与个人科研经历结合 |
| 阶段 6 | 大模型 API、Prompt、调用日志 | AI 应用能力 |
| 阶段 7 | Redis、缓存、限流 | 后端进阶能力 |
| 阶段 8 | Agent 工作流、任务规划 | AI Agent 雏形亮点 |

---

## 12. AI 辅助开发原则

### 12.1 不让 AI 一次性生成整个项目

错误方式：

```text
帮我做一个完整的 AI 学习档案平台。
```

正确方式：

```text
请只帮我完成用户注册接口，要求使用 Spring Boot + MyBatis-Plus，并解释 Controller、Service、Mapper、Entity 分别做什么。
```

---

### 12.2 每次只让 AI 完成一个明确任务

推荐 Prompt：

```text
你现在是我的 Java 后端代码助教。

当前项目：AI Learning Profile Platform
当前阶段：用户中心基础版
当前任务：实现用户注册接口

要求：
1. 不要生成无关功能
2. 先说明需要创建哪些文件
3. 再给出代码
4. 解释每个类的作用
5. 最后给出 Apifox / Postman 测试方式
```

---

### 12.3 AI 修改代码后必须记录

每次使用 Claude Code / Codex 修改代码后，需要记录：

1. 修改了哪些文件
2. 每个文件改了什么
3. 为什么这样改
4. 如何验证修改有效
5. 是否引入风险
6. 是否已经测试通过

建议记录到：

```text
docs/AI协作记录.md
```

---

## 13. README 应包含的内容

项目 README 建议包含：

```text
1. 项目介绍
2. 项目背景
3. 技术栈
4. 功能模块
5. 项目架构图
6. 数据库设计
7. 接口文档
8. 本地启动方式
9. 阶段开发记录
10. 项目亮点
11. 后续规划
```

---

## 14. 简历表达方向

当项目做到阶段 6 或阶段 7 后，可以考虑写入简历。

### 简历项目名称

AI 学习档案与简历分析平台

### 简历项目描述示例

基于 Spring Boot + MyBatis-Plus + Redis + 大模型 API 的 AI 学习档案管理平台，支持用户维护个人技术画像、学习记录、刷题记录和科研实验记录，并通过大模型生成阶段学习建议和简历优化建议。项目实现了用户登录鉴权、统一异常处理、缓存优化、AI 调用日志记录和阶段任务规划等功能。

### 可写技术点

- 使用 Spring Boot 搭建后端服务，采用 Controller / Service / Mapper 分层架构。
- 使用 MyBatis-Plus 实现用户、画像、学习记录等模块的 CRUD 和分页查询。
- 使用 JWT / Sa-Token 实现登录鉴权和接口访问控制。
- 使用 Redis 缓存登录态、AI 分析结果和热点用户画像。
- 封装大模型 API 调用模块，实现个人画像分析、简历分析和阶段任务规划。
- 设计 AI 调用日志表，记录 Prompt、模型响应、调用状态和异常信息，便于后续追踪和优化。
- 后续扩展简单 Agent 工作流，根据用户画像和学习记录自动生成下一阶段任务。

---

## 15. 项目亮点设计

### 15.1 真实需求驱动

项目来自个人学习、科研和求职的真实需求，不是普通模板项目。

### 15.2 AI 与 Java 后端结合

不仅是调用模型 API，而是把用户画像、学习记录、实验记录和 AI 分析结合起来。

### 15.3 可持续迭代

项目可以从简单 CRUD 起步，逐步扩展为长期个人学习系统。

### 15.4 可解释的 Agent 雏形

Agent 不是黑盒自动执行，而是基于用户画像、记录和任务看板生成阶段建议，便于追踪和复盘。

---

## 16. 当前最小可执行任务

当前不要先做完整大项目，第一步只做：

```text
创建 ai-learning-profile-backend 项目，实现 /hello 接口，并上传 GitHub。
```

### 任务清单

- [ ] 使用 Spring Initializr 创建 Spring Boot 项目
- [ ] 添加 Spring Web 依赖
- [ ] 创建 HelloController
- [ ] 实现 `/hello` 接口
- [ ] 本地启动项目
- [ ] 使用浏览器或 Apifox 测试接口
- [ ] 初始化 Git 仓库
- [ ] 上传 GitHub
- [ ] 编写 README

### 验收标准

- [ ] `localhost:8080/hello` 能返回正常结果
- [ ] GitHub 上能看到完整项目
- [ ] README 中写清楚项目介绍和启动方式
- [ ] 自己能解释 Spring Boot 项目目录结构

---

## 17. 后续版本规划

### v0.1

- Spring Boot 项目初始化
- `/hello` 接口
- GitHub 仓库
- README

### v0.2

- 用户表
- 用户注册
- 用户登录
- 用户 CRUD

### v0.3

- 统一返回结果
- 全局异常处理
- 参数校验
- 分页查询

### v0.4

- 登录鉴权
- token 校验
- 密码加密

### v0.5

- 个人技术画像管理
- 技能模块管理
- 阶段目标管理

### v0.6

- 学习记录管理
- LeetCode 刷题记录
- 标签系统

### v0.7

- 科研实验记录
- AI 协作记录

### v0.8

- AI 模型 API 调用
- AI 分析画像
- AI 生成阶段任务建议

### v0.9

- Redis 缓存
- 接口限流
- AI 分析结果缓存

### v1.0

- 简单 Agent 工作流
- 任务看板生成
- 简历项目整理
- 部署与文档完善

---

## 18. 学习策略总结

本项目的学习策略是：

```text
官方 Guide 入门
↓
项目驱动学习
↓
pdai 补知识体系
↓
AI 辅助写代码和解释代码
↓
每个阶段形成可验证产出
↓
最终沉淀成可写进简历的项目
```

核心原则：

> 不追求一开始做大而全，而是每个阶段都做出一个能运行、能解释、能复盘、能继续扩展的版本。

---

## 19. 给 AI 的项目启动 Prompt

以后让 ChatGPT / Claude Code / Codex 辅助本项目时，可以先提供如下 Prompt：

```text
你现在是我的 Java 后端项目助教。

项目名称：AI Learning Profile Platform
项目定位：一个面向学生和技术学习者的 AI 学习档案与简历分析平台。

我的当前水平：
- Java 基础较好，但 Spring Boot、MySQL、MyBatis-Plus、Redis 仍处于初学阶段。
- 目标是通过这个项目学习 Java 后端，并最终形成可写入简历的项目。

项目开发原则：
1. 不要一次性生成大项目。
2. 每次只完成一个明确功能。
3. 代码要适合初学者理解。
4. 每次输出都要解释项目结构和关键代码。
5. 每个阶段都要给出验收标准。
6. 不要过度设计，不要一开始使用微服务和复杂架构。

当前任务：
【在这里填写本次任务】
```

---

## 20. 当前行动建议

下一步立即执行：

1. 新建 GitHub 仓库：`ai-learning-profile-backend`
2. 用 Spring Initializr 创建 Spring Boot 项目
3. 只添加 Spring Web 依赖
4. 完成 `/hello` 接口
5. 上传 GitHub
6. 把过程记录到 Obsidian 的 Java 学习笔记中

完成这个最小闭环后，再进入用户中心模块。
