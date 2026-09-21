# 长河

长河是一款以全球并行时间线和可追溯史料为核心的 Android 历史浏览应用。

## 当前实现

当前仓库包含知识后台纵向切片：

- 带时间精度的历史陈述模型
- 来源、版本和引用模型
- 人工审核后发布的工作流
- Django Admin 内容管理
- 匿名只读的年度切片 API

## 本地运行

要求：Python 3.13、Docker Desktop、PowerShell。

```powershell
docker compose up -d db
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:DATABASE_URL = "postgresql://changhe:changhe-local@localhost:5432/changhe"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py load_reference_data
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

打开：

- 健康检查：http://127.0.0.1:8000/health/
- 内容后台：http://127.0.0.1:8000/admin/
- 年度切片：http://127.0.0.1:8000/api/v1/timeline/year-slice/?year=1520

## 验证

```powershell
cd backend
$env:DATABASE_URL = "postgresql://changhe:changhe-local@localhost:5432/changhe"
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
```

## 内容规则

- AI 输出只能保存为候选草稿。
- 发布操作需要员工审核者、审核原因和至少一个有效引用。
- 未获授权的全文不得进入仓库或同步包。
- 历史日期必须保留来源提供的精度和不确定性。
