# pgvector RAG 安装和使用教程

这份教程面向正在学习 RAG（Retrieval-Augmented Generation，检索增强生成）的开发者。重点不是把 pgvector 当成一个孤立数据库扩展来学，而是理解它在 RAG 系统里承担的职责：保存文本块的 embedding 向量，并按语义相似度快速检索相关内容。

一句话理解：

```text
PostgreSQL 负责存业务数据，pgvector 让 PostgreSQL 也能存向量、查相似向量。
```

在一个最小 RAG 系统中，pgvector 通常处在这个位置：

```text
原始文档
  -> 文档解析
  -> 文本切分 chunk
  -> embedding 模型生成向量
  -> PostgreSQL + pgvector 保存 chunk 和向量
  -> 用户问题生成 query 向量
  -> pgvector 相似度检索 Top K
  -> 把检索结果拼进 Prompt
  -> LLM 生成答案
```

---

## 目录

- [1. 你需要先掌握什么](#1-你需要先掌握什么)
- [2. 安装方式选择](#2-安装方式选择)
- [3. 使用 Docker 快速启动 pgvector](#3-使用-docker-快速启动-pgvector)
- [4. 连接数据库并启用 pgvector](#4-连接数据库并启用-pgvector)
- [5. 第一个 pgvector 表](#5-第一个-pgvector-表)
- [6. RAG 推荐表结构](#6-rag-推荐表结构)
- [7. RAG 入库流程](#7-rag-入库流程)
- [8. RAG 检索 SQL](#8-rag-检索-sql)
- [9. pgvector 索引](#9-pgvector-索引)
- [10. 索引和过滤的注意点](#10-索引和过滤的注意点)
- [11. 最小 Java 示例](#11-最小-java-示例)
- [12. 最小 Python 示例](#12-最小-python-示例)
- [13. Java 项目中的使用思路](#13-java-项目中的使用思路)
- [14. Prompt 组装示例](#14-prompt-组装示例)
- [15. 学习阶段推荐练习](#15-学习阶段推荐练习)
- [16. 常见问题](#16-常见问题)
- [17. RAG 使用 pgvector 的关键经验](#17-rag-使用-pgvector-的关键经验)
- [18. 最小验收清单](#18-最小验收清单)
- [19. 官方资料](#19-官方资料)

---

## 1. 你需要先掌握什么

学习 pgvector 前，建议先知道下面几个概念。

### 1.1 Embedding

Embedding 是把文本、图片、代码等内容转换成一组浮点数向量。

例如一句话：

```text
什么是 RAG？
```

经过 embedding 模型后，可能变成：

```text
[0.012, -0.232, 0.871, ...]
```

真实向量维度由 embedding 模型决定，常见维度有 384、768、1024、1536、3072 等。建表时必须让 `vector(n)` 的 `n` 和模型输出维度一致。

可以把 embedding 向量先理解成一个固定长度的数字数组：

```text
一段文本 -> embedding 模型 -> 一组数字
```

例如：

```text
"RAG 是什么？" -> [0.012, -0.232, 0.871, ...]
```

pgvector 做的事情，就是让 PostgreSQL 可以把这组数字作为一个专门的 `vector` 类型保存下来，并且可以直接比较两个 `vector` 谁更接近。

### 1.2 相似度检索

RAG 检索时，不是简单按关键词匹配，而是比较两个向量的距离。

常见距离或相似度：

| 方式 | pgvector 操作符 | 适合场景 |
| --- | --- | --- |
| L2 欧氏距离 | `<->` | 通用向量距离 |
| Inner Product 内积 | `<#>` | 模型明确要求内积检索时 |
| Cosine 余弦距离 | `<=>` | 文本 embedding 常用 |
| L1 曼哈顿距离 | `<+>` | 少数特殊场景 |

RAG 文本检索里，最常用的是余弦距离。

---

## 2. 安装方式选择

学习阶段推荐用 Docker，因为环境最干净。

生产环境可以选择：

- Docker 镜像
- Linux APT/Yum 包
- macOS Homebrew
- 源码编译安装
- 云数据库中已经内置 pgvector 的 PostgreSQL 服务

本教程默认使用 Docker。

---

## 3. 使用 Docker 快速启动 pgvector

### 3.1 单条命令启动

```bash
docker run --name rag-postgres \
  -e POSTGRES_USER=rag \
  -e POSTGRES_PASSWORD=ragpass \
  -e POSTGRES_DB=ragdb \
  -p 5432:5432 \
  -d pgvector/pgvector:pg18
```

说明：

- `rag-postgres`：容器名
- `rag`：数据库用户名
- `ragpass`：数据库密码
- `ragdb`：数据库名
- `5432`：PostgreSQL 默认端口
- `pgvector/pgvector:pg18`：带 pgvector 扩展的 PostgreSQL 镜像

如果本机已经有 PostgreSQL 占用了 5432，可以改成：

```bash
-p 15432:5432
```

这样本机连接端口就是 `15432`。

### 3.2 Docker Compose 写法

如果你在做 RAG 项目，推荐用 `docker-compose.yml` 管理数据库。

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg18
    container_name: rag-postgres
    environment:
      POSTGRES_USER: rag
      POSTGRES_PASSWORD: ragpass
      POSTGRES_DB: ragdb
    ports:
      - "5432:5432"
    volumes:
      - rag_postgres_data:/var/lib/postgresql/data

volumes:
  rag_postgres_data:
```

启动：

```bash
docker compose up -d
```

查看容器：

```bash
docker ps
```

停止：

```bash
docker compose down
```

如果想连数据一起删掉：

```bash
docker compose down -v
```

---

## 4. 连接数据库并启用 pgvector

进入容器：

```bash
docker exec -it rag-postgres psql -U rag -d ragdb
```

启用扩展：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

检查是否安装成功：

```sql
SELECT extname, extversion
FROM pg_extension
WHERE extname = 'vector';
```

如果能看到 `vector`，说明 pgvector 已经启用。

注意：pgvector 的扩展名叫 `vector`，不是 `pgvector`。

---

## 5. 第一个 pgvector 表

先用 3 维向量演示，便于理解。

这里的 `3` 不是 pgvector 固定要求，也不是 RAG 固定要求。它只是为了教程演示方便，因为 3 个数字可以直接手写出来。

真实项目里，向量维度由 embedding 模型决定：

| embedding 模型输出 | 数据库字段应该写成 |
| --- | --- |
| 每段文本输出 384 个数字 | `vector(384)` |
| 每段文本输出 768 个数字 | `vector(768)` |
| 每段文本输出 1536 个数字 | `vector(1536)` |
| 每段文本输出 3072 个数字 | `vector(3072)` |

核心规则：

```text
vector(n) 里的 n 必须等于 embedding 模型实际返回的数字个数。
```

```sql
DROP TABLE IF EXISTS items;

CREATE TABLE items (
  -- id 是主键，每插入一行会自动递增
  id bigserial PRIMARY KEY,

  -- content 保存原始文本。RAG 最终要把这段文本交给大模型作为上下文
  content text NOT NULL,

  -- embedding 保存 content 对应的向量
  -- vector(3) 表示这个字段只能保存 3 维向量，也就是正好 3 个数字
  -- NOT NULL 表示每一行都必须有向量，不能是空值
  embedding vector(3) NOT NULL
);
```

把这一行拆开看：

```sql
embedding vector(3) NOT NULL
```

含义是：

| 部分 | 含义 |
| --- | --- |
| `embedding` | 字段名，用来保存文本向量 |
| `vector` | pgvector 提供的数据类型 |
| `(3)` | 向量维度，表示必须正好有 3 个数字 |
| `NOT NULL` | 不允许为空 |

所以 `vector(3)` 可以插入：

```sql
'[0.10, 0.20, 0.30]'
```

不能插入 2 维：

```sql
'[0.10, 0.20]'
```

也不能插入 4 维：

```sql
'[0.10, 0.20, 0.30, 0.40]'
```

原因是表结构已经声明了 `embedding vector(3)`，数据库会检查向量维度是否正好等于 3。

插入几条数据：

```sql
INSERT INTO items (content, embedding) VALUES
  ('RAG 是检索增强生成', '[0.10, 0.20, 0.30]'),
  ('向量数据库可以做语义检索', '[0.11, 0.19, 0.29]'),
  ('PostgreSQL 是关系型数据库', '[0.90, 0.10, 0.10]');
```

查询最相似的 2 条：

```sql
SELECT
  id,
  content,
  -- <=> 表示余弦距离。距离越小，文本语义越接近
  embedding <=> '[0.10, 0.21, 0.31]' AS cosine_distance
FROM items
-- 按距离从小到大排序，最相似的排在前面
ORDER BY embedding <=> '[0.10, 0.21, 0.31]'
LIMIT 2;
```

距离越小，表示越相似。

这个查询可以读成：

```text
拿查询向量 [0.10, 0.21, 0.31]
和每一行的 embedding 做余弦距离计算，
按距离从小到大排序，
取最接近的 2 条文本。
```

在真实 RAG 里，`'[0.10, 0.21, 0.31]'` 不会手写，而是由 embedding 模型根据用户问题生成。

---

## 6. RAG 推荐表结构

实际 RAG 项目里，不建议只建一张简单向量表。至少要能保存：

- 文档信息
- chunk 文本
- chunk 的向量
- 元数据
- 来源定位信息

下面是一套适合入门项目的表结构。

### 6.1 文档表

```sql
CREATE TABLE rag_documents (
  -- 文档 id，一篇原始文档对应一条记录
  id bigserial PRIMARY KEY,

  -- 文档标题，用于展示引用来源
  title text NOT NULL,

  -- 文档来源类型，例如 file、url、notion、database
  source_type text NOT NULL DEFAULT 'file',

  -- 文档来源地址，例如文件路径、网页 URL、对象存储地址
  source_uri text,

  -- 文档级元数据，适合保存分类、作者、部门、权限标签等
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,

  -- 入库时间
  created_at timestamptz NOT NULL DEFAULT now()
);
```

字段说明：

| 字段 | 含义 |
| --- | --- |
| `title` | 文档标题 |
| `source_type` | 来源类型，如 `file`、`url`、`notion`、`database` |
| `source_uri` | 文件路径、URL 或业务系统标识 |
| `metadata` | 额外元数据，如作者、部门、权限标签 |

### 6.2 文本块表

假设你的 embedding 模型输出 1536 维向量：

```sql
CREATE TABLE rag_chunks (
  -- chunk id，一个文本块对应一条记录
  id bigserial PRIMARY KEY,

  -- 属于哪一篇文档。文档删除时，对应 chunk 也会自动删除
  document_id bigint NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,

  -- 当前 chunk 在原文档中的序号，通常从 0 或 1 开始
  chunk_index int NOT NULL,

  -- chunk 原文。检索命中后，要把这个字段放进 Prompt
  content text NOT NULL,

  -- chunk 对应的 embedding 向量
  -- vector(1536) 表示必须存 1536 维向量
  -- 这里的 1536 只是示例，必须改成你的 embedding 模型实际维度
  embedding vector(1536) NOT NULL,

  -- 可选：chunk 大约包含多少 token，便于控制 Prompt 长度
  token_count int,

  -- chunk 级元数据，例如页码、章节、标题路径、权限标签等
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,

  -- chunk 入库时间
  created_at timestamptz NOT NULL DEFAULT now(),

  -- 同一篇文档里，不允许出现重复 chunk_index
  UNIQUE (document_id, chunk_index)
);
```

如果你的模型输出不是 1536 维，要改这里：

```sql
embedding vector(1536)
```

例如 768 维模型：

```sql
embedding vector(768)
```

判断维度的方法很简单：调用一次 embedding 接口，看返回数组长度是多少。

如果返回结果像这样：

```json
[0.01, 0.02, 0.03]
```

长度是 3，就对应 `vector(3)`。

如果返回数组里有 1536 个数字，就对应 `vector(1536)`。

---

## 7. RAG 入库流程

RAG 入库不是把整篇文档直接塞进向量库，而是拆成多个 chunk。

推荐流程：

```text
1. 读取文档
2. 清洗文本
3. 按段落或 token 长度切分 chunk
4. 为每个 chunk 调 embedding 模型
5. 将 chunk 文本、向量、来源信息写入 rag_chunks
```

示例插入文档：

```sql
INSERT INTO rag_documents (title, source_type, source_uri, metadata)
VALUES (
  'RAG 入门教程',
  'file',
  '/docs/rag-intro.md',
  '{"category": "ai", "author": "demo"}'
)
RETURNING id;
```

假设返回的文档 id 是 `1`，插入 chunk：

```sql
INSERT INTO rag_chunks (
  document_id,
  chunk_index,
  content,
  embedding,
  token_count,
  metadata
) VALUES (
  1,
  0,
  'RAG 是一种把外部知识库和大语言模型结合起来的工程方案。',
  '[0.01, 0.02, 0.03, ...]',
  32,
  '{"page": 1, "section": "intro"}'
);
```

注意：上面的 `...` 只是说明，真实 SQL 里必须传完整向量。

如果表字段是 `embedding vector(1536)`，那么这里必须传 1536 个数字，不能只传 3 个数字。

---

## 8. RAG 检索 SQL

用户提问后，先把问题也转成 query embedding，然后在数据库中找最接近的 chunk。

### 8.1 基础 Top K 检索

```sql
SELECT
  c.id,
  c.document_id,
  d.title,
  c.content,
  c.metadata,
  -- 计算数据库中 chunk 向量和用户问题向量之间的余弦距离
  c.embedding <=> :query_embedding AS distance
FROM rag_chunks c
JOIN rag_documents d ON d.id = c.document_id
-- 距离越小越相似，所以升序排列
ORDER BY c.embedding <=> :query_embedding
-- 只取最相似的 5 个 chunk
LIMIT 5;
```

`:query_embedding` 是应用程序传入的向量参数。

它不是 SQL 固定语法，而是很多应用框架里的“命名参数”写法。实际执行前，应用程序会把它替换成用户问题对应的向量。

例如用户问：

```text
pgvector 在 RAG 中有什么作用？
```

应用程序会先调用 embedding 模型，把问题转成向量：

```text
[0.04, -0.12, 0.88, ...]
```

然后再把这个向量作为 `:query_embedding` 传给 SQL。

如果你是在 `psql` 里手动测试，不要直接复制 `:query_embedding`，要换成真实完整向量。

例如测试第 5 章的 `items` 表时，可以写：

```sql
ORDER BY embedding <=> '[0.10, 0.21, 0.31]'
```

如果测试的是 `embedding vector(1536)` 的真实 RAG 表，就必须传 1536 个数字。SQL 里不能写 `...` 代替省略部分。

### 8.2 带相似度分数

余弦距离越小越相似。为了更容易看，可以换算成相似度：

```sql
SELECT
  c.id,
  d.title,
  c.content,
  -- cosine distance 越小越相似
  -- 这里用 1 - distance 粗略转换成 similarity，数值越大越相似
  1 - (c.embedding <=> :query_embedding) AS similarity
FROM rag_chunks c
JOIN rag_documents d ON d.id = c.document_id
ORDER BY c.embedding <=> :query_embedding
LIMIT 5;
```

### 8.3 加相似度阈值

如果距离太大，说明检索结果可能不相关，可以过滤掉。

```sql
WITH results AS (
  SELECT
    c.id,
    d.title,
    c.content,
    -- 先取一批候选结果，并计算每条结果的距离
    c.embedding <=> :query_embedding AS distance
  FROM rag_chunks c
  JOIN rag_documents d ON d.id = c.document_id
  ORDER BY c.embedding <=> :query_embedding
  LIMIT 20
)
SELECT *
FROM results
-- 过滤掉距离过大的结果。0.35 只是示例阈值，需要结合业务调试
WHERE distance < 0.35
ORDER BY distance
LIMIT 5;
```

阈值没有固定标准，需要结合你的 embedding 模型和数据集调试。

### 8.4 按元数据过滤

例如只检索 `category = ai` 的文档：

```sql
SELECT
  c.id,
  d.title,
  c.content,
  c.embedding <=> :query_embedding AS distance
FROM rag_chunks c
JOIN rag_documents d ON d.id = c.document_id
-- 先按文档元数据过滤，再在过滤后的数据里做向量排序
WHERE d.metadata->>'category' = 'ai'
ORDER BY c.embedding <=> :query_embedding
LIMIT 5;
```

如果你要做企业知识库，权限过滤通常也写在 `WHERE` 条件里。

---

## 9. pgvector 索引

没有索引时，PostgreSQL 会逐行计算向量距离。数据量小的时候没问题，数据量大后会慢。

pgvector 常用近似向量索引：

- HNSW
- IVFFlat

学习 RAG 时，建议优先从 HNSW 开始。

### 9.1 HNSW 索引

HNSW 查询效果通常比较好，而且不要求先有数据再建索引。

```sql
CREATE INDEX rag_chunks_embedding_hnsw_idx
ON rag_chunks
-- hnsw 表示使用 HNSW 近似向量索引
-- vector_cosine_ops 表示这个索引用来配合余弦距离检索
USING hnsw (embedding vector_cosine_ops);
```

适合余弦距离：

```sql
ORDER BY embedding <=> :query_embedding
```

如果你使用 L2 距离，则索引操作类改成：

```sql
vector_l2_ops
```

如果你使用内积，则改成：

```sql
vector_ip_ops
```

### 9.2 HNSW 参数

建索引时可以设置：

```sql
CREATE INDEX rag_chunks_embedding_hnsw_idx
ON rag_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

查询时可以设置：

```sql
SET hnsw.ef_search = 100;
```

大致理解：

| 参数 | 含义 | 影响 |
| --- | --- | --- |
| `m` | 图中每个节点的连接数 | 越大召回越好，索引越大 |
| `ef_construction` | 建索引时搜索范围 | 越大构建越慢，召回可能更好 |
| `hnsw.ef_search` | 查询时搜索范围 | 越大查询越慢，召回越好 |

入门阶段可以先用默认值，等数据量上来再调。

### 9.3 IVFFlat 索引

IVFFlat 会把向量分成多个 list，查询时只扫描一部分 list。

```sql
CREATE INDEX rag_chunks_embedding_ivfflat_idx
ON rag_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

查询前可以设置扫描 list 数：

```sql
SET ivfflat.probes = 10;
```

大致理解：

| 参数 | 含义 | 影响 |
| --- | --- | --- |
| `lists` | 建索引时分成多少个列表 | 越大索引更细，但需要更多数据 |
| `ivfflat.probes` | 查询时扫描多少个列表 | 越大召回越好，查询越慢 |

IVFFlat 一般建议在已经有一定数据量后再建索引。

---

## 10. 索引和过滤的注意点

在 RAG 中，经常会同时做向量检索和权限过滤。例如：

```sql
WHERE tenant_id = 1001
ORDER BY embedding <=> :query_embedding
LIMIT 5
```

近似向量索引通常是先按向量索引找候选，再应用过滤条件。过滤条件很严格时，最终返回的结果可能少于 `LIMIT`。

可以考虑：

### 10.1 给过滤字段建普通索引

```sql
CREATE INDEX rag_documents_category_idx
ON rag_documents ((metadata->>'category'));
```

### 10.2 使用部分索引

如果某类数据经常被查，可以建部分向量索引：

```sql
CREATE INDEX rag_chunks_ai_hnsw_idx
ON rag_chunks
USING hnsw (embedding vector_cosine_ops)
WHERE metadata->>'category' = 'ai';
```

### 10.3 开启 iterative scan

pgvector 0.8.0 起支持 iterative index scans，可以在过滤导致结果不足时扫描更多索引结果。

```sql
SET hnsw.iterative_scan = relaxed_order;
```

或者：

```sql
SET hnsw.iterative_scan = strict_order;
```

`strict_order` 保证距离排序更严格，`relaxed_order` 可能召回更好但排序略微放松。

---

## 11. 最小 Java 示例

这一节用最朴素的 JDBC 演示 pgvector。先不使用 Spring AI、LangChain4j 或 ORM，这样你能清楚看到 Java 程序到底向 PostgreSQL 发送了什么 SQL。

这个示例仍然使用 `vector(3)`，只是为了方便手写 3 个数字。真实 RAG 项目要改成 embedding 模型的实际维度，例如 `vector(768)` 或 `vector(1536)`。

### 11.1 Maven 依赖

只需要 PostgreSQL JDBC 驱动即可。

如果你使用 Spring Boot，一般可以让 Spring Boot 依赖管理接管版本：

```xml
<dependency>
  <groupId>org.postgresql</groupId>
  <artifactId>postgresql</artifactId>
</dependency>
```

如果你不是 Spring Boot 项目，需要自己补上 `version`，版本选择你项目中合适的稳定版本。

### 11.2 Java 完整示例

下面代码使用了 Java 文本块 `"""`，适合 Java 15+。如果你还在用 Java 8，需要把多行 SQL 改成普通字符串拼接。

```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.Locale;

public class PgvectorJdbcDemo {

    private static final String JDBC_URL = "jdbc:postgresql://localhost:5432/ragdb";
    private static final String USERNAME = "rag";
    private static final String PASSWORD = "ragpass";

    public static void main(String[] args) throws Exception {
        try (Connection connection = DriverManager.getConnection(JDBC_URL, USERNAME, PASSWORD)) {
            createTable(connection);
            insertDemoRows(connection);
            searchSimilarChunks(connection);
        }
    }

    private static void createTable(Connection connection) throws Exception {
        try (Statement statement = connection.createStatement()) {
            // 启用 pgvector 扩展。扩展名是 vector，不是 pgvector
            statement.execute("CREATE EXTENSION IF NOT EXISTS vector");

            // vector(3) 表示 embedding 字段只能保存 3 维向量
            // 真实 RAG 项目要改成你的 embedding 模型维度，例如 vector(1536)
            statement.execute("""
                CREATE TABLE IF NOT EXISTS demo_java_chunks (
                  id bigserial PRIMARY KEY,
                  content text NOT NULL,
                  embedding vector(3) NOT NULL
                )
                """);

            statement.execute("TRUNCATE demo_java_chunks");
        }
    }

    private static void insertDemoRows(Connection connection) throws Exception {
        String sql = "INSERT INTO demo_java_chunks (content, embedding) VALUES (?, CAST(? AS vector))";

        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            insertOne(statement, "RAG 是检索增强生成", new float[] {0.10f, 0.20f, 0.30f});
            insertOne(statement, "pgvector 可以在 PostgreSQL 中保存向量", new float[] {0.11f, 0.19f, 0.28f});
            insertOne(statement, "今天的天气不错", new float[] {0.80f, 0.10f, 0.10f});
        }
    }

    private static void insertOne(PreparedStatement statement, String content, float[] embedding) throws Exception {
        statement.setString(1, content);

        // pgvector 可以接收 "[0.10,0.20,0.30]" 这种字符串格式
        // CAST(? AS vector) 会把字符串转换成 PostgreSQL 里的 vector 类型
        statement.setString(2, toPgvectorString(embedding));

        statement.executeUpdate();
    }

    private static void searchSimilarChunks(Connection connection) throws Exception {
        // 用户问题对应的向量。真实项目里，这个向量应该来自同一个 embedding 模型
        float[] queryEmbedding = new float[] {0.10f, 0.21f, 0.29f};
        String queryVector = toPgvectorString(queryEmbedding);

        String sql = """
            SELECT
              content,
              embedding <=> CAST(? AS vector) AS distance
            FROM demo_java_chunks
            ORDER BY embedding <=> CAST(? AS vector)
            LIMIT ?
            """;

        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, queryVector);
            statement.setString(2, queryVector);
            statement.setInt(3, 2);

            try (ResultSet resultSet = statement.executeQuery()) {
                while (resultSet.next()) {
                    String content = resultSet.getString("content");
                    double distance = resultSet.getDouble("distance");

                    // distance 越小，表示语义越接近
                    System.out.printf(Locale.US, "%.6f  %s%n", distance, content);
                }
            }
        }
    }

    private static String toPgvectorString(float[] values) {
        StringBuilder builder = new StringBuilder("[");

        for (int i = 0; i < values.length; i++) {
            if (i > 0) {
                builder.append(",");
            }
            builder.append(Float.toString(values[i]));
        }

        return builder.append("]").toString();
    }
}
```

### 11.3 这段 Java 代码在做什么

关键点有 4 个：

| 代码 | 含义 |
| --- | --- |
| `CREATE EXTENSION IF NOT EXISTS vector` | 在当前数据库启用 pgvector |
| `embedding vector(3)` | 创建一个 3 维向量字段 |
| `CAST(? AS vector)` | 把 Java 传入的字符串参数转换成 pgvector 向量 |
| `embedding <=> CAST(? AS vector)` | 计算数据库向量和查询向量的余弦距离 |

Java 里这段：

```java
new float[] {0.10f, 0.21f, 0.29f}
```

在真实 RAG 项目中，不应该手写。它应该来自 embedding 模型。

例如真实链路是：

```text
用户问题
  -> 调 embedding 模型
  -> 得到 float[] 或 List<Double>
  -> 转成 "[0.01,0.02,...]" 格式
  -> 传给 SQL 的 CAST(? AS vector)
  -> pgvector 做相似度检索
```

如果你的表是 `embedding vector(1536)`，那么 `float[]` 必须正好有 1536 个数字。

---

## 12. 最小 Python 示例

安装依赖：

```bash
pip install psycopg[binary] pgvector numpy
```

示例代码：

```python
import numpy as np
import psycopg
from pgvector.psycopg import register_vector

conn = psycopg.connect(
    "postgresql://rag:ragpass@localhost:5432/ragdb",
    autocommit=True,
)

conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
register_vector(conn)

conn.execute("""
CREATE TABLE IF NOT EXISTS demo_chunks (
  -- id 是主键
  id bigserial PRIMARY KEY,

  -- content 是原文
  content text NOT NULL,

  -- 这里仍然用 vector(3) 做演示
  -- 真实 RAG 项目要改成模型输出维度，例如 vector(768) 或 vector(1536)
  embedding vector(3) NOT NULL
)
""")

conn.execute("TRUNCATE demo_chunks")

rows = [
    # 每条数据包含：文本 + 这段文本对应的 3 维向量
    ("RAG 是检索增强生成", np.array([0.10, 0.20, 0.30])),
    ("pgvector 可以在 PostgreSQL 中保存向量", np.array([0.11, 0.19, 0.28])),
    ("今天的天气不错", np.array([0.80, 0.10, 0.10])),
]

for content, embedding in rows:
    conn.execute(
        "INSERT INTO demo_chunks (content, embedding) VALUES (%s, %s)",
        (content, embedding),
    )

# 用户问题对应的向量。真实项目里，这个向量来自 embedding 模型
query_embedding = np.array([0.10, 0.21, 0.29])

results = conn.execute(
    """
    SELECT content, embedding <=> %s AS distance
    FROM demo_chunks
    -- 距离越小，语义越接近
    ORDER BY embedding <=> %s
    LIMIT 2
    """,
    (query_embedding, query_embedding),
).fetchall()

for content, distance in results:
    print(distance, content)
```

真实 RAG 项目里，`query_embedding` 和每个 chunk 的 `embedding` 都应该来自同一个 embedding 模型。

---

## 13. Java 项目中的使用思路

Java 后端做 RAG 时，pgvector 通常有两种使用方式。

### 13.1 直接用 SQL

这是最容易理解底层原理的方式。

```sql
SELECT
  c.id,
  c.content,
  c.embedding <=> CAST(? AS vector) AS distance
FROM rag_chunks c
ORDER BY c.embedding <=> CAST(? AS vector)
LIMIT ?;
```

Java 侧可以把 embedding 数组转成 pgvector 字符串格式：

```text
[0.01,0.02,0.03]
```

再作为参数传入。

适合学习阶段，因为你能清楚看到 RAG 检索到底执行了什么 SQL。

### 13.2 使用框架封装

如果你使用 Spring AI、LangChain4j 等框架，通常可以直接配置 PGVector 向量存储。

学习建议：

```text
先手写 SQL 跑通
再使用框架封装
最后再做混合检索、重排序和权限控制
```

否则很容易只会调用框架 API，但不知道召回质量不好时该怎么排查。

---

## 14. Prompt 组装示例

pgvector 检索出来的是 chunk，不是最终答案。RAG 还需要把 chunk 拼进 Prompt。

示例：

```text
你是一个知识库问答助手。请只根据提供的资料回答问题。
如果资料中没有答案，请说“资料中没有找到相关信息”。

资料：
[1] RAG 是一种把外部知识库和大语言模型结合起来的工程方案。
[2] pgvector 可以在 PostgreSQL 中保存向量，并按相似度检索文本块。

问题：
pgvector 在 RAG 中有什么作用？
```

模型可能回答：

```text
pgvector 在 RAG 中用于保存文本块的向量表示，并根据用户问题的向量进行相似度检索，找出最相关的上下文资料供大语言模型生成答案。
```

---

## 15. 学习阶段推荐练习

### 练习 1：跑通 pgvector

目标：

```text
能启动 PostgreSQL + pgvector，并执行 CREATE EXTENSION vector。
```

验收 SQL：

```sql
SELECT extname, extversion
FROM pg_extension
WHERE extname = 'vector';
```

### 练习 2：手写向量检索

目标：

```text
能创建 vector(3) 表，插入 3 条数据，按余弦距离查 Top 2。
```

这里的 `vector(3)` 仍然只是练习用的最小维度，不代表真实 RAG 项目只能使用 3 维向量。

验收 SQL：

```sql
SELECT content
FROM items
ORDER BY embedding <=> '[0.10, 0.21, 0.31]'
LIMIT 2;
```

### 练习 3：改成真实 embedding 维度

目标：

```text
把 vector(3) 改成你的 embedding 模型维度，例如 vector(768) 或 vector(1536)。
```

关键点：

```text
表字段维度必须等于 embedding 模型输出维度。
```

### 练习 4：做一个最小 RAG 检索器

目标：

```text
输入一个问题 -> 生成问题向量 -> 查询 Top 5 chunk -> 打印 chunk 内容。
```

先不接 LLM 也可以。只要能检索出相关 chunk，就已经完成 RAG 的核心检索部分。

### 练习 5：加 HNSW 索引

目标：

```text
给 embedding 字段创建 HNSW 索引，并比较建索引前后的查询计划。
```

查看查询计划：

```sql
EXPLAIN ANALYZE
SELECT content
FROM rag_chunks
ORDER BY embedding <=> :query_embedding
LIMIT 5;
```

---

## 16. 常见问题

### 16.1 `type "vector" does not exist`

原因通常是没有启用扩展。

执行：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

如果仍然失败，说明 PostgreSQL 实例里没有安装 pgvector，需要先安装扩展包或换用 pgvector Docker 镜像。

### 16.2 向量维度不匹配

例如表是：

```sql
embedding vector(1536)
```

但插入了 768 维向量，就会报错。

解决方法：

```text
确认 embedding 模型输出维度，并让 vector(n) 的 n 与它一致。
```

### 16.3 为什么查出来的内容不相关

常见原因：

- chunk 切分太大或太小
- embedding 模型不适合中文或你的业务领域
- query 和文档使用了不同 embedding 模型
- 相似度阈值设置不合理
- Top K 太小
- 文档清洗质量差
- 没有做混合检索或重排序

### 16.4 有了 pgvector，还需要 Elasticsearch 吗

看需求。

pgvector 擅长语义检索。Elasticsearch/OpenSearch 擅长关键词检索、倒排索引、复杂文本过滤和高亮。

很多生产 RAG 系统会做混合检索：

```text
向量检索 pgvector + 关键词检索 Elasticsearch/PostgreSQL full-text search + reranker
```

学习阶段先把 pgvector 跑通即可。

### 16.5 数据量多大时需要索引

没有绝对标准。

粗略建议：

- 几千条 chunk：可以先不建索引，直接精确搜索
- 几万到几十万条 chunk：建议建 HNSW
- 百万级以上：需要认真评估索引参数、过滤条件、分区、召回率和延迟

---

## 17. RAG 使用 pgvector 的关键经验

### 17.1 chunk 文本要和向量一起保存

不要只保存向量。LLM 最终需要的是文本上下文。

推荐字段：

```sql
content text NOT NULL,
embedding vector(1536) NOT NULL
```

### 17.2 保存来源信息

RAG 答案应该能追溯来源。

推荐保存：

- 文档 id
- 文档标题
- 页码
- 章节
- URL
- chunk 序号

### 17.3 query 和 document 必须使用同一个 embedding 模型

文档入库时用模型 A，用户问题也必须用模型 A。

否则向量空间不一致，检索结果会不稳定。

### 17.4 不要一开始就追求复杂架构

学习顺序建议：

```text
pgvector 基础 SQL
  -> RAG 表设计
  -> 文档 chunk 入库
  -> Top K 检索
  -> Prompt 组装
  -> HNSW 索引
  -> 元数据过滤
  -> 混合检索
  -> reranker
```

---

## 18. 最小验收清单

如果你能独立完成下面这些事，就说明 pgvector 的 RAG 基础已经入门：

- 能用 Docker 启动 pgvector PostgreSQL
- 能执行 `CREATE EXTENSION vector`
- 能创建 `embedding vector(n)` 字段
- 能插入文本和向量
- 能用 `<=>` 做余弦距离检索
- 能设计 `documents` 和 `chunks` 两张表
- 能把用户问题转成向量并查 Top K chunk
- 能把 chunk 拼进 Prompt
- 能创建 HNSW 索引
- 能解释为什么检索结果不相关

---

## 19. 官方资料

- pgvector GitHub 仓库和官方 README：https://github.com/pgvector/pgvector
- pgvector Docker 镜像：https://hub.docker.com/r/pgvector/pgvector
- pgvector Python 客户端：https://github.com/pgvector/pgvector-python
