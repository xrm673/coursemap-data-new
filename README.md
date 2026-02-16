# Cornell 课程数据导入系统

从 Cornell University API 获取课程数据并存储到 AWS RDS MySQL 数据库。

## 项目结构

```
course-map-data/
├── src/
│   ├── models/                    # 数据模型层
│   │   ├── __init__.py
│   │   └── course.py              # Course ORM 模型
│   │
│   ├── repositories/              # 数据访问层
│   │   ├── __init__.py
│   │   └── course_repository.py  # Course 数据访问
│   │
│   ├── services/                  # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── api_service.py         # API 调用
│   │   └── course_service.py      # 课程业务逻辑
│   │
│   ├── database.py                # 数据库连接管理
│   └── main.py                    # 主程序入口
│
├── requirements.txt               # Python 依赖
├── .env.example                   # 环境变量示例
├── .gitignore                     # Git 忽略文件
└── README.md                      # 项目说明
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

复制 `.env.example` 为 `.env` 并填入你的 AWS RDS 信息：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
DB_HOST=your-rds-endpoint.xxxxx.us-east-1.rds.amazonaws.com
DB_PORT=3306
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password
```

### 3. 运行程序

```bash
cd src
python main.py
```

程序会自动：
1. 连接数据库
2. 创建 `courses` 表（如果不存在）
3. 从 Cornell API 获取课程数据
4. 保存到数据库
5. 显示统计和示例查询


## API 说明

Cornell Classes API:
- URL: `https://classes.cornell.edu/api/2.0/search/classes.json`
- 参数：
  - `roster`: 学期代码（如 "SP26" = Spring 2026）
  - `subject`: 学科代码（如 "MATH"）

## 架构说明

### 分层架构

1. **Models（模型层）**
   - 定义数据库表结构
   - 使用 SQLAlchemy ORM

2. **Repositories（数据访问层）**
   - 封装所有数据库操作（CRUD）
   - 提供查询方法

3. **Services（业务逻辑层）**
   - 从 API 获取数据
   - 数据转换和验证
   - 调用 Repository 保存数据

4. **Database（连接管理）**
   - 管理数据库连接
   - 提供 Session
   - 创建表结构

### 优势

- ✅ 职责分离清晰
- ✅ 易于测试和维护
- ✅ 方便扩展新表和功能
- ✅ ORM 自动处理 SQL 和类型转换

## 新增功能 ✨

### 学期追踪和历史学期导入

系统现在支持：
- ✅ 追踪每门课程和注册组的**最后开设学期**
- ✅ 智能判断**历史学期**和**更新学期**
- ✅ 历史学期导入**不覆盖**最新数据，只补充历史课表
- ✅ 支持**乱序导入**（可先导入新学期，再补充旧学期）
- ✅ 快速查询"**3年内开设的课程**"（用于前端筛选）

详细说明请查看 [CHANGELOG.md](CHANGELOG.md)

### 使用示例

```python
# 导入最新学期
stats = course_service.import_courses_from_api("SP26", "MATH")

# 补充历史学期（不会覆盖 SP26 的数据）
stats = course_service.import_courses_from_api("FA25", "MATH")

# 查询 3 年内的课程
from models import Course
recent = session.query(Course).filter(
    Course.last_offered_year >= 2023
).all()
```

更多示例见 [example_usage.py](example_usage.py)

## 自定义使用

修改 `src/main.py` 中的参数来导入不同的课程：

## 依赖说明

- `requests`: HTTP 请求库，用于调用 Cornell API
- `sqlalchemy`: Python ORM 库
- `pymysql`: MySQL 驱动
- `python-dotenv`: 环境变量管理

## 未来扩展

当需要添加更多表（如 EnrollGroups, ClassSections 等）时：

1. 在 `models/` 添加新模型文件
2. 在模型中定义关系（`relationship`）
3. Repository 和 Service 会自动处理关联
4. 现有代码无需大改

## 测试

运行测试验证学期工具函数：
```bash
python test_semester_utils.py
```

## 注意事项

- `.env` 文件包含敏感信息，已加入 `.gitignore`，不会提交到 Git
- 首次运行会自动创建表结构（包括新的 `last_offered_*` 字段）
- 支持重复导入同一学期（幂等操作）
- 历史学期导入不会覆盖最新数据，只补充历史课表信息
