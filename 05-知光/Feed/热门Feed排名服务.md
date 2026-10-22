
>"每分钟重算一次热门榜，生成新版本，旧版本保留 30 分钟

```
① 加分布式锁（防多实例重复建）
    ↓
② 确保候选集存在（首次建）
    ↓
③ 拿候选集 ID（最多 2 万）
    ↓
④ 批量拿"帖子分片"
    ↓
⑤ 批量拿"点赞数 / 收藏数"
    ↓
⑥ 生成"新版本号"（当前分钟）
    ↓
⑦ 逐个算"热门分数"
    ↓
⑧ 写"新榜 ZSet"
    ↓
⑨ 设"旧榜 TTL"（30 分钟）
    ↓
⑩ 更新"当前版本号"
    ↓
⑪ 释放锁
```

```java
public void rebuild() {  
    RLock lock = redisson.getLock(FeedKeys.HOT_REBUILD_LOCK);  
    boolean locked = false;  
  
    try {  
        locked = lock.tryLock();  
        if (!locked) return;  
  
        // 确保"候选集"存在  
        ensureCandidates();  
         //  拿"候选集的 ID"（最多 2 万）  
        Set<String> members = redis.opsForZSet().reverseRange(FeedKeys.HOT_CANDIDATES, 0, MAX_CANDIDATES - 1L);  
  
        if (members == null) {  
            members = Set.of();  
        }  
  
        List<Long> ids = members.stream().map(Long::parseLong).toList();  
  
        // 批量拿"帖子分片"  
        Map<Long, FeedPostSnapshot> posts = feedCacheService.getPosts(ids);  
        // 批量拿"点赞数 / 收藏数"  
        Map<Long, Long> likes = counterService.getCounts(ids, CounterType.LIKE);  
        Map<Long, Long> favorites = counterService.getCounts(ids, CounterType.FAV);  
  
        // 版本 = "当前分钟"  
        long version = System.currentTimeMillis() / 60_000L;  
        String rankKey = FeedKeys.hotRank(version);  
  
        //  删旧榜（如果版本号相同，覆盖）  
        redis.delete(rankKey);  
  
        // 逐个算"热门分数"  
        Set<ZSetOperations.TypedTuple<String>> tuples = new HashSet<>();  
        Instant now = Instant.now();  
  
        for (Long id : ids) {  
            FeedPostSnapshot post = posts.get(id);  
  
            //  过滤：非"公开 + 已发布" → 跳过  
            if (post == null || !post.published() || !post.publicVisible()) {  
                continue;  
            }  
  
            // ageHours  
            double ageHours = Math.max(0,  
                    Duration.between(post.publishTime() == null ? post.createTime() : post.publishTime(), now).toMinutes() / 60.0);  
  
            // 互动分  
            double interaction =  
                    likes.getOrDefault(id, 0L) * 3.0  
                    + favorites.getOrDefault(id, 0L) * 5.0  
                    + 1.0;  
            // 时间衰减  
            double score = interaction / Math.pow(ageHours + 2.0, 1.5);  
            tuples.add(ZSetOperations.TypedTuple.of(String.valueOf(id), score));  
        }  
  
        // 写新榜  
        if (!tuples.isEmpty()) {  
            redis.opsForZSet().add(rankKey, tuples);  
        }  
        /*  
         * 游标中的旧 version 还能继续使用，  
         * 所以旧榜保留 30 分钟。  
         */        redis.expire(rankKey, Duration.ofMinutes(30));  
        // 更新"当前版本"  
        redis.opsForValue().set(FeedKeys.HOT_CURRENT_VERSION, String.valueOf(version));  
    } finally {  
        if (locked && lock.isHeldByCurrentThread()) {  
            lock.unlock();  
        }  
    }  
}
```