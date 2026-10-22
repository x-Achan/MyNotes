

```

public static final String BIG_V_EPOCH = "feed:big-v:epoch";String pageKey = "following:" + viewerId + ":" + userVersion + ":" + bigVEpoch + ":" + safeSize + ":" + cursorToken(cursorValue); String pageKey = "profile:" + authorId + ":" + scope + ":" + version + ":" + safeSize + ":" + cursorToken(cursorValue); Predicate<FeedPostSnapshot> permission; if (owner) { permission = post -> !post.deleted(); } else if (following) { permission = post -> post.published() && (post.publicVisible() || post.followersVisible()); } else { permission = post -> post.published() && post.publicVisible(); }这些代码都是干嘛的，以及key

Predicate<FeedPostSnapshot> permission 这个是什么
```


```
┌──────────────────────────────────────────────┐
│  FeedServiceImpl                             │
├──────────────────────────────────────────────┤
│  🌐 对外接口（4 种 Feed）                       │
│    hot(cursor, size, viewerId)   ← 热门       │
│    mine(viewerId, cursor, size)  ← 我的       │
│    profile(authorId, viewerId, cursor, size)  │
│                                  ← 他人        │
│    following(viewerId, cursor, size)  ← 关注  │
│                                              │
│  🔧 内部方法                                  │
│    readPage(...)         ← 读一页（核心）      │
│    hydrate(...)          ← 组装响应           │
│    timeCursor / nextCursor ← 游标              │
│    encode / decode       ← 游标编解码          │
│    safeSize / cursorToken ← 工具              │
└──────────────────────────────────────────────┘
```


# 核心 readPage 读一页

第一步：先读页面缓存 调用 getPage()，读L1 L2，命中直接组装结果

第二步：未命中 → 从 ZSet 拿候选，过滤，凑够 size











