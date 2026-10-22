
>管理 作者 “Feed ZSet"、"关注收件箱 ZSet"、"大V 拉取集合"、"热门候选 ZSet" 的读写和自愈

```
┌────────────────────────────────────────────────┐
│  FeedIndexService                              │
├────────────────────────────────────────────────┤
│  📖 读（Read）                                  │
│    readAuthor(authorId, cursor, limit)         │
│    readFollowing(userId, cursor, limit)        │
│    readHot(version, cursor, limit)             │
│                                                │
│  🛡️ 自愈（Ensure）                              │
│    ensureAuthor(authorId)                      │
│    ensureFollowing(userId)                     │
│                                                │
│  🔄 事件投影（Project）                          │
│    upsertAuthorPost(post)                      │
│    removeAuthorPost(post)                      │
│    addHotCandidate(post)                       │
│    removeHotCandidate(postId)                  │
│    projectOrdinaryPost(post, eligible)         │
│    projectRelation(followerId, authorId, ...)  │
│                                                │
│  🔢 版本（Version）                             │
│    authorVersion / followingVersion / bigVEpoch│
└────────────────────────────────────────────────┘
```

# 一、自愈（Lazy重建）

>读取索引ZSet时，要确保ZSet都存在，如果不存在需要互斥重建
>个人主页ZSet和关注ZSet是懒重建，过期没有时才重建
>hot Set定时重建

操作：Redis命中返回，不存在，加锁从数据库重建

## 1. 确保作者索引存在 ensureAuthor

传入：作者authorId

得到Key，先判断是否存在
```java
String key = FeedKeys.authorIndex(authorId);
```
如果存在，续期TTL
```java
redis.expire(key, Duration.ofDays(INDEX_TTL_DAYS));
```
不存在，加锁重建
```java
RLock lock = redisson.getLock(FeedKeys.authorLock(authorId));
boolean = locked = lock.tryLock(2, 15, TimeUnit.SECONDS);
```
重建前先再Zset中加上起始标识
```java
redis.opsForZSet().add(key, FeedKeys.INIT_MEMBER, Double.NEGATIVE_INFINIT)
```

查数据库，获取帖子列表
```java
knowPostMapper.listAuthorPostsForFeedIndex(authorId)
```
SQL语句：
```xml
<!-- 根据作者-->  
<select id="listAuthorPostsForFeedIndex" resultMap="KnowPostResultMap">  
    SELECT *    
    FROM know_posts    
    WHERE creator_id = #{creatorId}      
    AND status != 'deleted'    
    ORDER BY create_time DESC, id DESC
</select>
```

遍历列表，逐个添加到Redis的ZSet中，soore用创建时间，延长TTL
```java
redis.opsForZSet().add(  
        key,   
        String.valueOf(post.getId()),   
        post.getCreateTime().toEpochMilli());

redis.expire(key, Duration.ofDays(INDEX_TTL_DAYS));
```

最后释放锁
```java
lock.unlock();
```

# 2. 确保关注Feed存在（推拉不同处理） ensureFollowing

>关注Feed有 大V 和普通用户

有两个key：pull和push
```java
String inboxKey = FeedKeys.followingInbox(userId);  
String pullKey = FeedKeys.pullAuthors(userId);
```
如果都存在，直接返回
如果有一个不存在，获取锁进行重建，Redisson
```java
RLock lock = redisson.getLock(FeedKeys.followingLock(userId));
```
##### 大V：拉模式，只存储用户关注的大V的id，读取关注Feed时再拉帖子Id
从数据库中，先获取用户关注的大V的id
```java
Set<Long> bigAuthors = new HashSet<>(
                relationMapper.listFollowedBigAuthorIds(userId, BIG_V_THRESHOLD)
```
查询SQL：
```xml
<select id="listFollowedBigAuthorIds" resultType="long">  
    SELECT f.to_user_id    
    FROM following f             
    JOIN (        
	    SELECT to_user_id        
	    FROM following        
	    WHERE rel_status = 1        
	    GROUP BY to_user_id        
	    HAVING COUNT(*) >= #{threshold}) big_author 
    ON big_author.to_user_id = f.to_user_id    
    WHERE f.from_user_id = #{userId}      
    AND f.rel_status = 1
    </select>
```

删除原来的 pull key，初始化一个新的 pull
```java
redis.delete(pullKey);  
redis.opsForSet().add(pullKey, FeedKeys.INIT_MEMBER);
```
将用户关注的大V的id存入 pull箱 和全局大V名单中
```java
redis.opsForSet().add(pullKey, String.valueOf(authorId));
redis.opsForSet().add(FeedKeys.BIG_AUTHORS, String.valueOf(authorId));
```

##### 普通用户：推模式，inbox

查用户关注的人的最近的帖子

```java
knowPostMapper.listRecentFollowingPosts(userId, INBOX_REBUILD_SIZE)
```
SQL语句：涉及三张表，following，know_posts，users
```sql
<select id="listRecentFollowingPosts" resultType="KnowPostFeedRow">  
    SELECT    
    <include refid="FeedColumns"/>  
    FROM following f    
    JOIN know_posts p ON p.creator_id = f.to_user_id    
    JOIN users u ON u.id = p.creator_id    
    WHERE f.from_user_id = #{userId}    
    AND f.rel_status = 1    
    AND p.status = 'published'    
    AND p.visible IN ('public', 'followers')    
    ORDER BY p.create_time DESC, p.id DESC    
    LIMIT #{limit}
</select>
```

全部加入 inbox中
```java
redis.opsForZSet().add(
					inboxKey, 
					String.valueOf(row.getId()), 
					row.getCreateTime().toEpochMilli());
```
延长TTL
```java
redis.expire(inboxKey, Duration.ofDays(INDEX_TTL_DAYS));  
redis.expire(pullKey, Duration.ofDays(INDEX_TTL_DAYS));
```




# 二、读路径

## 1. 作者主页Feed

确保ZSet存在
```java
ensureAuthor
```
返回，游标分页读取
```java
readZSet(FeedKeys.authorIndex(authorId), cursor, limit)
```

## 2. 读关注Feed（推拉结合）

确保 关注 索引Set存在
```java
ensureFollowing(userId);
```
读 inbox收件箱，得到普通作者的帖子
```java
candidates.addAll(readZSet(FeedKeys.followingInbox(userId), cursor, limit));
```
读 大V  id集合，逐个拉取他们的帖子
```java
// 获取id Set
Set<String> pullAuthors = redis.opsForSet().members(FeedKeys.pullAuthors(userId));
```
读每个大V的主页Feed，readAuthor
```java
readAuthor(authorId, cursor, limit)
```
最后多路合并+ 去重 + 按socre排序得到 candidates


## 3. 读热门Feed

读 热门Feed的ZSet，游标分页
```java
readZSet(FeedKeys.hotRank(version), cursor, limit)
```

关键：热门Feed用version区分版本


## 4. 游标分页 ZSet

传入：key，cursor，limit
返回：帖子id集合 FeedCandidate list

过量取三倍，reverseRangeByScoreWithScores，按 score 倒序 + 过滤
```java
redis.opsForZSet().reverseRangeByScoreWithScores(
                    key,
                    0,
                    cursor.score(),
                    0,
                    Math.max(limit * 3L, limit)   // ← 过量取 3 倍
            );
```

通过 afterCursor 判断，严格小于 cursor 或同 score 且 postId 小，放入result返回


# 三、写路径（事件投影）


## 1. 帖子新增/更新  upsertAuthorPost

主页Feed索引增加记录，只有在索引ZSet存在时才写
```java
String key = FeedKeys.authorIndex(post.getCreatorId());

if (redis.hasKey(key)) {   // 只在"已存在"时写
        redis.opsForZSet().add(
                key,
                String.valueOf(post.getId()),
                post.getCreateTime().toEpochMilli()
        );
}
```

版本key自增，作者主页旧页面缓存失效
```java
redis.opsForValue().increment(FeedKeys.authorVersion(authorId));
```
## 2. 帖子删除 removeAuthorPost

主页ZSet，直接删除该帖子，版本自增
```java
redis.opsForZSet().remove(
            FeedKeys.authorIndex(post.getCreatorId()),
            String.valueOf(post.getId())
);

redis.opsForValue().increment(FeedKeys.authorVersion(authorId));
```

## 3. 热门候选 addHotCandidate

直接往里面加
```java
redis.opsForZSet().add(
            FeedKeys.HOT_CANDIDATES,
            String.valueOf(post.getId()),
            post.getCreateTime().toEpochMilli()
    );
```

## 4. 推给粉丝 projectOrdinaryPost（写扩散）

查作者所有粉丝

```java
List<Long> followers = relationMapper.listFollowerIds(post.getCreatorId());
```

循环遍历粉丝，逐个推送到 inbox中
```java
String inbox = FeedKeys.followingInbox(followerId);

redis.opsForZSet().add(
					inbox, 
					String.valueOf(post.getId()),
					post.getCreateTime().toEpochMilli());
```
关注页面版本 + 1
```java
redis.opsForValue().increment(FeedKeys.followingVersion(userId));
```

## 5. 关注/取关 projectRelation

影响用户的 关注 Feed，涉及 pull 和 push

```java
String pullKey = FeedKeys.pullAuthors(followerId);
String inboxKey = FeedKeys.followingInbox(followerId);
```

##### 关注大V，加入pull
```java
redis.opsForSet().add(pullKey, String.valueOf(authorId));
redis.opsForSet().add(FeedKeys.BIG_AUTHORS, String.valueOf(authorId));
```

##### 取关大V，从pull中移除
```java
redis.opsForSet().remove(pullKey, String.valueOf(authorId));
```

##### 关注普通作者
回填最近 n 条帖子到inbox
```java
knowPostMapper.listRecentVisiblePostsByAuthor(authorId, FOLLOW_BACKFILL_SIZE)
```
循环处理，逐个回填
```java
redis.opsForZSet().add(  
        inboxKey,  
        String.valueOf(row.getId()),  
        row.getCreateTime().toEpochMilli()  
);
```
##### 取关普通作者

先从普通作者的主页获取它的帖子ids
```java
Set<String> ids = redis.opsForZSet().range(FeedKeys.authorIndex(authorId), 0, -1);
```

在从用户的inbox中删除该作者的所有帖子
```java
redis.opsForZSet().remove(inboxKey, ids.toArray());
```

关注Feed页面缓存版本 + 1
```java
redis.opsForValue().increment(FeedKeys.followingVersion(userId));
```








