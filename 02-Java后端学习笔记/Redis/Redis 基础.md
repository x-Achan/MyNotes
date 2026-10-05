
Remote Dictionary Server：远程词典服务器
是一个基于内存的键值型NoSQL数据库

启动方式：
```shell
redis-server
```

redis.config文件修改
```properties
# 监听的地址，默认是127.0.0.1，会导致只能在本地访问，修i改为0.0.0.0则可以在任意IP访问，生产环境不要设置为0.0.0

bind 0.0.0.0 

# 守护进程，修改为yes后即可后台运行
daemonize yes

# 密码
requirepass 123321

```

配置完成后，执行
```
redis-server redis.conf
```
后台启动

还可以设置开机自启


redis cli 
```shell
# IP和端口号可以不填，就是本机默认
redis-cli -h [IP地址] -p [端口号] -a [密码]
```

- Key-Value
- 单线程，每个命令具备原子性
- 低延迟，速度快（基于内存）
- 支持数据的持久化
- 支持主从集群、分片集群
- 支持多语言

数据结构
key一般是String类型

value类型多样：
- String
- Hash
- List
- Set
- SortedSet
- GEO
- BitMap
- HyperLog

通用命令：通过 help [commond] 可以查看帮助
 - keys：查看key（不建议在生产环境用）
 - del：删除指定key
 - exists：判断key是否存在
 - expire：给key设置有效期，到期自动删除
 - ttl：查看key的剩余有效期


String类型
根据字符串的格式不同，分为三类
- Stirng
- int
- float
底层都是字节数组形式存储，是不过编码方式不同，字符串类型的最大空间不能超过512m

常见命令
- set
- get
- mset：批量保存
- mget
- incr：让一个整型的key自增1
- incrby：让一个整形的key自增并指定步长
- incrbyfloat：浮点数增长并指定步长
- setnx：添加一个String类型键值对，前提是这个key不存在，否则不成功
- setex：添加一个String类型键值对，指定ttl

Redis的key的格式
- 项目名：业务名：类型：id


Hash类型
String结构是将对象序列化为JSON字符串后存储，当需要修改对象某个字段时很不方便
Hash结构可以将对象中的每个字段独立存储，可以针对单个字段做CRUD

常见命令：
- hset key field value
- hget key field
- hmset
- hmget
- hgetall
- hkeys
- hvals
- hincrby
- hsetnx     


List类型：双向链表
- 有序
- 元素可以重复
- 插入和删除快速
- 查询速度一般
常用来存储一个有序数据

命令：
- lpush key element（头部）
- lpop key
- rpush（尾部）
- rpop
- lrange key star end：返回角标范围内的所有元素
- blpop 和 brpop：阻塞式获取

如何用List模拟一个栈？队列？阻塞队列？


Set类型：可以看作是一个value为null的hashmap
- 无序
- 元素不可重复
- 查找快
- 支持交集、并集、差集等功能

命令：
- sadd key member
- srem key member
- scard key：计数
- sismember key member
- smembers
- sinter key1 key2：交集
- sdiff key1 key2：差集
- sunion keyu1 key2 ：并集

SortedSet类型：可排序集合
- 可排序
- 元素不重复

命令：
- zadd key score member
- zrem key
- zscore key member
- zrank key member：获取排名
- zcard key
- zcount key min max
- zincrby key increment member
- zrange key min max
- zrangebyscore key min max
- zdiff zinter zunion
所有排名默认都是升序，如果要将徐需要在z后面添加rev即可，例如 zrevrank




Jedis直连方式：
- 引入依赖 github
- 创建jedis对象，建立连接
- 使用命令操作数据
- 释放连接

Jedis连接池：
Jedis本身是线程不安全的，并且频繁的创建和销毁链接会有性能损耗，因此我们推荐大家使用jedis连接池代替jedis的直连方式

SpringDataRedis中提供了RedisTemplate工具类，封装对Redis的通用命令
- 引入依赖
- 配置yaml文件
- 注入RedisTemplate（提供五种不同的API）

 RedisTemplate的两种序列化方案
方案一：
- 自定义RedisTemplate
- 修改RedisTemplate的序列化器为GenericJackson2JsonRedisSerializer

方案二：
- 使用StringRedisTemplate
- 写入Redis时，手动  把对象序列化为JSON
- 读取Redis时，手动把读取到的JSON反序列化为对象


 