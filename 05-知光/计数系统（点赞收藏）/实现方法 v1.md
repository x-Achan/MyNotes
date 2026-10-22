
# 1. 陈述
 
 >点赞用 MySQL 明细表当真相源 + Redis 当计数派生视图，写路径用 Lua 原子增量避免"key 缺失被当成 0"， 读路径 懒加载 + 空值缓存 + 单飞锁，缓存过期用 TTL 抖动防雪崩； Redis 会漂移，所以后台跑 定时对账（anti-entropy），修正时用 差值 INCRBY 而不是 SET 覆盖； 对账用 Redisson 分布式锁保证多实例只有一个在跑
 
# 2. 数据库设计

点赞表结构（like_record）

```sql
-- 点赞明细表：靠唯一键判重（这就是"真相源"）
CREATE TABLE IF NOT EXISTS like_record (
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id    BIGINT UNSIGNED NOT NULL,
  post_id    BIGINT UNSIGNED NOT NULL,
  type       VARCHAR(16) NOT NULL COMMENT 'like / fav',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_user_post_type (user_id, post_id, type),   -- ★ 幂等的关键
  KEY ix_post_type (post_id, type)                          -- 按帖子查
  KEY ix_user_type_created (user_id, type, created_at) -- 查询我的点赞列表
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```


like_recorad表中，存在唯一键（保证幂等性的关键）
```sql
UNIQUE KEY uk_user_post_type (user_id, post_id, type),
```

插入一条点赞记录的SQL，单独 INSERT
```xml
<insert id="insert">  
    INSERT INTO like_record (user_id, post_id, type)    
    VALUES (#{userId}, #{postId}, #{type})
</insert>
```

>幂等实现：当插入重复的 uk 时，会抛出 DuplicateKeyException → INSERT / UPDATE 时"唯一键冲突"

- INSERT → 要插的数据"唯一键已存在" → 冲突，DuplicateKeyException
- UPDATE → 改后的值"和其他行冲突" → 冲突，DuplicateKeyException

收到同一个用户对同一个帖子的点赞，insertRecord 执行会发生唯一键冲突，捕获异常，返回false
```java
private boolean insertRecord(CounterType type, long userId, long postId) {  
    try {  
        likeRecordMapper.insert(userId, postId, type.value());  
        return true;  
    } catch (DuplicateKeyException e) {  
        return false;  
    }  
}
```


# 3. 获取计数（查询点赞数/收藏数）

S1：（首次检查）先从Redis中查询，如果命中直接返回
```java
String key = CounterKeys.knowpost(postId,type);  
// 1.第一次检查  
String count = redis.opsForValue().get(key);  
if(count != null) {  
    return Long.parseLong(count);  
}
```
S2：Redis未命中，需要从数据库中重建
缓存击穿：重建操作需要读取数据库，并且计算count(\*)，如果多个请求同时查询这篇帖子的点赞数，会造成缓存击穿
解决方法：single-flight 单飞锁，多个请求过来时需要抢锁，只有一个请求可以抢到锁，执行重建操作，将数据库信息写到Redis中

S2.1：ConcurrentHashMap作为锁容器，每一个Key创建一个锁对象
```java
// 单飞锁容器，以缓存key为粒度，保证通过一个key在同一时刻只有一个线程回源  
private final ConcurrentHashMap<String,Object> flightLocks = new ConcurrentHashMap<>();
Object lock = flightLocks.computeIfAbsent(key,k -> new Object());
```

S2.2：（双重检查）抢到锁的线程，重建之前，再查一次Redis

S3：重建操作 rebuild，将真相源写入Redis
S3.1：从数据库查值（当前帖子有多少赞）
S3.2：处理缓存穿透 + 缓存雪崩
缓存穿透：对于没有查到的值，计数为0，也要写入Redis中
缓存雪崩：设置抖动TTL
```java
redis.opsForValue().set(  
        CounterKeys.knowpost(postId, type),  
        String.valueOf(actual),  
        Duration.ofSeconds(ttl));
```
S3.3：Redis中还有一张索引表，用于定时抽样重建，将当前Key写入索引表中
```java
// 登记索引，供对账抽样时使用  
redis.opsForSet().add(CounterKeys.INDEX,CounterKeys.indexEntry(postId,type));
```

S4：完成重建后要释放锁，在 finally中释放
```java
flightLocks.remove(key);
```


### 附加：批量查计数，用于Feed返回多个帖子的赞计数

getcounts
核心：MGET 批量获取
```java
List<String> values = redis.opsForValue().multiGet(keys);
```
缺失的放入 missing ，命中的放入result
对missing要进行重建
重建通过 SETNX互斥

获取锁成功，批量查Mysql
```java
likeRecordMapper.countByPostIdsAndType
```
sql语句，使用动态sql
```xml
<!-- 批量计数（批量懒重建用）：一次 GROUP BY，不是 N 次查询 -->  
<select id="countByPostIdsAndType" resultType="PostCountRow">  
    SELECT post_id AS postId, COUNT(*) AS cnt    
    FROM like_record    
    WHERE type = #{type}    
    AND post_id IN    
    <foreach collection="postIds" item="pid" open="(" separator="," close=")">  
        #{pid}    
    </foreach>  
    GROUP BY post_id
</select>
```
查询结果重建到Redis中，再添加到Result中
返回result

# 4. 增加计数（用户给帖子点赞/收藏）

S1：前置校验，查询帖子是否存在
S2：点赞/取消赞
就是对like_record记录插入/删除，操作唯一真相源（写数据库）
外部用 changed 接收是否成功插入
```java
// 是否修改成功，保证幂等性，  
boolean changed = on  
        ? insertRecord(type,userId,postId)  
        : deleteRecord(type,userId,postId);
```

on标记了用户的意图（最终效果）
- 如果是 true 就是插入一条点赞记录
- 如果是 false 就是删除一条点赞记录

S2.1：changed = false 时 ： 说明数据源没有发生修改，toggle是重复操作，不用修改 like_record 表，直接返回redis中的值，相当于没有做任何操作

S2.2：changed = true 时 ： 说明数据源发生了修改（添加了一条点赞记录），在redis中，要将帖子的点赞数+1，使用Lua脚本完成自增INCR（写Redis），如果Redis缺失，就执行重建rebuild
==（保证双写一致性）==

```java
Long after = redis.execute(INCR_IF_EXISTS, List.of(key), String.valueOf(delta));  
// Redis缺失或者发生飘逸为复数，从真相源重建  
if(after == null || after < 0){  
    // 写路径的重建是罕见操作，可以接受各自重建  
    return rebuild(postId,type);  
}
```

注意，此处重建不需要单飞锁，因为写操作的重建是罕见操作，可以接受各自重建


# 5. 定时实现双写一致性

使用注解@Scheduled，实现一个方法的定时执行

```java
@Scheduled(fixedDelayString = "${counter.reconcile.interval-ms:300000}")
```

在Redis中，用一张索引表，记录Redis中存在的帖子的点赞记录key，从而定期的抽样，对抽到的样本key进行值更新，保证Redis存到的就是最新值
key
```java
key:"cnt:index"
```
value采用Set，保存Redis中存在的记录的key值
每一个value都是下面的形式
```java
postId:type
```

如果是分布式场景，索引表是多个服务器端共享的，所以定时重建操作只需要一个服务器端实现就行，所以需要分布式锁Redisson
多个服务器端抢锁
```java
RLock lock = redisson.getLock(LOCK_KEY);
// 抢锁：对账是周期性任务，抢不到就跳过本轮，下一轮会补 → 不需要排队  
boolean isLock = lock.tryLock(0, TimeUnit.SECONDS);
```
如果抢到锁，则查Redis中的索引表,，查Set（抽样）
```java
List<String> samples = redis.opsForSet().randomMembers(CounterKeys.INDEX, SAMPLE_SIZE);
```

对每一个样本进行单独处理
```java
for (String sample : samples) {
```
==（关键）计算数据库真相源的值和Redis保存的值的差==
```java
long redisValue = Long.parseLong(value);  
long truthValue = likeRecordMapper.countByPostAndType(postId, type.value());
long delta = truthValue - redisValue;
```
==（关键）对Redis的值更新，使用自增差值，而不是覆盖set，避免并发问题==
```java
redis.opsForValue().increment(key,delta);
```

# 6. 总结

用Redis存储每个帖子的点赞数，key是
```
cnt:knowpost:{postId}:like
```
value存储点赞数

读：当用户getCount时，Redis未命中，需要解决缓存击穿/穿透问题，用单飞锁解决缓存击穿，多个请求线程，只有一个线程实现重建，将数据库值写回Redis中，同时设置抖动TTL解决缓存雪崩的问题，

写：当用户写数据时，首先写入数据库真相源，此处用uk保证幂等，在redis中自增INCR，redis中可能不存在，用lua脚本实现拆查询和自增的原子性，如果查询不存在，需要重建

对账自愈：维护Redis中数据的时效性，用一张索引表记录所有key，后端服务器定时对索引表中的数据进行重建，重建时采用自增差值，而不是直接覆盖，避免并发问题，分布式场景下，只需要一台服务器实现重建即可，使用Redisson分布式锁
```java
反例（SET truth）：Redis=5、truth=6 → SET 6
   若期间并发来了一个赞（Redis→6、truth→7），那个赞被覆盖丢失 ❌

正解（INCRBY truth-current）：delta=+1
   期间并发那个赞让 Redis 变 6、truth 变 7 → INCRBY +1 → Redis=7 = truth ✅

本质：SET 是【绝对操作】覆盖期间一切变化；
      INCRBY 是【相对操作】期间的并发增量自然叠加。
```


# 7. 问题

点赞是一个高频写的功能，每次点击，都要写入数据库，一个帖子爆火，点赞请求太多，数据库压力过大


# 8.AI总结

**数据模型**

- `like_record` 是**真相源**（谁赞了谁），`uk_user_post_type` 唯一键既是幂等保障，也是并发守卫
- Redis 的 `cnt:knowpost:{id}:{like|fav}` 是**派生视图**——和 V1 的 `like_count` 列是同一个东西（都是"物化缓存"），只是位置从 MySQL 换到了 Redis
- **核心认知：事实必须持久化，派生可以随时重算**。这决定了后面所有设计

**写路径（3 步）**

1. 校验帖子存在
2. 写明细（真相源）—— 裸 INSERT + 捕 `DuplicateKeyException` 实现幂等
3. Lua 原子更新计数：`EXISTS + INCRBY`；返回 `-1` 说明 key 缺失 → 从真相源重建，**且不再自增**（因为明细已写好，重建值已含本次操作）

**读路径（3 层防护）**

- 命中即返回（`"0"` 也算命中 → 防穿透）
- 未命中 → single-flight 单飞锁（同 key 并发只让一个线程回源 → 防击穿）
- 回填写入带**随机抖动的 TTL**（防雪崩）

**一致性（对账 + 自愈）**

- 用 `cnt:index` Set 记录已缓存的计数 key，**随机抽样**（对比参考实现的 `KEYS` 全库扫描，生产禁用）
- 比对真相源与 Redis，偏差用 **差值 `INCRBY(truth-current)`** 修正
- **为什么不能 `SET`**：对账期间的并发写入会被覆盖丢失；`INCRBY` 是相对操作，并发增量自然叠加
- 偏差率作为 SLI 监控

**锁（分场景）**

- 缓存回源用**单机锁**（只保护一次轻查询，上分布式锁反而更亏）
- 定时对账用 **Redisson 分布式锁**（重任务必须去重；`tryLock(0)` 不等待 + `isHeldByCurrentThread()` 安全释放 + 看门狗续期）






## 写法 A：技术深度导向（推荐投大厂后端实习）

> **点赞/收藏计数系统（Java / Redis / MySQL / Redisson）**
> 
> - 以 **MySQL 明细表为真相源 + Redis 为计数派生视图**，写路径用 **Lua 脚本 `EXISTS+INCRBY`** 保证原子性与"缺失自愈"；读路径实现**懒加载 + 空值缓存 + single-flight + TTL 抖动**，系统性解决缓存穿透/击穿/雪崩三件套。
> - 针对缓存副本漂移，实现**定时对账 + 自愈（anti-entropy）**：以索引集合随机抽样比对真相源，采用**差值 `INCRBY` 而非覆盖 `SET`** 修正，保证对账期间的并发写入不被覆盖，并用单元测试锁定该设计决策。
> - 多实例下用 **Redisson 分布式锁**保证对账单实例执行；按"被保护操作的成本"分场景选锁——缓存回源用单机锁、重任务用分布式锁。

## 写法 B：量化 + 工程方法导向（更能体现能力，**推荐**）

> **点赞/收藏计数系统（Java / Redis / MySQL / Redisson）**
> 
> - 设计并实现**三阶段演进**的计数方案：MySQL 行计数 → Redis 派生计数 + Lua 原子更新 → **对账自愈**；补齐缓存穿透/击穿/雪崩三层防护（空值缓存 / single-flight / TTL 抖动）。
> - 自建 **200 并发压测量化验证**，通过 `Innodb_row_lock_waits` 等指标发现：将计数迁到 Redis 后耗时**并未改善（747ms → 785ms）**，据此定位到**真正的瓶颈是明细表唯一索引上的 INSERT gap 锁竞争**，纠正了优化方向并明确后续走**写聚合 / 异步落库**——**建立了"测量驱动优化"而非"凭直觉优化"的方法论**。
> - 实现**反熵（anti-entropy）对账机制**：索引集合随机抽样、**差值修正而非覆盖**避免并发丢失；并用 Redisson 分布式锁解决多实例重复对账。

## 写法 C：一句话版（简历空间紧张时）

> 基于 **MySQL 真相源 + Redis 派生视图**实现点赞计数系统，覆盖缓存穿透/击穿/雪崩三层防护与 **anti-entropy 对账自愈**；通过 200 并发压测定位出真正瓶颈是**明细表唯一索引 INSERT 的 gap 锁竞争**（而非计数更新），形成测量驱动的优化闭环。








