#!/bin/bash

# LAMMPS MCP 启动脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查端口是否被占用
check_port() {
    if lsof -i:$1 >/dev/null 2>&1; then
        print_error "端口 $1 已被占用"
        return 1
    fi
    return 0
}

print_info "🚀 启动 LAMMPS MCP 服务..."

# 检查Docker和Docker Compose是否安装
if ! command_exists docker; then
    print_error "Docker 未安装，请先安装 Docker"
    echo "安装指南: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command_exists docker-compose; then
    if ! command_exists docker compose; then
        print_error "Docker Compose 未安装，请先安装 Docker Compose"
        echo "安装指南: https://docs.docker.com/compose/install/"
        exit 1
    fi
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

print_success "Docker 和 Docker Compose 已安装"

# 检查端口占用
-check_port 8000 || exit 1
-check_port 6379 || exit 1
+check_port 18000 || exit 1
+check_port 16379 || exit 1
+check_port 18080 || exit 1

# 创建必要的目录
-print_info "📁 创建必要的目录..."
-mkdir -p data/simulations data/uploads data/logs data/backups
-mkdir -p nginx/ssl
+print_info "📁 创建必要的目录..."
+mkdir -p data/simulations data/uploads data/logs data/backups
+mkdir -p nginx/ssl
+mkdir -p examples

# 设置权限
print_info "🔒 设置目录权限..."
chmod -R 755 data/ nginx/

# 检查.env文件
if [ ! -f .env ]; then
    print_warning "未找到 .env 文件，创建默认配置..."
    cat > .env << EOF
# LAMMPS MCP 配置
ENVIRONMENT=development
REDIS_URL=redis://redis:6379
WORKERS=2
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key-change-this
EOF
    print_info "请编辑 .env 文件以配置您的环境"
fi

# 构建镜像
print_info "🔨 构建 Docker 镜像..."
$DOCKER_COMPOSE build --no-cache

# 启动服务
print_info "🚀 启动服务..."
$DOCKER_COMPOSE up -d

# 等待服务启动
print_info "⏳ 等待服务启动..."
for i in {1..30}; do
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        print_success "API 服务已启动"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "服务启动超时"
        $DOCKER_COMPOSE logs --tail=50
        exit 1
    fi
    sleep 2
done

# 显示服务状态
 print_info "📊 服务状态:"
 $DOCKER_COMPOSE ps
 
 # 显示资源使用情况
 print_info "💾 资源使用情况:"
 docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
 
 print_success "服务启动完成！"
 echo ""
-echo "🌐 访问地址:"
-echo "   API: http://localhost:8000"
-echo "   文档: http://localhost:8000/docs"
-echo "   健康检查: http://localhost:8000/health"
+echo "🌐 访问地址:"
+echo "   API: http://localhost:18000"
+echo "   文档: http://localhost:18000/docs"
+echo "   健康检查: http://localhost:18000/health"
+echo "   Nginx: http://localhost:18080"
 echo ""
-echo "📂 数据目录:"
-echo "   模拟数据: ./data/simulations/"
-echo "   上传文件: ./data/uploads/"
-echo "   日志文件: ./data/logs/"
+echo "📂 数据目录:"
+echo "   模拟数据: ./data/simulations/"
+echo "   上传文件: ./data/uploads/"
+echo "   日志文件: ./data/logs/"
+echo "   示例输入: ./examples/"
 echo ""
echo "🔧 常用命令:"
echo "   查看日志: $DOCKER_COMPOSE logs -f [service]"
echo "   停止服务: $DOCKER_COMPOSE down"
echo "   重启服务: $DOCKER_COMPOSE restart"
echo "   查看状态: $DOCKER_COMPOSE ps"
echo "   进入容器: $DOCKER_COMPOSE exec api bash"
echo "   清理数据: $DOCKER_COMPOSE down -v"
echo ""
echo "🆘 故障排除:"
echo "   查看详细日志: $DOCKER_COMPOSE logs --tail=100 api"
echo "   检查服务状态: $DOCKER_COMPOSE ps -a"
echo "   重启单个服务: $DOCKER_COMPOSE restart api"