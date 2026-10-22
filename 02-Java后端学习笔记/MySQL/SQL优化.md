
 1. insert 优化
 - 手动提交事务（建议）
```mysql
strat treasaction
insert into 表名 values('');
insert into 表名 values('');
insert into 表名 values('');
commit;
```

- 主键顺序插入(性能更高)
乱序插入可能会导致页分裂现象 

大批量数据插入 
insert性能较低，使用mysql数据库提供的**load指令**（加载本地文件）进行插入

```mysql
# 客户端连接服务器端时，加上参数 --local-infile
mysql --local-infile -u root -p
# 设置全局参数local_infile为1，开启从本地加载文件导入数据的开关
set global local_infile=1;
# 查看开关是否开启
select @@local_infile;
# 执行load指令将准备好的数据，加载到表结构中
load data local infile '/root/sql1.log' into table 表名 fields terminated by ',' lines terminated by '\n';
```

2. 主键优化
满足业务需求的情况下，尽量降低主键的长度
插入数据时，尽量选择顺序插入，选择使用auto_increment自增主键
尽量不要使用uuid做主键或者其他自然主键
业务操作时，避免对主键的修改

3. order by优化

mysql两种排序方式（用explain在extra后显示）：
- using filesort：所有不是通过索引直接返回排序结果的排序都叫FileSort排序，通过表的索引或全表扫描，读取满足条件的数据行，然后在排序缓冲区sort buffer中完成排序操作
- using index：通过有序索引顺序扫描直接返回有序数据，不需要额外排序，操作效率高

根据排序字段建立合适的索引，多字段排序时，也遵循最左前缀法则
尽量使用覆盖索引
多字段排序，一个升序一个降序，此时需要注意联合索引在创建时规则
如果不可避免的出现filesort，大数据量排序时，可以适当增加排序缓冲区大小sort_buffer_size(默认256K)

4. group by优化
分组操作时，可以通过索引提高效率
分组操作时，索引的使用也是满足最左前缀法则 

5. limit优化
一般分页查询时，通过创建覆盖索引能够比较好的提升性能，可以通过覆盖索引加子查询的形式进行优化

6. count优化
性能：count(字段)<count(主键 id)<count(1)<count(\*)

7. update优化
 InnoDB的行锁是针对索引加的锁，不是针对记录加的锁，并且该索引不能失效，否则回从行锁升级为表锁 
 尽量根据主键/索引字段进行更新