
同步调用
- 时效性强
- 拓展性差
- 性能下降
- 级联失败问题


异步调用
- 消息发送者
- 消息代理
- 消息接收者

优点：
- 接触耦合，拓展性强
- 无需等待，性能好
- 故障隔离
- 缓存消息，流量削峰填谷

RabbitMQ的整体架构及核心概念：
- publisher
- consumer
- queue
- exchange
 
Spring AMQP
提供模板来发送和接收消息，其中spring-amqp是基础抽象，spring-rabbit是底层的默认实现

配置pom.xml

```xml
spring:
  rabbitmq:
    host: 192.168.150.101  # 主机名
    port: 5672             # 端口
    virtual-host: /hmall   # 虚拟主机
    username: hmall        # 用户名
    password: 123          # 密码
```

生产者API
```java
@Autowired
private RabbitTemplate rabbitTemplate;
```
作用
>Spring AMQP提供的RabbitMQ操作模板，用于发送消息

消息发送
```java
rabbitTemplate.convertAndSend(
        queueName,
        message
);
```

消费者API：
创建监听类
```java
@Component
public class OrderListener {
}
```

消费者必须交给Spring管理

 @RabbitListener监听队列
核心API：

```
@RabbitListener(
    queues = "simple.queue"
)
public void listen(String msg){

    System.out.println(msg);

}
```

作用：
监听指定队列。

当消息进入：
```
simple.queue
```
自动调用该方法。

消费者堆积问题

默认情况下：
- RabbitMQ采用轮询机制分发消息
- 不管消费者当前是否忙，都会继续投递消息
- 可能导致某个消费者消息堆积

1. 多个消费者绑定一个队列，加快消息处理速度
2. 同一个消息只会被一个消费者处理
3. 通过设置prefech来控制消费者预取的消息数量， 处理完一条再处理下一条，实现能者多劳

因此我们需要修改 `application.yml`，设置 `preFetch` 值为 1，确保同一时刻最多投递给消费者 1 条消息

```yml
spring:
  rabbitmq:
    listener:
      simple:
        prefetch: 1 # 每次只能获取一条消息，处理完成才能获取下一个消息
```


只能生产环境都会经过exchange来发送消息，而不是直接发送到队列，交换机类型有以下三种：
- Fanout：广播
- Direct：定向
- Topic：话题

Fanout交换机，广播到每一个跟其绑定的queue

Direct交换机
- 每一个queue斗鱼Exchange设置一个BindingKey
- 发布者发送消息时，指定消息的RoutingKey
- Exchange将消息路由到BindingKey与RountingKey一致的队列

Topic交换机
类似于DiretcExchange，区别在与RountingKey可是是多个单词的列表，并且以.分割
Queue与Exchange指定BindingKey时可以使用通配符
- #:
- \*:

Java配置类Bean声明
```java
@Configuration
public class FanoutConfig {

    // 声明FanoutExchange交换机
    @Bean
    public FanoutExchange fanoutExchange(){
        return new FanoutExchange("hmall.fanout");
    }


    // 声明第1个队列
    @Bean
    public Queue fanoutQueue1(){
        return new Queue("fanout.queue1");
    }


    // 绑定队列和交换机
    @Bean
    public Binding bindingQueue1(
            Queue fanoutQueue1,
            FanoutExchange fanoutExchange){

        return BindingBuilder
                .bind(fanoutQueue1)
                .to(fanoutExchange);
    }


    // ... 略，以相同方式声明第2个队列，并完成绑定

}
```


SpringAMQP还提供了基于 `@RabbitListener` 注解来声明队列和交换机的方式：
```java
@RabbitListener(
    bindings = @QueueBinding(
        value = @Queue(name = "direct.queue1"),
        exchange = @Exchange(
            name = "itcast.direct",
            type = ExchangeTypes.DIRECT
        ),
        key = {"red", "blue"}
    )
)
public void listenDirectQueue1(String msg){

    System.out.println(
        "消费者1接收到Direct消息：[" + msg + "]"
    );

}
```

 
RabbitMQ传输本质是byte[]，SpringAMQP通过MessageConverter实现Java对象与消息之间的转换，企业开发通常使用Jackson2JsonMessageConverter替代默认JDK序列化，实现JSON格式消息传递。

使用：
```java
Jackson2JsonMessageConverter
```


第一步：引入Jackson依赖
publisher和consumer都需要：

```xml
<dependency>
    <groupId>
        com.fasterxml.jackson.core
    </groupId>

    <artifactId>
        jackson-databind
    </artifactId>
</dependency>
```

作用：
提供JSON序列化和反序列化能力

第二步：配置MessageConverter
创建配置类：

```java
@Configuration
public class MessageConfig {


    @Bean
    public MessageConverter messageConverter(){

        return new Jackson2JsonMessageConverter();

    }

}
```
SpringAMQP会自动使用这个Converter
生产者：
```java
rabbitTemplate.convertAndSend(
        exchange,
        routingKey,
        object
);
```
转换器会自动处理