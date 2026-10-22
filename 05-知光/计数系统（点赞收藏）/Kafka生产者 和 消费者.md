
# 生产者

```java

private String topic;  // topic 用 String

kafkaTemplate.send(topic, event.eid(), payload).get(5, TimeUnit.SECONDS);
```

发事件失败的话要回滚报错
```java
try {  
    // 发事件  
    eventProducer.publish(CounterEvent.of("knowpost",eid,type,userId,on ? 1:-1));  
} catch (Exception e) {  
    toggleBitmap(type, postId, userId, !on); // 补偿：把位改回去  
    throw new IllegalStateException("点赞失败，请重试", e);  
}
```

形参：topic，key，data
key我们定义的是事件:CounterEvent
```java
public record CounterEvent(  
        String eventId,  
        String etype,  
        String eid,  
        String metric,  
        long uid,  
        int delta,  
        long ts  
) {
```

# 消费者
落库sql语句：
```xml
<!-- 写聚合落库：一次多值 INSERT 替 N 次单条 INSERT。  
 这正是压测里"唯一索引 gap 锁竞争"的解药：200 次插入 → 1 次插入。 -->  
<insert id="batchInsertIgnore">  
    INSERT IGNORE INTO like_record (user_id, post_id, type) VALUES    <foreach collection="rows" item="r" separator=",">  
        (#{r.userId}, #{r.postId}, #{r.type})    </foreach>  
</insert>
```

IGNORE是遇到uk直接忽略

```java
@KafkaListener(
    topics = "${counter.kafka.topic:counter-events}", //主题
    groupId = "${spring.kafka.consumer.group-id:counter-persist}" //组id
)
```


```java
// 一批消息messages，确认工具ack
public void onMessages(List<String> messages, Acknowledgment ack)
```

批量消费需要在 Spring kafka中配置
```yaml
spring:
  kafka:
    consumer:
      max-poll-records: 500      # 一次最多拿 500 条
      enable-auto-commit: false  # 关自动提交
    listener:
      type: batch                # 批量模式
      ack-mode: manual           # 手动 ack
```

messages空批，直接不处理，直接ack确认

反序列化：单条坏不能影响整批
```java
List<CounterEvent> events = new ArrayList<>(messages.size());
for (String raw : messages) {
    try {
        events.add(objectMapper.readValue(raw, CounterEvent.class));
    } catch (Exception e) {
        log.error("[计数落库] 事件反序列化失败，跳过: {}", raw, e);
    }
}
```

批量 insert 再 确认
```java
likeRecordMapper.batchInsertIgnore(rows);
ack.acknowledge();
```