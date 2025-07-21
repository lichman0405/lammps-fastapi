# LAMMPS MCP - Molecular Dynamics Simulation Service

[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Powered-green.svg)](https://fastapi.tiangolo.com/)
[![LAMMPS](https://img.shields.io/badge/LAMMPS-Integrated-orange.svg)](https://www.lammps.org/)

An advanced web service that provides RESTful API for LAMMPS molecular dynamics simulations, supporting distributed computing and real-time monitoring.

## 🌟 Features

- **RESTful API**: Clean and intuitive REST API for LAMMPS simulations
- **Distributed Computing**: Celery-based task queue for scalable simulation processing
- **Real-time Monitoring**: Flower integration for task monitoring and management
- **Docker Support**: Complete containerization with Docker Compose
- **Multiple Examples**: Ready-to-use LAMMPS simulation examples
- **Health Checks**: Built-in health monitoring and status reporting
- **Security**: Non-root container execution and security best practices
- **Monitoring & Observability**: Integrated Prometheus, Grafana, Loki, and log collection

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Ports 18000 (API), 16379 (Redis), 18080 (Nginx), 19090 (Prometheus), 13000 (Grafana), 19100 (Node Exporter), 19121 (Redis Exporter), 13100 (Loki) available

### One-Click Start

```bash
# Clone the repository
git clone <repository-url>
cd lammps-mcp

# Make the script executable
chmod +x start.sh start-monitoring.sh

# Start the main service
./start.sh

# Start monitoring stack (Prometheus, Grafana, Loki, etc.)
./start-monitoring.sh
```

### Manual Start

```bash
# Build and start services
docker-compose build
docker-compose up -d

# Start monitoring stack
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Check service status
docker-compose ps
```

## 📋 API Documentation

Once the service is running, you can access:

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Flower Monitoring**: http://localhost:5555

## 📁 Project Structure

```
lammps-mcp/
├── app/                    # Main application code
│   ├── api/               # API endpoints and routing
│   ├── core/              # Core configurations
│   ├── models/            # Data models
│   ├── services/          # Business logic
│   └── tasks/             # Celery tasks
├── examples/              # LAMMPS simulation examples
├── data/                  # Data directories (created automatically)
├── nginx/                 # Nginx configuration
├── docker-compose.yml     # Docker Compose configuration
├── Dockerfile            # Docker configuration
└── start.sh              # Startup script
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Application Configuration
ENVIRONMENT=development
REDIS_URL=redis://redis:6379
WORKERS=2
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key-change-this
```

### Docker Configuration

The service uses multi-stage Docker builds for optimal performance:

- **Base Image**: python:3.11-slim
- **LAMMPS**: Compiled from source with Python support
- **Security**: Runs as non-root user
- **Health Checks**: Built-in health monitoring

## 📊 Usage Examples

### Submit a Simulation

```bash
# Submit LJ fluid simulation
curl -X POST "http://localhost:8000/api/v1/simulations" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "LJ Fluid Simulation",
    "input_file": "examples/lj_fluid_complete.in",
    "parameters": {
      "temperature": 1.0,
      "density": 0.8
    }
  }'
```

### Check Simulation Status

```bash
# Get simulation status
curl "http://localhost:8000/api/v1/simulations/{simulation_id}/status"
```

### Download Results

```bash
# Download simulation results
curl "http://localhost:8000/api/v1/simulations/{simulation_id}/download" \
  -o results.zip
```

## 🧪 Examples

The project includes several LAMMPS simulation examples:

### 1. Lennard-Jones Fluid (`examples/lj_fluid_complete.in`)
- **Description**: Basic LJ fluid simulation with NVT and NVE ensembles
- **Features**: Equilibration, production run, MSD calculation, RDF analysis
- **Usage**: Ready to run without additional files

### 2. Graphene Tensile Test (`examples/graphene.in`)
- **Description**: Graphene sheet under tensile loading
- **Features**: AIREBO potential, stress-strain analysis, deformation tracking
- **Requirements**: Requires `CH.airebo` potential file

### 3. Basic LJ Fluid (`examples/lj_fluid.in`)
- **Description**: Simple LJ fluid setup
- **Features**: Basic initialization and NVE dynamics
- **Usage**: Minimal configuration example

## 🔍 Monitoring and Debugging

### Service Health

```bash
# Check service health
curl http://localhost:8000/health

# View service logs
docker-compose logs -f api
docker-compose logs -f worker
```

### Resource Monitoring

```bash
# View container statistics
docker stats

# Check Redis status
docker-compose exec redis redis-cli ping
```

### Troubleshooting

Common issues and solutions:

1. **Port Conflicts**: Ensure ports 8000 and 6379 are available
2. **Permission Issues**: Check directory permissions in `./data/`
3. **LAMMPS Errors**: Verify input files in `./examples/`
4. **Memory Issues**: Monitor resource usage with `docker stats`

## 🐛 Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis (if running locally)
redis-server

# Start Celery worker
celery -A app.celery worker --loglevel=info

# Start API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Run tests
python test_service.py

# Test with curl
curl http://localhost:8000/health
```

## 🛡️ Security

- **Non-root containers**: All services run as non-root users
- **Volume permissions**: Proper file ownership and permissions
- **Environment variables**: Sensitive data managed via .env files
- **Network isolation**: Services communicate through dedicated networks

## 📈 Scaling

### Horizontal Scaling

```bash
# Scale worker processes
docker-compose up -d --scale worker=4

# Monitor with Flower
open http://localhost:5555
```

### Vertical Scaling

Adjust resource limits in `docker-compose.yml`:

```yaml
services:
  worker:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- [LAMMPS Official Documentation](https://docs.lammps.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Docker Documentation](https://docs.docker.com/)

---

**中文文档**: [README.md](README.md)

## 🔍 Monitoring and Observability

- **Prometheus**: http://localhost:19090
- **Grafana**: http://localhost:13000 (default login: admin/admin123)
- **Loki**: http://localhost:13100
- **Node Exporter**: http://localhost:19100
- **Redis Exporter**: http://localhost:19121

Logs are collected from ./logs and visualized in Grafana via Loki.