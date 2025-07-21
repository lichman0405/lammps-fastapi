# LAMMPS 示例文件说明

本目录包含完整的LAMMPS模拟示例，每个示例都包含运行所需的所有文件。

## 示例列表

### 1. lj_fluid_complete.in - LJ流体完整模拟
一个完整的Lennard-Jones流体模拟示例，包含：
- 能量最小化
- NVT系综平衡
- NVE系综生产模拟
- MSD和RDF计算
- 轨迹输出

**所需文件：**
- lj_fluid_complete.in (输入脚本)
- 无需额外势函数文件 (使用内置LJ势)

### 2. graphene.in - 石墨烯拉伸模拟
石墨烯单轴拉伸的分子动力学模拟示例，包含：
- 石墨烯结构创建
- AIREBO势函数
- 能量最小化
- NPT平衡
- 拉伸变形测试
- 应力-应变分析

**所需文件：**
- graphene.in (输入脚本)
- CH.airebo (AIREBO势函数文件，需要从LAMMPS安装目录获取)

## 势函数文件获取

### AIREBO势函数文件
CH.airebo文件通常位于LAMMPS安装目录的`potentials/`子目录中。

**获取方法：**
```bash
# 如果LAMMPS已安装，复制势函数文件
cp /path/to/lammps/potentials/CH.airebo ./examples/

# 或者从LAMMPS GitHub获取
wget https://raw.githubusercontent.com/lammps/lammps/master/potentials/CH.airebo
```

## 运行示例

### 方法1：使用API
```bash
# 运行LJ流体模拟
curl -X POST "http://localhost:8000/api/simulations" \
  -H "Content-Type: application/json" \
  -d '{
    "simulation_id": "lj_test_001",
    "input_script": "'$(cat lj_fluid_complete.in | sed ':a;N;$!ba;s/\n/\\n/g')'",
    "mpi_processes": 2
  }'

# 运行石墨烯模拟
curl -X POST "http://localhost:8000/api/simulations" \
  -H "Content-Type: application/json" \
  -d '{
    "simulation_id": "graphene_test_001",
    "input_script": "'$(cat graphene.in | sed ':a;N;$!ba;s/\n/\\n/g')'",
    "mpi_processes": 4
  }'
```

### 方法2：手动运行
```bash
# 启动容器
./start.sh

# 进入容器
docker-compose exec api bash

# 运行模拟
lmp -in /app/examples/lj_fluid_complete.in
```

## 注意事项

1. **势函数文件权限**：确保势函数文件具有正确的读取权限
2. **内存需求**：石墨烯模拟可能需要较大内存，建议分配至少4GB
3. **并行计算**：根据系统核心数调整MPI进程数
4. **输出文件**：大型模拟会产生大量输出数据，注意磁盘空间

## 故障排除

### 势函数文件缺失
如果运行时报错找不到势函数文件：
- 检查文件路径是否正确
- 确认文件存在于指定位置
- 检查文件权限

### 内存不足
对于大体系模拟：
- 减少原子数量
- 增加内存分配
- 使用更小的模拟盒子

### 并行运行问题
- 确保MPI已正确安装
- 检查进程数不超过CPU核心数
- 查看日志文件获取详细错误信息