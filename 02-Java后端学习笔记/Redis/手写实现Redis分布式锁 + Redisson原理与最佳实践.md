手写 Redis 锁是为了理解分布式锁原理；生产环境更多使用 Redisson 这种成熟方案
# 一、手写Redis锁

以一人一单问题为例，在单机情况下，可以使用Sycronized悲观锁实现对相同请求得互斥访问，但是在分布式集群下，不同主机有不同的JVM锁监控器，无法做到不同主机之间得互斥访问，因此需要互斥锁，**满足在分布式集群下，多个线程可见并且互斥的锁**

1. 如何实现？

锁机制核心思想：
> 多个线程访问共享资源时，通过竞争一个唯一资源，保证同一时间只有一个线程进入关键代码区域

因此，手写Redis锁实现需要：
利用Redis中 SET NX key 唯一性的特点，保证同一时间只有一个线程创建成功
- Redis的Key作为锁资源（唯一性）
- 获取锁操作SET NX就是原子操作（原子性）
- **TTL：防止持锁线程异常退出导致死锁**
   
核心方法：
```bash
# 添加锁，NX是互斥，EX是超时时间
SET lock thread1 NX EX 10
# 手动释放锁
DEL key
```
Java核心API：添加Key，获取锁
```java
stringRedisTemplate
		.opsForValue()
		.setIfAbsent(key,value,timeoutSec,TimeUnit.SECONDS); 
```
删除Key，释放锁
```java
stringRedisTemplate.delete(KEY_PREFIX + name);  
```

2. 问题1：获取锁后，执行业务过程中TTL过期

Redis分布式锁为了防止死锁需要设置TTL，如果A线程获取锁后，在执行业务逻辑时发生阻塞，此时TTL过期，另一个B线程可能重新获取同一个锁Key，原线程A执行完成后执行删除锁，会误删其B线程持有的锁

解决方法：
**Value用于标识锁的持有者**
在释放锁前（delete），需要**取出get**锁的value标识，判断当前线程是否是锁的获取者，标识：UUID+线程id，如果是则**释放锁delete**
>Key解决“大家抢的是不是同一把锁”，Value解决“这把锁是不是我的”

定义标识前缀
```java
private static final String ID_PREFIX = UUID.randomUUID().toString() + "-";
```
核心代码：
```java
String key = KEY_PREFIX + name;  
// value = UUID + 线程id
String value = ID_PREFIX + Thread.currentThread().getId();  
  
Boolean success = stringRedisTemplate  
        .opsForValue()  
        .setIfAbsent(key,value,timeoutSec, TimeUnit.SECONDS);
```
例如：
```
key:
lock:order:100

value:
线程唯一标识(UUID)
```

3. 问题2：判断标识的get和delete操作不是原子操作

判断锁标识并且删除key释放锁的过程，需要对Redis执行 get  和 delete，执行多个Redis命令，不具备原子性，在两个操作中间如果另一个线程提前delete，也会发生误删


```java
@Override  
public void unLock(){  
    // 获取线程标识  
    String threadID = ID_PREFIX + Thread.currentThread().getId();  
    String id = stringRedisTemplate.opsForValue().get(KEY_PREFIX + name);  
    //判断标识是否一致  
    if(threadID.equals(id)){  
        stringRedisTemplate.delete(KEY_PREFIX + name);  
    }  
}
```

因此要保证释放锁原子性

解决办法：Lua脚本保证多个Redis的操作原子性

lua脚本内容：
```lua
if redis.call('get',KEYS[1]) == ARGV[1]
then
    return redis.call('del',KEYS[1])
end
return 0
```

Java调用脚本

```java
private static final DefaultRedisScript<Long> UNLOCK_SCRIPT;  
static{  
    UNLOCK_SCRIPT = new DefaultRedisScript<>();  
    UNLOCK_SCRIPT.setLocation(new ClassPathResource("unlock.lua"));  
    UNLOCK_SCRIPT.setResultType(Long.class);  
}
```

新的释放锁操作变为一个函数，保证原子性
```java
@Override  
public void unLock(){  
    stringRedisTemplate.execute(  
            UNLOCK_SCRIPT,  
            Collections.singletonList(KEY_PREFIX + name),  
            ID_PREFIX + Thread.currentThread().getId()  
    );  
}
```

利用Redis锁实现分布式锁的核心思想：
- **SETNX解决互斥**
- **TTL解决死锁**
- **value解决锁归属**
- **Lua解决释放锁原子性**


4. 简单的Redis实现分布式锁的案例：
```java
public class SimpleRedisLock implements ILock{  
  
    private StringRedisTemplate stringRedisTemplate;  
    private String name;  
    private static final String KEY_PREFIX = "lock";  
    private static final String ID_PREFIX = UUID.randomUUID().toString() + "-";  
  
    private static final DefaultRedisScript<Long> UNLOCK_SCRIPT;  
    static{  
        UNLOCK_SCRIPT = new DefaultRedisScript<>();  
        UNLOCK_SCRIPT.setLocation(new ClassPathResource("unlock.lua"));  
        UNLOCK_SCRIPT.setResultType(Long.class);  
    }  
  
    public SimpleRedisLock(String name,StringRedisTemplate stringRedisTemplate){  
        this.name = name;  
        this.stringRedisTemplate = stringRedisTemplate;  
    }  
  
    @Override  
    public boolean tryLock(long timeoutSec) {  
        String key = KEY_PREFIX + name;  
        String value = ID_PREFIX + Thread.currentThread().getId();  
  
        Boolean success = stringRedisTemplate  
                .opsForValue()  
                .setIfAbsent(key,value,timeoutSec, TimeUnit.SECONDS);  
        return Boolean.TRUE.equals(success);  
    }  
  
  // lua脚本实现原子性
    @Override  
    public void unLock(){  
        stringRedisTemplate.execute(  
                UNLOCK_SCRIPT,  
                Collections.singletonList(KEY_PREFIX + name),  
                ID_PREFIX + Thread.currentThread().getId()  
        );  
    }  
  // 解决锁的归属，判断标识
    @Override  
    public void unLock(){  
        // 获取线程标识  
        String threadID = ID_PREFIX + Thread.currentThread().getId();  
        String id = stringRedisTemplate.opsForValue().get(KEY_PREFIX + name);  
        //判断标识是否一致  
        if(threadID.equals(id)){  
            stringRedisTemplate.delete(KEY_PREFIX + name);  
        }  
    }  
}
```

使用框架：
```java
// 创建锁对象
SimpleRedisLock lock = new SimpleRedisLock("order:" + userId,stringRedisTemplate);
// 获取锁
boolean isLock = lock.tryLock(1200);
```

# 二、Redisson分布式锁

企业实际开发中，如果项目已经引入 Redis，并且需要分布式锁，一般优先使用 Redisson，而不是自己手写 Redis 锁

Redisson相比手写Redis分布式锁，主要解决：
1. **同一线程重复获取锁的问题（可重入）**
2. **获取锁失败后的等待问题（锁重试）**
3. **业务执行时间不确定导致锁过期的问题（看门狗）**

4. Redisson实践
依赖：
```xml
<dependency>
    <groupId>org.redisson</groupId>
    <artifactId>redisson-spring-boot-starter</artifactId>
    <version>3.23.5</version>
</dependency>
```

编写配置类

```java
@Configuration  
public class RedissonConfig {  
    @Bean  
    public RedissonClient redissonClient(){  
        Config config = new Config();  
        config.useSingleServer()  
                .setAddress("redis://127.0.0.1:6379")  
                .setPassword("123321");  
        return Redisson.create(config);  
    }  
}
```

注入RedissonClient
```java
@Resource
private RedissonClient redissonClient;
```
使用
```java
// 创建锁对象
RLock lock = redissonClient.getLock(key);
// 获取锁
boolean isLock = lock.tryLock();
```

2. 核心机制

2.1 可重入锁原理

Redisson基于Redis Hash保存锁信息，其中field保存线程唯一标识，value保存重入次数。获取锁时利用Lua脚本保证判断和修改的原子性；释放锁时减少重入次数，直到次数为0才删除锁

>参考Java中的ReentranLock，记录重入次数state

2.2 锁重试机制：
拿不到锁，可以等待一段时间继续尝试
```java
// 参数分别是：等待获取锁时间、锁自动释放时间TTL
boolean isLock = lock.tryLock(1,10,TimeUnit.SECONDS);
```

2.3 看门狗机制：
如果业务没有执行完成，就自动延长锁时间
默认情况下
- 锁时间 = 30秒
- 看门狗每10秒续期一次
不指定leaseTime时，Redisson开启看门狗
```java
lock.tryLock();
```
指定leaseTime时，关闭看门狗
```java
lock.tryLock(1,10,SECONDS);
```

