为什么数据库自增ID不适合分布式？

>单机数据库自增ID依赖单节点，在多实例部署时无法保证全局唯一，因此需要独立的ID生成方案

核心：
- ID = 时间戳部分 + Redis自增序列部分
- 时间戳:保证 ID 整体递增
- Redis incr：保证同一秒内生成的 ID 不重复

全局ID生成器特点：唯一、高性能、递增、安全

使用long型保存ID，64位，ID的组成部分：
- 符号位：1bit，始终为0 
- 时间戳：31bit
- 序列号：32bit

重点API：
```java
opsForValue().increment()
```

Redis生成全局ID工具类代码
```java
@Component  
public class RedisIdWorker {  
  
    // 开始时间戳  
    private static final long BEGIN_TIMESTAMP = 1640995200L;  
    // 序列号占用位数  
    private static final int COUNT_BITS = 32;  
  
    @Resource  
    private StringRedisTemplate stringRedisTemplate;  
  
    /**  
     * 生成全局唯一ID  
     *     * @param keyPrefix 业务前缀  
     * @return 唯一ID  
     */    public long nextId(String keyPrefix){  
  
        // 1. 生成时间戳  
        LocalDateTime now = LocalDateTime.now();  
  
        // 当前时间距离1970年的秒数  
        long nowSecond = now.toEpochSecond(  
                ZoneOffset.UTC  
        );  
        // 减去开始时间，减少数字长度  
        long timestamp = nowSecond - BEGIN_TIMESTAMP;  
  
        // 获取当前日期  
        String date = now.format(  
                DateTimeFormatter.ofPattern("yyyy:MM:dd")  
        );  
  
        long count = stringRedisTemplate.opsForValue()  
		        .increment("icr:" + keyPrefix + ":" + date); 
  
        return timestamp << COUNT_BITS | count;  
    }  
}
```

