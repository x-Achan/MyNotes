
SQL重建的代价太大了。所以如果只是用单表实现关注，只需要简单的像点赞一样加redis，然后计数重建就行，原项目之所以加上outbox + CDC，就是为了双表设计引出来的，为了不适用SQL重建，双表设计的初衷就是为了未来的分库分表
```
双表设计 → 需要同步 → SQL 重建太贵 → 所以引入 Outbox + CDC
```

**Outbox 是「跨系统可靠投递」的通用基础设施**


----



关注成功需要两件事同时发生

① 数据库写入关系（following 表）
② 让下游知道发生了什么（让 follower 表、缓存、计数更新）


**而这两件事跨了两个系统（MySQL + Kafka），没法用本地事务保证**

失败案例：
```
❌ 先写库、再发 Kafka
   INSERT following 成功 → kafka.send 失败
   → 关系存在了，但粉丝表/缓存/计数永远不知道 → 永久不一致

❌ 先发 Kafka、再写库
   kafka.send 成功 → INSERT following 失败（比如唯一键、DB 挂了）
   → 消费端会去插一条"根本不存在"的粉丝关系 → 数据错乱
```

所以要保证两个系统的原子性，引入OutBox，把发消息变成写本地表
```
① 同一个本地事务里写两张表：
     BEGIN
       INSERT following (...)
       INSERT outbox (id, aggregate_type, aggregate_id, type, payload)
     COMMIT
   → 事务保证"要么都有，要么都没有" ✅ 原子性由数据库给

② 有独立的一环去"搬运" outbox 表 → MQ
   （Canal 订阅 binlog / 定时轮询 / Debezium）

③ 消费端处理，保证幂等
```

OutBox表结构

```java
CREATE TABLE outbox (
  id             BIGINT UNSIGNED NOT NULL,
  aggregate_type VARCHAR(64) NOT NULL,   -- 'following'
  aggregate_id   BIGINT UNSIGNED NULL,   -- 关系行 id
  type           VARCHAR(64) NOT NULL,   -- 'FollowCreated' / 'FollowCanceled'
  payload        JSON NOT NULL,          -- ★ 序列化好的事件体
  created_at     TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY ix_outbox_agg (aggregate_type, aggregate_id),
  KEY ix_outbox_ct (created_at)
);
```

一张 outbox 表能承载**所有聚合类型**的事件（`aggregate_type` 区分）

可以轮询OutBox表，也可以 CDC订阅binlog

CDC 的关键优势：它是"事后订阅"，不是"业务代码里去发消息" —— 所以无论谁往 outbox 表里写（甚至 DBA 手工写），都会被捕获。业务代码只管写表


## 为什么点赞不用 outbox？

对点赞来说，Redis 原子更新加重建对账通常够用。

对关注来说，Outbox + Kafka 的价值主要在于可靠地同步两个用户的列表和计数；如果只看关注计数本身，确实可以不使用 Kafka

```
Kafka 负责及时传播
对账负责最终修复
```