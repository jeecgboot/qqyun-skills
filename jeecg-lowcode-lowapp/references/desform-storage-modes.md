# 数据存储模式

表单设计器支持三种数据存储模式，通过配置切换。

## 配置方式

```yaml
jeecg:
  desform:
    data-factory:
      active: mongo  # sql | mongo | es
```

默认值：`mongo`（未配置时）

## 三种模式对比

| 维度 | SQL | MongoDB（默认） | Elasticsearch |
|------|-----|---------|---------------|
| 存储位置 | `design_form_data` 表 | `desform_data_{code}` 集合 | `desform_{code}` 索引 |
| 数据一致性 | 强（ACID） | 最终一致 | 最终一致 |
| 查询灵活性 | 中 | 高 | 搜索优秀 |
| 扩展性 | 低 | 高 | 高 |
| 适用场景 | 传统ERP、强一致 | 通用场景 | 搜索密集 |

## 切换注意事项

- 模式切换需要数据迁移，不能热切换
- SQL 模式时会加载 MockMongoTemplate 避免依赖报错
- 通过 Spring `@Conditional` 注解实现条件化 Bean 注册
