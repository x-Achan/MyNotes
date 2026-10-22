>Canal = 一个读取和解析 MySQL Binlog 的独立服务
### 0. Canal 的工作链路

```
业务事务
   ↓
写入 following 和 outbox
   ↓
MySQL 提交事务
   ↓
MySQL 产生 Binlog
   ↓
Canal 伪装成 MySQL 从库订阅 Binlog
   ↓
Canal 解析 Binlog
   ↓
Canal Kafka Adapter 发布到 Kafka
   ↓
你的 Spring Boot 消费者处理消息
   ↓
更新 Redis 计数
```

### 1. Canal 如何订阅 Binlog

Canal Server 会连接 MySQL，并使用一个具有复制权限的账号登录。

它不会定时查询数据库，而是按照 MySQL 主从复制协议，伪装成一个 MySQL 从库：

1. 向 MySQL 注册一个唯一的 `server-id`
2. 请求从某个 Binlog 文件和位置开始同步
3. MySQL 持续把 Binlog 事件发送给 Canal
4. Canal 解析出数据库、表、操作类型和行数据
5. Canal 保存消费位置，重启后可以继续消费

因此它本质上是：

```
Canal = 一个读取和解析 MySQL Binlog 的独立服务
```

MySQL 通常需要开启：

```
server-id=1001
log-bin=mysql-bin
binlog_format=ROW
binlog_row_image=FULL
```

并创建复制账号，例如：

```
CREATE USER 'canal'@'%' IDENTIFIED BY '密码';

GRANT SELECT, REPLICATION SLAVE, REPLICATION CLIENT
ON *.*
TO 'canal'@'%';

FLUSH PRIVILEGES;
```

### 2. Canal 如何把消息发给 Kafka

Canal 本身主要负责读取和解析 Binlog，Kafka 投递通常由 Canal Adapter 完成。

Canal Adapter 会连接 Canal Server，接收 Canal 解析出来的事件，然后使用 Kafka Producer 发送到指定 Topic。

典型的外部配置类似下面这样：

```
canal.conf:
  mode: kafka
  canalServerHost: canal-server
  canalServerPort: 11111

  canalAdapters:
    - instance: example
      groups:
        - groupId: relation-group
          outerAdapters:
            - key: kafka
              properties:
                bootstrap.servers: kafka:9092
                topic: canal-outbox
```

不同 Canal 版本的配置文件结构可能略有差异，但核心配置基本都是：

- Canal Server 地址
- Canal instance 名称
- Kafka 地址
- Kafka Topic
- Kafka 分区策略
- 消费组或 Adapter 分组

Canal Server 自己还需要配置 MySQL 连接信息，例如：

```
canal.instance.master.address=mysql:3306
canal.instance.dbUsername=canal
canal.instance.dbPassword=密码
canal.instance.filter.regex=zhiguang\\.outbox
```

这里的 `filter.regex` 可以只监听 `outbox` 表，避免把整个数据库的 Binlog 都发送出去。

