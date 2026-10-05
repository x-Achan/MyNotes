
1. 逻辑存储结构
- 表空间（ibd文件）
一个mysql实例可以对应多个表空间
- 段
分为数据段、索引段、回滚段
InnoDB是索引组织表，数据段就是B+树的叶子节点，索引段即为B+树的非叶子节点，段用来管理多个区
- 区
表空间的单元结构，**每个区的大小为1M，默认InnoDB存储引擎页大小为16K，即一个区中一共有64个连续的页**
- 页
存储引擎磁盘管理最小单元，每个页大小默认16KB，为了保证页的连续性，**InnoDB存储引擎每次从磁盘申请4-5个区**
- row行
数据按行存放 

2. 结构
内存架构
- buffer pool 缓冲池
以Page页为单位，底层采用链表数据结构管理Page
free page 空闲页，未被使用
clean page 被使用的page，数据没有修改过
dirty page 脏页，被使用page，数据被修改过，其中数据和磁盘数据产生不一致

- change buffer 更改缓冲区（针对非唯一一二级索引页）
在执行DML语句时，如果这些数据Page没有在Buffer Pool中，不会直接操作磁盘，而会将数据变更存在更改缓冲区change buffer中，在未来数据被读取时，再将数据合并恢复到buffer pool中，再将合并后的数据刷新到磁盘中

意义：与聚集索引不同，二级索引通常是非唯一的，并且以相对随机的顺序插入二级索引（主键聚集索引通常顺序插入），删除和更新可能会影响索引树中不相邻的二级索引页，如果每一次都操作磁盘，会造成大量的磁盘IO，有了Change buffer之后，可以在缓冲池中进行合并处理，减少磁盘IO

- Adaptive Hash Index 自适应hash索引
用于优化对 buffer pool 数据的查询。InnoDB存储引擎会监控对表上个索引页的查询，如果观察到hash索引可以提升速度，则建立hash索引，称之为自适应hash索引 

- log buffer 日志缓冲区
用来保存要写入到磁盘中的log日志数据，默认大小 16MB，定期刷新到磁盘中

磁盘结构 
- 系统表空间 
- 文件表空间
每张表都会生成一个独立的表空间文件
- 通用表空间 
在创建表时，可以指定该表空间
```mysql
create tablespace XXXX add datafile 'file_name' engine=engine_name;

create table XXX... tablespace ts_name;
```
- undo 撤销表空间
mysql实例在初始化时会自动创建两个默认的undo表空间（初始大小16M），用于存储undo log 日志

- 临时表空间
存储临时表

- 双写缓冲区 .dbwlr
 数据页从buffer pool刷新到磁盘前，先将数据页写入双写缓冲区文件中，便于系统异常时恢复数据

- Redo log 重做日志
记录数据页的变化
用来实现事务的持久性
重做日志缓冲（内存）
重做日志文件（磁盘）
当事务提交之后会把所有修改信息存到该日志中，用于再刷新脏页到磁盘时，发生错误时，进行数据恢复使用
WAL（write-Ahead Logging）

后台线程
- master thread
后台核心线程
- io thread
read thread 4个 读操作
write thread 4个 写操作
log thread 1个 将日志缓冲区刷新到磁盘
insert buffer thread 1个 将写缓冲区刷新到磁盘
- purge thread
回收事务已经提交的undo log
- page cleaner thread
协助 matser thread 刷新脏页到磁盘

事务原理：
特性：
原子性：undo log
undo log 回滚日志，用于记录数据被修改前的信息
提供回滚和MVCC
undo log 记录逻辑日志，可以认为当delete一条记录时，undo log中会记录一条对应的insert记录，反之亦然，当update一条记录时，它记录一条对应相反的update记录。当执行rollback时，就可以从undo log中的逻辑记录读取到相应的内容进行回滚 
undo log销毁：undo log在事务执行时产生，事务提交时，并不会立即删除undo log，因为这些日志可能还用于MVCC
undo log存储：undo log采用段的方式进行管理和记录，存放在前面介绍的rollback segment回滚段中，内部包含1024个undo log segment
redo log 记录物理日志
一致性：undo log + redo log
持久性：redo log
redo log 保证持久性
redo log 重做日志

隔离性：锁+MVCC

 

MVCC 多版本并发控制
指维护一个数据的多个版本，使得读写操作没有冲突，快照读为MySQL实现MVCC提供了一个非阻塞读功能。MVCC的具体实现，还需要依赖于数据库记录中的三个隐式字段、undo log日志、readView

- 三个隐式字段：
**DB_TRX_ID**：最近修改事务ID
**DB_ROLL_PTR**：回滚指针，指向这条记录的上一个版本，用于配合undo log，指向数据的上一个版本
DB_ROW_ID：隐藏主键，如果表结构没有指定主键，将生成该字段

当前读

快照读

- undo log 版本链
不同事务或相同事务对同一条记录进行修改，会导致该记录的undo log 生成一条记录版本链表，链表的头部是最新的旧纪录，链表尾部是最早的旧纪录 

- readview
ReadView（读视图）是快照读SQL执行时MVCC提取数据的依据，记录并维护当前活跃的事务（未提交的）id
核心字段：
- m_ids：当前活跃的事务ID集合
- min_trx_id：最小活跃事务ID
- max_trx_id：预分配事务ID，当前最大事务ID+1（因为事务ID是自增的）
- creator_trx_id：ReadView创建者的事务ID 

trx_id：代表当前事务ID 

版本链数据访问规则

RR隔离级别下，仅在事务第一次执行快照读时生成ReadView，后续复用该ReadView










