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

#### 查看帮助
```bash
python src/main.py --help
```

#### 基本用法

**重建表 + 导入指定学期的所有课程：**
```bash
python src/main.py --reset --semester SP26
```

**增量更新指定学期：**
```bash
python src/main.py --semester FA26
```

**只导入指定学科：**
```bash
python src/main.py --semester SP26 --subjects INFO CS MATH
```

**跳过 Combined Groups 解析（加快速度）：**
```bash
python src/main.py --semester SP26 --skip-combined
```

#### 命令行参数说明

| 参数 | 必需 | 说明 | 示例 |
|------|------|------|------|
| `--semester` | ✅ | 学期代码 | `SP26`, `FA25`, `WI26` |
| `--reset` | ❌ | 重建数据库表（警告：删除所有数据） | - |
| `--subjects` | ❌ | 指定要导入的学科列表 | `INFO CS MATH` |
| `--skip-combined` | ❌ | 跳过 Combined Groups 解析 | - |

#### 执行流程

程序会自动：
1. 连接数据库
2. 创建/重建数据表
3. 初始化 Subject 数据（从 API 获取所有学科）
4. 导入课程数据（所有学科或指定学科）
5. 解析 Combined Course 关系（可选）


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

### 增量更新架构

系统现在支持智能增量更新：
- ✅ **EnrollGroup 和 ClassSection ID 稳定** - 不会因重复导入而改变
- ✅ **智能匹配** - 自动识别现有记录并更新
- ✅ **只更新必要字段** - 如 `open_status`（选课状态）
- ✅ **保护用户数据** - 用户选课记录不受影响

### Combined Courses

系统自动处理课程组合关系：
- ✅ **自动匹配** - 按 topic 和 section 匹配 combined courses
- ✅ **支持多课程组合** - 使用 Union-Find 算法处理 A-B-C 关系
- ✅ **分组管理** - 所有 combined 的 EnrollGroup 归入同一组

### Subject 管理

系统自动管理所有学科：
- ✅ **自动获取** - 从 Cornell API 获取 200+ 个学科
- ✅ **外键关系** - Course 与 Subject 建立外键关系
- ✅ **避免重复** - 已存在的 Subject 自动跳过

### 学期追踪和历史学期导入

系统支持：
- ✅ 追踪每门课程的**最后开设学期**
- ✅ 智能判断**历史学期**和**更新学期**
- ✅ 历史学期导入**不覆盖**最新数据
- ✅ 支持**乱序导入**（可先导入新学期，再补充旧学期）

### 使用场景

#### 场景 1: 首次部署（完整导入）
```bash
python src/main.py --reset --semester SP26
```
导入 SP26 所有学科的课程（200+ 学科，预计 15-30 分钟）

#### 场景 2: 快速测试
```bash
python src/main.py --reset --semester SP26 --subjects INFO CS MATH
```
只导入 3 个学科进行测试（预计 1-2 分钟）

#### 场景 3: 每日增量更新
```bash
python src/main.py --semester SP26
```
更新所有课程的最新信息（如选课状态）

#### 场景 4: 快速刷新
```bash
python src/main.py --semester SP26 --skip-combined
```
跳过 combined 解析，加快更新速度

#### 场景 5: 切换学期
```bash
python src/main.py --semester FA26
```
导入新学期的课程数据

## 数据库结构

系统包含以下数据表：

- **subjects** - 学科表（INFO, CS, MATH 等）
- **courses** - 课程表
- **course_attributes** - 课程属性（分配类别等）
- **enroll_groups** - 注册组（每学期的课程实例）
- **class_sections** - 班级（LEC, DIS, LAB 等）
- **meetings** - 上课时间和地点
- **instructors** - 教师信息
- **meeting_instructors** - Meeting 和 Instructor 的关联
- **combined_groups** - Combined Course 分组

详细的表结构和关系请查看 `src/models/` 目录。

## 自定义使用

修改命令行参数来导入不同的课程（见上方"运行程序"部分）。

或者在代码中使用：

```python
from database import Database
from repositories import CourseRepository
from services import CourseService

# 初始化
db = Database()
session = db.get_session()
course_repo = CourseRepository(session)
course_service = CourseService(course_repo)

# 初始化 Subject
course_service.initialize_subjects("SP26")

# 导入特定学科
stats = course_service.import_courses_from_api("SP26", "INFO")

# 导入所有学科
all_stats = course_service.import_all_subjects("SP26")

# 解析 combined groups
combined_stats = course_service.resolve_combined_groups("SP26")
```

## 依赖说明

- `requests`: HTTP 请求库，用于调用 Cornell API
- `sqlalchemy`: Python ORM 库
- `pymysql`: MySQL 驱动
- `python-dotenv`: 环境变量管理

## 注意事项

- `.env` 文件包含敏感信息，已加入 `.gitignore`，不会提交到 Git
- 首次运行必须使用 `--reset` 参数重建表结构
- 支持重复导入同一学期（增量更新）
- 历史学期导入不会覆盖最新数据
- 导入所有学科（200+）预计需要 15-30 分钟
- 建议先用 `--subjects` 参数测试几个学科

## 常见问题

**Q: 如何查看有哪些学科可以导入？**
A: 运行程序后，系统会自动从 API 获取所有学科列表并存入数据库。

**Q: 如何只更新选课状态而不重新导入所有数据？**
A: 使用 `python src/main.py --semester SP26` 即可，系统会智能匹配现有数据并只更新变化的字段。

**Q: Combined Groups 是什么？**
A: 一些课程会交叉列出（如 CS 4780 和 INFO 4780 是同一门课），系统会自动识别并将它们分组。

**Q: 为什么导入很慢？**
A: 因为要调用 200+ 次 API（每个学科一次）。可以使用 `--subjects` 参数只导入需要的学科。
