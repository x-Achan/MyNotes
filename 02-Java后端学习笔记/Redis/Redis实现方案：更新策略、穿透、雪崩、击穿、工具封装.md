# 一、认识缓存

缓存是数据交换的缓冲区（Cache），是存储数据的临时地方，一般读写性能较高
- 降低后端负载
- 提高读写效率，降低响应时间
- 需要实现数据一致性

# 二、 缓存更新策略

1. 三种更新策略
- 内存淘汰：Redis的内存淘汰机制，默认存在
- 超时剔除：给数据添加TTL时间，到期后自动删除缓存
- 主动更新：编写业务逻辑，在修改数据库的同时，更新缓存，Cache Aside模式

>低一致性需求：使用内存淘汰机制
   高一致性需求：主动更新，并以超时剔除作为兜底方案

2. 最佳实践方案

读操作：
- 缓存命中直接返回
- 未命中则查询数据库，并写入缓存，设定超时时间
写操作：
- **==先写数据库 ，再删除缓存(Cache Aside 思路)==**
- 确保数据库于缓存操作的原子性

3. 更新操作案例

- 流程
>PUT请求，更新数据库信息
>核心：**先update数据库，再删除Redis缓存**

- 代码
```java
@Override  
public Result update(Shop shop){  
  
    Long id = shop.getId();  
    
    if(id == null){  
        return Result.fail("id不能为空");  
    }  
  
    // 1. 先操作数据库  
    updateById(shop);  
    // 2. 再删除缓存  
    stringRedisTemplate.delete(CACHE_SHOP_KEY + id);  
  
    return Result.ok();  
}
```

4. 根据id查询案例

- 流程
>优先查询 Redis，缓存命中，就直接返回；
>缓存未命中，查询数据库，并把数据库查询结果写入 Redis
```java
public Result queryById(Long id) {  
    String key = CACHE_SHOP_KEY + id;  
    // 1.从 redis中获取信息  
    String shopJson = stringRedisTemplate.opsForValue().get(key);  
  
    // 2.redis中存在，获取成功，返回信息  
    if(StrUtil.isNotBlank(shopJson)){  
        Shop shop = JSONUtil.toBean(shopJson,Shop.class);  
        return Result.ok(shop);  
    }  
    // 3.redis中不存在，查询数据库  
    Shop shop = getById(id);  
    // 4.数据库中不存在，返回false  
    if(shop == null){  
        return Result.fail("店铺不存在");  
    }  
    // 5.数据库中存在，将信息添加到 redis中，返回信息给前端  
    stringRedisTemplate.opsForValue().set(key,JSONUtil.toJsonStr(shop));  
    // 6. 返回信息  
    return Result.ok(shop);  
}
```

# 三、缓存穿透

1. 什么是缓存穿透？
>客户端请求一个在缓存和数据库中都不存在的资源，缓存永远不会命中，这些请求都会打到数据库，给数据库带来巨大的压力

2. 解决方案

2.1 布隆过滤器
- 内存占用少，没有多余Key
- 实现复杂
- 存在误判可能 

2.2 缓存空对象（不是null）
- 实现简单，维护方便
- 额外的内存消耗
- 可能造成短期的不一致（设置空对象的TTL）

3. 缓存空对象实践案例

在原有的根据id查询案例基础上,添加对缓存穿透的解决方案
- Redis命中，判断是否为空对象，是空对象则返回给前端信息，不再查找数据库
```java
// 解决缓存穿透：判断 shopJson 是否为为空对象  
if(shopJson != null){  
    return Result.fail("店铺信息不存在");  
}
```
- 数据库未命中，将空对象写入Redis中，TTL比一般的数据设置的更短
```java
// 4.数据库中不存在，返回false  
if(shop == null){  
    // 解决缓存穿透：将空对象写入Redis  
    stringRedisTemplate.opsForValue().set(key,"",CACHE_NULL_TTL,TimeUnit.MINUTES);  
    return Result.fail("店铺不存在");  
}
```

>null 不是 ""，null代表缓存没有数据，需要去数据库中查，""代表为空对象

# 四、缓存击穿

1. 什么是缓存击穿？
>也叫热点Key问题，就是一个被高并发并且缓存重建业务较复杂的key突然失效了，无数请求会在瞬间给数据库带来巨大压力

2. 解决方案
- 互斥锁
	- 没有额外的内存消耗
	- 保证一致性
	- 实现简单
	- 线程需要等待，性能受影响
	- 可能有死锁风险
- 逻辑过期
	- 线程无需等待，性能较好
	- 不保证一致性
	- 有额外内存消耗
	- 实现复杂

3. 互斥锁解决缓存击穿案例
3.1 过程
请求查询缓存（热点Key），缓存未命中，需要查询数据库，在查询数据库之前，需要获取互斥锁，只有一个请求线程可以获取锁，从而进入数据库进行查询和缓存重建，其他请求线程获取锁失败，就会线程等待，然后重新获取查询缓存

>热点 Key 失效后，只允许一个线程查询数据库并重建缓存，其他线程等待后重试，避免大量请求同时打到数据库

3.2 通过 SETNX 实现互斥锁
代码：
```java
public boolean tryLock(String key){
    Boolean flag = stringRedisTemplate.opsForValue()
            .setIfAbsent(key, "1", 10, TimeUnit.SECONDS);
    return BooleanUtil.isTrue(flag);
}
```
锁必须设置 TTL，避免线程异常退出后产生永久死锁

>flag是有可能为null，可能出现空指针异常，所以使用BooleanUtil.isTrue(flag)做拆箱

```java
public void unlock(String key){  
    stringRedisTemplate.delete(key);  
}
```

核心 API：
```java
setIfAbsent()
```
对应 Redis：
```bash
SETNX
```
含义：
> **只有 Key 不存在时才能写入成功**


3.3 核心代码

查询Redis未命中，尝试获取锁，获取失败则进入休眠，休眠结束重新查询Redis
```java
// 3.redis中不存在，尝试获取锁  
boolean isLock = tryLock(lockKey);  
// 3.1 获取失败,则进入休眠,休眠结束回头重新执行  
if (!isLock) {  
    Thread.sleep(50);  
    return queryWithMutex(id);
```

>注意：休眠结束不是继续接着执行当前函数，然后重新调用当前函数

如果没有获得锁，就需要线程休眠
```java
try {
    ...
    Thread.sleep(50);
    ...
} catch (InterruptedException e) {
    throw new RuntimeException(e);
} finally {
    unlock(lockKey);
}
```

>Thread.sleep需要用try-catch包围，查询数据库和写缓存应放在 `try` 中，释放锁放在 `finally` 中

finally确保拿到锁的线程，保证无论业务成功还是异常，都一定会释放锁，避免死锁，**只有真正获得锁的线程才能执行 `unlock()`，获取锁失败的线程不能进入释放锁的 finally**
```
正常执行完/中途return/发生异常
都会 → finally执行
```

3.4 完整代码实现

```java
// 缓存击穿(互斥锁)  
public Shop queryWithMutex(Long id){  
  
    String key = CACHE_SHOP_KEY + id;  
    // 1.从 redis中获取信息  
    String shopJson = stringRedisTemplate.opsForValue().get(key);  
  
    // 2.redis中存在，获取成功，返回信息  
    if (StrUtil.isNotBlank(shopJson)) {  
        Shop shop = JSONUtil.toBean(shopJson, Shop.class);  
        return shop;  
    }  
  
    // 解决缓存穿透：判断 shopJson 是否为为空对象  
    if (shopJson != null) {  
        return null;  
    }  
  
    String lockKey = "lock:shop" + id;  
    Shop shop = null;  
  
    try {  
        // 3.redis中不存在，尝试获取锁  
        boolean isLock = tryLock(lockKey);  
        // 3.1 获取失败,则进入休眠,休眠结束回头重新执行  
        if (!isLock) {  
            Thread.sleep(50);  
            return queryWithMutex(id);  
        }  
    } catch (InterruptedException e) {  
        throw new RuntimeException(e);  
    }  
  
    try {  
        // 3.2 获取成功，查询数据库  
        shop = getById(id);  
        // 4.数据库中不存在，返回false  
        if (shop == null) {  
            // 解决缓存穿透：将空对象写入Redis  
            stringRedisTemplate.opsForValue()  
                    .set(key, "", CACHE_NULL_TTL, TimeUnit.MINUTES);  
            return null;  
        }  
        // 5.数据库中存在，将信息添加到 redis中，返回信息给前端  
        stringRedisTemplate.opsForValue()  
                .set(key, JSONUtil.toJsonStr(shop), CACHE_SHOP_TTL, TimeUnit.MINUTES);  
    } finally {  
        // 6.释放锁  
        unlock(lockKey);  
    }  
    // 7.返回信息  
    return shop;  
}
```


4. 逻辑过期方式解决缓存击穿问题

4.1 介绍

对每一份数据都加上一个逻辑过期属性expireTime，让过期数据仍然保留在 Redis 中，请求发现数据逻辑过期后，尝试获取锁
- 获取成功则异步重建缓存
- 获取失败说明已有线程正在重建，此时直接返回旧数据，从而避免大量线程等待和数据库瞬时压力

>不依赖 Redis 的物理 TTL 删除热点数据，否则 Redis Key 真过期没了，失去了“返回旧数据”的意义

特点：
- 数据不物理删除：Redis 中保留旧数据，通过 `expireTime` 判断是否逻辑过期。
- 互斥重建：逻辑过期后通过 Redis 锁保证只有一个线程负责缓存重建，避免缓存击穿。
- 异步更新：获取锁的线程把重建任务提交线程池，当前请求和其他请求都直接返回旧数据，实现低延迟和高可用。

>逻辑过期方案通常依赖： **热点数据提前缓存 / 预热到 Redis**，所以完全查不到时，当前代码直接返回，不去访问数据库。

4.2 给每个数据对象添加到期时间

```java
@Data  
public class RedisData {  
    private LocalDateTime expireTime; //到期时间  
    private Object data; //数据信息  
}
```

>在Redis中存储的是不data，而是携带到期时间的RedisData

4.3 查询Redis数据，取出业务数据和逻辑时间

```java
// RedisData
RedisData redisData =
        JSONUtil.toBean(shopJson, RedisData.class);
// 实际数据对象
Shop shop =
        JSONUtil.toBean(
                (JSONObject) redisData.getData(),
                Shop.class
        );
// 到期时间
LocalDateTime expireTime =
        redisData.getExpireTime();
```

4.4 判断是否逻辑过期
如果没有过期，直接返回缓存
```java
if (expireTime.isAfter(LocalDateTime.now())) {
    return shop;
}
```
如果数据过期，抢锁
```java
String lockKey = LOCK_SHOP_KEY + id;
boolean isLock = tryLock(lockKey);
```
4.5 抢锁成功，开启独立线程
线程池实现
```java
private static final ExecutorService CACHE_REBUILD_EXECUTOR = Executors.newFixedThreadPool(10);
```
此时不是当前请求线程进行缓存重建，而是开启独立线程进行缓存重建，当前请求线程还是会返回旧缓存，**即：缓存重建不阻塞当前用户请求**

```java
if(isLock){  
    CACHE_REBUILD_EXECUTOR.submit(() -> {  
        //重建缓存  
        try {  
            saveShop2Redis(id,20L);  
        } catch (Exception e) {  
            throw new RuntimeException(e);  
        } finally {  
            //释放锁  
            unlock(lockKey);  
        }  
    });  
}
```

saveShop2Redis主要实现，查询数据库，封装到期时间，保存到Redis中
```java
public void saveShop2Redis(Long id,Long expireSeconds){  
    // 1.查询店铺数据  
    Shop shop = getById(id);  
    // 2.封装逻辑过期时间  
    RedisData redisData = new RedisData();  
    redisData.setData(shop);  
    redisData.setExpireTime(LocalDateTime.now().plusSeconds(expireSeconds));  
    // 3.写入Redis（不添加TTL）  
    stringRedisTemplate.opsForValue().set(CACHE_SHOP_KEY + id,JSONUtil.toJsonStr(redisData));  
}
```

4.6 抢锁失败，直接返回就缓存
```java
return shop;
```

5. 完整代码
```java
//创建线程池  
private static final ExecutorService CACHE_REBUILD_EXECUTOR = Executors.newFixedThreadPool(10);  
// 缓存击穿（逻辑过期）  
public Shop queryWithLogicExpire(Long id){  
    String key = CACHE_SHOP_KEY + id;  
    // 1.从 redis中获取信息  
    String shopJson = stringRedisTemplate.opsForValue().get(key);  
  
    // 2.redis未命中，直接返回未找到  
    if(StrUtil.isBlank(shopJson)){  
        return null;  
    }  
  
    // 3.命中，将 json 反序列化为对象  
    RedisData redisData = JSONUtil.toBean(shopJson,RedisData.class);  
    Shop shop = JSONUtil.toBean((JSONObject) redisData.getData(),Shop.class);  
    LocalDateTime expireTime = redisData.getExpireTime();  
  
    // 4.判断是否逻辑过期  
    if(expireTime.isAfter(LocalDateTime.now())){  
        // 4.1 未过期，直接返回缓存数据  
        return shop;  
    }  
    // 4.2 过期，尝试获取锁  
    String lockKey = LOCK_SHOP_KEY + id;  
    boolean isLock = tryLock(lockKey);  
  
    // 5.获取锁成功，开启独立线程，实现缓存重建  
    if(isLock){  
        CACHE_REBUILD_EXECUTOR.submit(() -> {  
            //重建缓存  
            try {  
                saveShop2Redis(id,20L);  
            } catch (Exception e) {  
                throw new RuntimeException(e);  
            } finally {  
                //释放锁  
                unlock(lockKey);  
            }  
        });  
    }  
    // 6.获取锁失败，返回缓存数据  
    return shop;  
}  
  
// 缓存重建  
public void saveShop2Redis(Long id,Long expireSeconds){  
    // 1.查询店铺数据  
    Shop shop = getById(id);  
    // 2.封装逻辑过期时间  
    RedisData redisData = new RedisData();  
    redisData.setData(shop);  
    redisData.setExpireTime(LocalDateTime.now().plusSeconds(expireSeconds));  
    // 3.写入Redis（不添加TTL）  
    stringRedisTemplate.opsForValue().set(CACHE_SHOP_KEY + id,JSONUtil.toJsonStr(redisData));  
}
```

# 五、缓存雪崩

>同一时间大量的缓存Key同时失效（TTL到期）或者Redis服务宕机，导致大量请求到达数据库，带来巨大压力

方案：
- 给不同的Key的TTL添加随机值
- 利用Redis集群提高服务的可用性
- 给缓存业务添加降级限流策略
- 给业务添加多级缓存

# 六、缓存工具工具封装

在以上的案例中，都是以商户信息为例子，请求查询Shop对象，返回Shop对象
但是实际应用中，数据类型是不确定的
- 返回值类型
- id类型
>在数据类型不确定的情况下，要利用泛型，由调用者告诉我们真实的类型是什么

牵扯到数据库查询时，需要由调用者告诉我们数据库的查询函数，要传入函数，比如getById()

1. 缓存穿透方案（泛型）
```java
public <R,ID> R queryWithPassThrough(  
        String keyPrefix, ID id, Class<R> type,Function<ID,R> dbFallback,Long time,TimeUnit unit){  
  
    String key = keyPrefix + id;  
    // 1.从 redis中获取信息  
    String json = stringRedisTemplate.opsForValue().get(key);  
  
    // 2.redis中存在，获取成功，返回信息  
    if(StrUtil.isNotBlank(json)){  
        log.info("缓存中");  
        return JSONUtil.toBean(json,type);  
    }  
  
    // 解决缓存穿透：判断 json 是否为为空对象  
    if(json != null){  
        return null;  
    }  
  
    // 3.redis中不存在，查询数据库  
    R r = dbFallback.apply(id);  
    // 4.数据库中不存在，返回false  
    if(r == null){  
        // 解决缓存穿透：将空对象写入Redis  
        this.set(key,"",time,unit);  
        return null;  
    }  
    // 5.数据库中存在，将信息添加到 redis中，返回信息给前端  
    this.set(key,r,time,unit);  
    // 6. 返回信息  
    return r;  
}
```

2. 逻辑过期解决缓存击穿（泛型）
```java
//创建线程池  
private static final ExecutorService CACHE_REBUILD_EXECUTOR = Executors.newFixedThreadPool(10);  
// 缓存击穿（逻辑过期）  
public <R,ID> R queryWithLogicExpire(  
        String keyPrefix,ID id,Class<R> type,Function<ID,R> dbFallback,Long time,TimeUnit unit){  
    String key = keyPrefix + id;  
  
    // 1.从 redis中获取信息  
    String json = stringRedisTemplate.opsForValue().get(key);  
  
    // 2.redis未命中，直接返回未找到  
    if(StrUtil.isBlank(json)){  
        return null;  
    }  
  
    // 3.命中，将 json 反序列化为对象  
    RedisData redisData = JSONUtil.toBean(json,RedisData.class);  
    R r = JSONUtil.toBean((JSONObject) redisData.getData(),type);  
    LocalDateTime expireTime = redisData.getExpireTime();  
  
    // 4.判断是否逻辑过期  
    if(expireTime.isAfter(LocalDateTime.now())){  
        // 4.1 未过期，直接返回缓存数据  
        return r;  
    }  
    // 4.2 过期，尝试获取锁  
    String lockKey = LOCK_SHOP_KEY + id;  
    boolean isLock = tryLock(lockKey);  
  
    // 5.获取锁成功，开启独立线程，实现缓存重建  
    if(isLock){  
        CACHE_REBUILD_EXECUTOR.submit(() -> {  
            //重建缓存  
            try {  
                R r1 = dbFallback.apply(id);  
                this.setWithLogicExpire(key,r1,time,unit);  
            } catch (Exception e) {  
                throw new RuntimeException(e);  
            } finally {  
                //释放锁  
                unlock(lockKey);  
            }  
        });  
    }  
    // 6.获取锁失败，返回缓存数据  
    return r;  
}
```

3. 数据封装
```java
// Java对象存储到Redis中  
public void set(String key, Object value, Long time, TimeUnit unit){  
    stringRedisTemplate.opsForValue().set(key, JSONUtil.toJsonStr(value),time,unit);  
}  
  
// Java对象添加逻辑过期，存储到Redis中  
public void setWithLogicExpire(String key,Object value,Long time,TimeUnit unit){  
    // 设置逻辑过期  
    RedisData redisData = new RedisData();  
    redisData.setData(value);  
    redisData.setExpireTime(LocalDateTime.now().plusSeconds(unit.toSeconds(time)));  
    // 存入Redis  
    stringRedisTemplate.opsForValue().set(key,JSONUtil.toJsonStr(redisData));  
}
```

# 七、常用API总结：

1. 数据转换工具

| 转换方向        | API                            | 当前使用场景           |
| ----------- | ------------------------------ | ---------------- |
| Java → JSON | `JSONUtil.toJsonStr(obj)`      | Java对象写Redis     |
| JSON → Java | `JSONUtil.toBean(json, clazz)` | Redis读取业务对象      |
| Bean → Bean | `BeanUtil.copyProperties()`    | `User → UserDTO` |
| Bean → Map  | `BeanUtil.beanToMap()`         | DTO → Redis Hash |
| Map → Bean  | `BeanUtil.fillBeanWithMap()`   | Redis Hash → DTO |
| 判断空字符串      | `StrUtil.isBlank()`            | 判断Redis是否无有效数据   |
| 判断非空        | `StrUtil.isNotBlank()`         | 判断缓存是否命中         |
| Boolean安全判断 | `BooleanUtil.isTrue()`         | SETNX结果判断        |
| 时间单位转换      | `unit.toSeconds(time)`         | 逻辑过期             |
| 执行传入函数      | `dbFallback.apply(id)`         | 调用数据库查询          |

2. Redis API

|数据类型|Spring API|常用方法|作用|
|---|---|---|---|
|String|`opsForValue()`|`get(key)`|获取值|
|String|`opsForValue()`|`set(key,value)`|保存值|
|String|`opsForValue()`|`set(key,value,time,unit)`|保存并设置TTL|
|String|`opsForValue()`|`setIfAbsent()`|SETNX，常用于锁|
|String|`opsForValue()`|`increment()`|自增|
|Hash|`opsForHash()`|`put()`|保存一个字段|
|Hash|`opsForHash()`|`putAll()`|保存整个Map|
|Hash|`opsForHash()`|`get()`|获取一个字段|
|Hash|`opsForHash()`|`entries()`|获取整个Hash|
|Hash|`opsForHash()`|`delete()`|删除Hash字段|
|List|`opsForList()`|`leftPush()`|左侧插入|
|List|`opsForList()`|`rightPush()`|右侧插入|
|List|`opsForList()`|`leftPop()`|左侧弹出|
|List|`opsForList()`|`rightPop()`|右侧弹出|
|List|`opsForList()`|`range()`|查询指定范围|
|Set|`opsForSet()`|`add()`|添加元素|
|Set|`opsForSet()`|`members()`|查询所有成员|
|Set|`opsForSet()`|`isMember()`|判断成员是否存在|
|Set|`opsForSet()`|`remove()`|删除元素|
|Set|`opsForSet()`|`intersect()`|求交集|
|ZSet|`opsForZSet()`|`add()`|添加元素和score|
|ZSet|`opsForZSet()`|`incrementScore()`|修改分数|
|ZSet|`opsForZSet()`|`range()`|升序查询|
|ZSet|`opsForZSet()`|`reverseRange()`|降序查询|