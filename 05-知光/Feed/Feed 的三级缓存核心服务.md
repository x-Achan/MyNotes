```
┌─────────────────────────────────────────┐
│  FeedCacheService                        │
├─────────────────────────────────────────┤
│  📄 页面缓存（Page Cache）                │
│    getPage(key)  ← L1 → L2               │
│    putPage(key, page)  → L2 + L1        │
│                                          │
│  📦 帖子分片缓存（Post Fragment）          │
│    getPosts(postIds)  ← L3 → MySQL       │
│    putPost(snapshot)  → L3              │
│    refreshPost(postId)  ← 从 MySQL 刷新  │
│    evictPost(postId)  ← 删缓存           │
└─────────────────────────────────────────┘
```
# 一、caffeine本地缓存配置

### 依赖

```xml
<!-- Feed L1 本地页面缓存 -->  
<dependency>  
    <groupId>com.github.ben-manes.caffeine</groupId>  
    <artifactId>caffeine</artifactId>  
</dependency>  
```

### 配置

```java
@Configuration  
public class FeedCacheConfig {  
    @Bean  
    public Cache<String, FeedPageSnapshot> feedPageLocalCache() {  
        return Caffeine.newBuilder()  
                .maximumSize(20_000)  // 最大容量
                .expireAfterWrite(Duration.ofSeconds(30))  // TTL
                .build();  
    }  
}
```

# 二、读页面缓存 getPage

传入：key
返回：页面快照：保存当前页的ids，以及下一页的游标

```java
/**  
 * 页面快照  
 * 页面缓存只保存帖子 ID 顺序和下一页游标。  
 */  
public record FeedPageSnapshot(  
        List<Long> postIds,  
        String nextCursor,  
        boolean hasMore  
) {}
```

核心代码：
先查 L1 本地缓存，命中直接返回 page（FeedPageSnapshot）
```java
FeedPageSnapshot local = feedPageLocalCache.getIfPresent(key);
```
未命中，查 L2 页面缓存
```java
String json = redis.opsForValue().get(FeedKeys.page(key));
```
命中则回填 L1，返回 page，未命中返回 null
```java
feedPageLocalCache.put(key, page);  
return page;
```


# 三、写页面缓存 putPage

传入：key 和 page
返回：void
过程：
设置 TTL抖动防雪崩
写Redis，写本地cache
```java
long ttl = PAGE_TTL_SECONDS + ThreadLocalRandom.current().nextLong(31);  
  
redis.opsForValue().set(FeedKeys.page(key), json, Duration.ofSeconds(ttl));  
feedPageLocalCache.put(key, page);
```


# 四、读分片缓存 getPosts

传入：postIds 列表
传出：Map，存储id对应的post

过程：
MGET批量查Redis
```java
// MGET 批量查
List<String> values = redis.opsForValue().multiGet(keys);

Map<Long, FeedPostSnapshot> result = new HashMap<>();
List<Long> missing = new ArrayList<>();
```
命中放入result，未命中放入missing，分类处理

对于 missing，要MySQL重建
通过ids返回所有posts
```java
putPost(snapshot);
```
循环遍历，调用写分片缓存 putPosts 逐个写回redis分片缓存

返回result


# 五、写分片缓存 putPost（单个片）

传入：FeedPostSnapshot

```java
long ttl = POST_TTL_SECONDS + ThreadLocalRandom.current().nextLong(601);
redis.opsForValue().set(
					FeedKeys.postFragment(snapshot.id()), 
					json, 
					Duration.ofSeconds(ttl)); //ttl设置要抖动
```

# 六、刷新分片缓存

传入：postId

从数据库读，删除原本分片，存储新的分片
```java
KnowPostFeedRow row = knowPostMapper.findFeedRowById(postId);  
evictPost(postId);  
putPost(toSnapshot(row));  
```


# 七、删除分片缓存（主动失效）

传入： postId
```java
redis.delete(FeedKeys.postFragment(postId));
```