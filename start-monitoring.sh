#!/bin/bash

# LAMMPS MCP 监控服务启动脚本
# 包含Prometheus、Grafana、Loki等监控组件

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 错误处理函数
handle_error() {
    echo -e "${RED}错误: 在步骤 $1 失败${NC}"
    echo -e "${RED}错误信息: $2${NC}"
    exit 1
}

# 检查Docker和Docker Compose
if ! command -v docker &> /dev/null; then
    handle_error "Docker检查" "Docker未安装或未正确配置"
fi

if ! command -v docker-compose &> /dev/null; then
    handle_error "Docker Compose检查" "Docker Compose未安装或未正确配置"
fi

# 创建必要的目录
 echo -e "${GREEN}创建必要的目录...${NC}"
-mkdir -p data/{prometheus,grafana,loki,logs}
-mkdir -p grafana/provisioning/{dashboards,datasources}
+mkdir -p data/{prometheus,grafana,loki}
+mkdir -p logs
+mkdir -p grafana/provisioning/{dashboards,datasources}

# 设置权限
 echo -e "${GREEN}设置目录权限...${NC}"
-sudo chown -R 472:472 data/grafana  # Grafana用户ID
-sudo chown -R 10001:10001 data/prometheus  # Prometheus用户ID
+sudo chown -R 472:472 data/grafana  # Grafana用户ID
+sudo chown -R 65534:65534 data/loki  # Loki用户ID
+sudo chown -R 10001:10001 data/prometheus  # Prometheus用户ID

# 创建Grafana数据源配置
cat > grafana/provisioning/datasources/datasources.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
EOF

# 创建Grafana仪表板配置
cat > grafana/provisioning/dashboards/dashboards.yml << EOF
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

# 启动监控服务
 echo -e "${GREEN}启动监控服务...${NC}"
-docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
+docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# 等待服务启动
echo -e "${YELLOW}等待监控服务启动...${NC}"
sleep 10

# 检查服务状态
echo -e "${GREEN}检查监控服务状态...${NC}"
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml ps

# 显示访问信息
 echo -e "${GREEN}监控服务已启动！${NC}"
 echo -e "${GREEN}=====================${NC}"
-echo -e "${YELLOW}Prometheus: http://localhost:9090${NC}"
-echo -e "${YELLOW}Grafana: http://localhost:3000${NC}"
-echo -e "${YELLOW}Grafana 默认登录: admin/admin123${NC}"
-echo -e "${YELLOW}Loki: http://localhost:3100${NC}"
-echo -e "${YELLOW}Node Exporter: http://localhost:9100${NC}"
-echo -e "${YELLOW}Redis Exporter: http://localhost:9121${NC}"
+echo -e "${YELLOW}Prometheus: http://localhost:19090${NC}"
+echo -e "${YELLOW}Grafana: http://localhost:13000${NC}"
+echo -e "${YELLOW}Grafana 默认登录: admin/admin123${NC}"
+echo -e "${YELLOW}Loki: http://localhost:13100${NC}"
+echo -e "${YELLOW}Node Exporter: http://localhost:19100${NC}"
+echo -e "${YELLOW}Redis Exporter: http://localhost:19121${NC}"
 echo -e "${GREEN}=====================${NC}"

# 显示常用命令
echo -e "${GREEN}常用命令:${NC}"
echo -e "  查看日志: docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml logs -f [服务名]"
echo -e "  停止服务: docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml down"
echo -e "  重启服务: docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml restart"
echo -e "  更新配置: docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d"