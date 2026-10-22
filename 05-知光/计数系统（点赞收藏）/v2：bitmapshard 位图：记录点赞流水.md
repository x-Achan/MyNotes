
# 方法

每个帖子在redis中有一个key
```java
bitmap:post:12345:like
```
redis中用位图bitmap的每一位，记录用户是否点赞这篇帖子
比如，id为10000的用户点赞
则将bit[10000] = 1

问题，用户id大小，决定了存储空间，用户id越来越大，且帖子点赞数少，但是存储的id号很大，导致存储稀疏，浪费空间
方法：对key分片

```
bitmap:post:12345:like:0  
bitmap:post:12345:like:1  
bitmap:post:12345:like:2
...
```
分片大小决定了每个key的存储空间
用户id首先计算所在分片号，得到key
```java
userId / CHUNK_SIZE
```
再计算片内偏移量
```java
userId % CHUNK_SIZE
```
得到自己的bit位
再进行修改


# 点赞计数

lua脚本：读当前位 → 与目标一致则返回 0（无变化）→ 否则置位并返回 1
KEYS[1]=位图键　ARGV[1]=位偏移　ARGV[2]=目标值(0/1)

```lua
local cur = redis.call('GETBIT', KEYS[1], ARGV[1])  
local want = tonumber(ARGV[2])  
if cur == want then  
    return 0end  
redis.call('SETBIT', KEYS[1], ARGV[1], want)  
return 1
```

包装到函数中，返回是否变化 changed
```java
// changed 给出"是否真的变化"  
Long changed = redis.execute(  
        TOGGLE_BIT,  
        List.of(bmKey),  
        String.valueOf(BitmapShard.bitOf(userId))  
        , on ? "1" : "0");
```
changed = true，发kafka事件
```java
eventProducer.publish(CounterEvent.of("knowpost",eid,type,userId,on ? 1:-1));
```
Redis中的计数cnt对当前的帖子点赞数key自增
```java
long count = applyDeltaAtomic(type, postId, on ? 1 : -1);
```
自增也是执行lua脚本：查询key，自增key
最后返回结果


# 判断用户是否点赞

取出bitmap中值
```java
Boolean bit = redis.opsForValue().getBit(bmKey, BitmapShard.bitOf(userId));
```