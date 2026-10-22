## 一、CAS乐观锁

1. 乐观锁

认为线程安全问题不一定会发生，因此不加锁，**只是在个更新数据时去判断有没有其他线程对数据做了修改**，如果没有修改则认为是安全的，自己才更新数据，如果已经被其他线程修改，说明发生了安全问题，此时可以重试或异常

CAS乐观锁：主要解决资源数量竞争问题
>Compare And Swap
>核心：更新数据时，不仅修改数据，还要验证当前状态是否满足条件

2. 典型场景：库存超卖
多个用户线程同时购买，库存stock超卖
```sql
UPDATE product
SET stock = stock - 1
WHERE id = 1
AND stock > 0
```

>只有满足：库存 stcok > 0，才允许扣减

Java代码：
```java
// 扣减库存（CAS乐观锁）
boolean success = seckillVoucherService
        .update()
        .setSql("stock = stock - 1")
        .eq("voucher_id", voucherId)
        .gt("stock",0) //核心
        .update();


if(!success){
    return Result.fail("库存不足");
}
```

# 二、悲观锁

1. 悲观锁
>认为线程安全问题一定会发生，因此在操作数据之前先获得锁，确保线程串行执行，例如Synchronized、Lock都属于悲观锁

2. 典型场景
- 一个用户只能购买一次
- 一个用户只能领取一次新人礼包
- 一个账号只能参与一次活动
>连续相同请求发送，只有一个请求成功，其他请求拒绝

3. 一个用户购买商品过程
- 查询库存是否还有
- 创建订单数据
>问题：查询和创建不是原子操作，中间有时间窗口，如果用户快速请求多次，就会创建多个订单

核心目标：让同一个业务对象（例如同一个用户）的关键业务流程，同一时间只能有一个线程执行，例如：查询库存 + 创建订单

4. 使用悲观锁实现一人一单

最简单的思想，就是给用户加锁，例如一个用户只能购买一次，则锁住用户对象

例子：
```java
Long userId = UserHolder.getUser().getId();
String lockKey = "user:" + userId;

synchronized(lockKey.intern()){
    // 查询订单

    // 判断是否存在

    // 创建订单
}
```

不能锁userID，因为两个请求可能产生两个不同的Long对象，锁住的不是同一个对象

所以使用字符串常量池
重点：
```
intern()
```

>作用：让相同字符串指向同一个对象

注意：这里用悲观锁实现的场景是单机模式，在服务器集群中，**一个JVM只有一个锁监视器**，多个JVM锁的对象不同，需要使用Redis分布式锁

# 三、一个用户领取秒杀优惠券案例完整代码（使用乐观锁与悲观锁）

```java
@Override
@Transactional
public Result seckillVoucher(Long voucherId){

    //1.查询优惠券
    SeckillVoucher voucher =
        seckillVoucherService.getById(voucherId);

    //2.判断秒杀时间
    if(voucher.getBeginTime()
        .isAfter(LocalDateTime.now())){
        return Result.fail("未开始");
    }


    if(voucher.getEndTime()
        .isBefore(LocalDateTime.now())){
        return Result.fail("已结束");
    }

    //3.判断库存
    if(voucher.getStock() < 1){
        return Result.fail("库存不足");
    }

// 悲观锁
    Long userId =
        UserHolder.getUser().getId();
    String lockKey =
        "order:" + userId;
    synchronized(lockKey.intern()){

        //4.查询用户是否已经购买
        int count =
          query()
          .eq("user_id",userId)
          .eq("voucher_id",voucherId)
          .count();

        if(count > 0){
            return Result.fail(
              "不能重复购买"
            );
        }

// 乐观锁
        //5.扣库存
        boolean success =
        seckillVoucherService
        .update()
        .setSql("stock=stock-1")
        .eq("voucher_id",voucherId)
        .gt("stock",0)
        .update();


        if(!success){
            return Result.fail(
              "库存不足"
            );
        }

        //6.创建订单
        VoucherOrder order =
              new VoucherOrder();
        order.setUserId(userId);
        order.setVoucherId(voucherId);
        save(order);
        
        return Result.ok(order.getId());
    }
}
```

