# LAMMPS MCP - 分子动力学模拟服务

[![Docker](https://img.shields.io/badge/Docker-支持-blue.svg)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-驱动-green.svg)](https://fastapi.tiangolo.com/)
[![LAMMPS](https://img.shields.io/badge/LAMMPS-集成-orange.svg)](https://www.lammps.org/)

一个现代化的LAMMPS分子动力学模拟服务，提供RESTful API接口，支持Docker容器化部署，具备完整的日志记录和MPI并行计算能力。

**[English Version](README-en.md)** | **中文版本**

## 🚀 功能特性

- **完整的LAMMPS功能支持** - 通过Python API访问所有LAMMPS功能
- **RESTful API** - 标准化的HTTP接口，易于集成
- **异步任务处理** - 基于Celery的分布式任务队列
- **Docker容器化** - 一键部署，无需复杂配置
- **MPI并行支持** - 支持多进程并行计算
- **结构化日志** - 完整的操作和错误日志记录
- **实时监控** - 任务进度和系统状态监控
- **文件管理** - 模拟输入输出文件的完整管理

## 📋 目录结构

```
lammps-mcp/
├── app/                    # 应用代码
│   ├── api/               # API路由
│   │   ├── endpoints/     # 端点定义
│   │   └── router.py      # 路由配置
│   ├── core/              # 核心配置
│   ├── models/            # 数据模型
│   ├── services/          # 业务逻辑
│   ├── tasks/             # 异步任务
│   ├── main.py            # FastAPI入口
│   └── celery.py          # Celery配置
├── data/                  # 数据目录
├── nginx/                 # Nginx配置
├── docker-compose.yml     # Docker Compose配置
├── Dockerfile            # Docker镜像构建
├── requirements.txt      # Python依赖
└── README.md            # 项目文档
```

## 🛠️ 快速开始

### 前提条件

- Docker 和 Docker Compose
- 至少 4GB 内存
- 支持MPI的系统（可选）
- 端口需求：18000（API）、16379（Redis）、18080（Nginx）


### 一键启动

```bash
# 克隆项目
git clone <repository-url>
cd lammps-mcp
```

### 手动启动

```bash
# 创建必要目录
mkdir -p data/simulations data/uploads data/logs

# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 启动监控服务
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# 查看服务状态
docker-compose ps
```

## 📖 API使用指南

### 创建模拟

```bash
curl -X POST http://localhost:18000/api/v1/simulations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Lennard-Jones模拟",
    "description": "简单的LJ流体模拟",
    "input_script": "units lj\natom_style atomic\nlattice fcc 0.8442\nregion box block 0 10 0 10 0 10\ncreate_box 1 box\ncreate_atoms 1 box\nmass 1 1.0\nvelocity all create 1.44 87287 loop geom\npair_style lj/cut 2.5\npair_coeff 1 1 1.0 1.0 2.5\nneighbor 0.3 bin\nneigh_modify delay 5 every 1\nfix 1 all nve\nrun 1000",
    "mpi_processes": 2
  }'
```

### 启动模拟

```bash
curl -X POST http://localhost:18000/api/v1/simulations/{simulation_id}/start
```

### 获取模拟状态

```bash
curl http://localhost:18000/api/v1/simulations/{simulation_id}
```

### 获取模拟日志

```bash
curl http://localhost:18000/api/v1/simulations/{simulation_id}/logs
```

### 获取模拟结果

```bash
curl http://localhost:18000/api/v1/simulations/{simulation_id}/results
```

## 🔧 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `LAMMPS_POTENTIALS` | `/app/lammps/potentials` | 势函数文件目录 |
| `DATA_DIR` | `/app/data` | 数据存储目录 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `REDIS_URL` | `redis://redis:6379/0` | Redis连接URL |
| `MPI_PROCESSES` | `1` | 默认MPI进程数 |

### Docker Compose服务

- **api**: FastAPI应用服务
- **worker**: Celery工作进程
- **redis**: 消息队列和缓存
- **nginx**: 反向代理和静态文件服务
- **flower**: Celery监控界面

### 服务监控

- **API文档**: http://localhost:18000/docs - Swagger文档
- **健康检查**: http://localhost:18000/health

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f api
docker-compose logs -f worker
```

## 🧪 示例用例

### 1. 创建并运行LJ流体模拟

```python
import requests

# 创建模拟
response = requests.post('http://localhost:18000/api/v1/simulations', json={
    'name': 'LJ流体测试',
    'input_script': '''
        units lj
        atom_style atomic
        lattice fcc 0.8442
        region box block 0 10 0 10 0 10
        create_box 1 box
        create_atoms 1 box
        mass 1 1.0
        velocity all create 1.44 87287 loop geom
        pair_style lj/cut 2.5
        pair_coeff 1 1 1.0 1.0 2.5
        neighbor 0.3 bin
        neigh_modify delay 5 every 1
        fix 1 all nve
        thermo 100
        run 1000
    ''',
    'mpi_processes': 2
})

simulation_id = response.json()['id']

# 启动模拟
requests.post(f'http://localhost:18000/api/v1/simulations/{simulation_id}/start')
```

### 2. 批量模拟

```python
import asyncio
import aiohttp

async def run_simulations():
    async with aiohttp.ClientSession() as session:
        # 创建多个模拟任务
        tasks = []
        for temp in [1.0, 1.5, 2.0]:
            task = session.post('http://localhost:18000/api/v1/simulations', json={
                'name': f'T={temp} LJ模拟',
                'input_script': f'''
                    units lj
                    atom_style atomic
                    lattice fcc 0.8442
                    region box block 0 10 0 10 0 10
                    create_box 1 box
                    create_atoms 1 box
                    mass 1 1.0
                    velocity all create {temp} 87287 loop geom
                    pair_style lj/cut 2.5
                    pair_coeff 1 1 1.0 1.0 2.5
                    fix 1 all nve
                    thermo 100
                    run 1000
                ''',
                'mpi_processes': 1
            })
            tasks.append(task)
        
        # 并行创建
        responses = await asyncio.gather(*tasks)
        
        # 启动所有模拟
        start_tasks = []
        for response in responses:
            sim_id = (await response.json())['id']
            start_tasks.append(
                session.post(f'http://localhost:18000/api/v1/simulations/{sim_id}/start')
            )
        
        await asyncio.gather(*start_tasks)

# 运行批量模拟
asyncio.run(run_simulations())
```

## 🐛 故障排除

### 常见问题

1. **容器启动失败**
   ```bash
   # 检查日志
   docker-compose logs
   
   # 重新构建
   docker-compose build --no-cache
   ```

2. **LAMMPS找不到势函数文件**
   ```bash
   # 检查势函数目录
   docker-compose exec api ls -la /app/lammps/potentials/
   ```

3. **MPI进程无法启动**
   ```bash
   # 检查MPI安装
   docker-compose exec api mpirun --version
   ```

4. **内存不足**
   ```bash
   # 增加Docker内存限制
   # 编辑docker-compose.yml中的mem_limit
   ```

### 调试技巧

- 使用 `docker-compose exec api bash` 进入容器调试
- 查看详细日志：`docker-compose logs -f --tail=100 api`
- 检查任务状态：访问 http://localhost:5555

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙋‍♂️ 支持

如有问题或建议，请通过以下方式联系：

- 创建 GitHub Issue
- 发送邮件至项目维护者

## 🔗 相关资源

- [LAMMPS官方文档](https://docs.lammps.org/)
- [LAMMPS Python接口](https://docs.lammps.org/Python_head.html)
- [FastAPI文档](https://fastapi.tiangolo.com/)
- [Celery文档](https://docs.celeryproject.org/)