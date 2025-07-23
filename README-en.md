
# LAMMPS MCP - Molecular Dynamics Simulation Service

[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Driven-green.svg)](https://fastapi.tiangolo.com/)
[![LAMMPS](https://img.shields.io/badge/LAMMPS-Integrated-orange.svg)](https://www.lammps.org/)

A modern LAMMPS molecular dynamics simulation service providing RESTful API interface, Docker container deployment, complete logging, and MPI parallel computing support.

**[English Version](README-en.md)** | **中文版**

## 🚀 Features

- **Full LAMMPS Functionality Support** - Access all LAMMPS features via the Python API
- **RESTful API** - Standardized HTTP interface for easy integration
- **Asynchronous Task Processing** - Distributed task queue powered by Celery
- **Docker Containerization** - One-click deployment without complex configuration
- **MPI Parallel Support** - Supports multi-process parallel computing
- **Structured Logging** - Complete operational and error logging
- **Real-time Monitoring** - Task progress and system status monitoring
- **File Management** - Full management of simulation input and output files

## 📋 Directory Structure

```
lammps-mcp/
├── app/                    # Application code
│   ├── api/               # API routes
│   │   ├── endpoints/     # Endpoint definitions
│   │   └── router.py      # Route configuration
│   ├── core/              # Core configuration
│   ├── models/            # Data models
│   ├── services/          # Business logic
│   ├── tasks/             # Asynchronous tasks
│   ├── main.py            # FastAPI entrypoint
│   └── celery.py          # Celery configuration
├── data/                  # Data directory
├── nginx/                 # Nginx configuration
├── docker-compose.yml     # Docker Compose config
├── Dockerfile            # Docker image build file
├── requirements.txt      # Python dependencies
└── README.md            # Project documentation
```

## 🛠️ Quick Start

### Prerequisites

- Docker and Docker Compose
- At least 4GB of RAM
- MPI-supported system (optional)
- Required ports: 18000 (API), 16379 (Redis), 18080 (Nginx)

### One-Click Launch

```bash
# Clone the project
git clone <repository-url>
cd lammps-mcp
```

### Manual Launch

```bash
# Create necessary directories
mkdir -p data/simulations data/uploads data/logs

# Build the image
docker-compose build

# Start the service
docker-compose up -d

# Start monitoring services
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Check service status
docker-compose ps
```

## 📖 API Usage Guide

### Create Simulation

```bash
curl -X POST http://localhost:18000/api/v1/simulations   -H "Content-Type: application/json"   -d '{
    "name": "Lennard-Jones Simulation",
    "description": "Simple LJ fluid simulation",
    "input_script": "units lj\natom_style atomic\nlattice fcc 0.8442\nregion box block 0 10 0 10 0 10\ncreate_box 1 box\ncreate_atoms 1 box\nmass 1 1.0\nvelocity all create 1.44 87287 loop geom\npair_style lj/cut 2.5\npair_coeff 1 1 1.0 1.0 2.5\nneighbor 0.3 bin\nneigh_modify delay 5 every 1\nfix 1 all nve\nrun 1000",
    "mpi_processes": 2
  }'
```

### Start Simulation

```bash
curl -X POST http://localhost:18000/api/v1/simulations/{simulation_id}/start
```

### Get Simulation Status

```bash
curl http://localhost:18000/api/v1/simulations/{simulation_id}
```

### Get Simulation Logs

```bash
curl http://localhost:18000/api/v1/simulations/{simulation_id}/logs
```

### Get Simulation Results

```bash
curl http://localhost:18000/api/v1/simulations/{simulation_id}/results
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LAMMPS_POTENTIALS` | `/app/lammps/potentials` | Potential file directory |
| `DATA_DIR` | `/app/data` | Data storage directory |
| `LOG_LEVEL` | `INFO` | Logging level |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `MPI_PROCESSES` | `1` | Default MPI process count |

### Docker Compose Services

- **api**: FastAPI application service
- **worker**: Celery worker process
- **redis**: Message queue and cache
- **nginx**: Reverse proxy and static file service
- **flower**: Celery monitoring UI

### Monitoring Services

- **API Docs**: http://localhost:18000/docs - Swagger documentation
- **Health Check**: http://localhost:18000/health

### Log Viewing

```bash
# View logs for all services
docker-compose logs -f

# View specific service logs
docker-compose logs -f api
docker-compose logs -f worker
```

## 🧪 Example Use Cases

### 1. Create and Run an LJ Fluid Simulation

```python
import requests

# Create a simulation
response = requests.post('http://localhost:18000/api/v1/simulations', json={
    'name': 'LJ Fluid Test',
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

# Start the simulation
requests.post(f'http://localhost:18000/api/v1/simulations/{simulation_id}/start')
```

### 2. Batch Simulations

```python
import asyncio
import aiohttp

async def run_simulations():
    async with aiohttp.ClientSession() as session:
        # Create multiple simulations
        tasks = []
        for temp in [1.0, 1.5, 2.0]:
            task = session.post('http://localhost:18000/api/v1/simulations', json={
                'name': f'T={temp} LJ Simulation',
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

        # Parallel creation
        responses = await asyncio.gather(*tasks)

        # Start all simulations
        start_tasks = []
        for response in responses:
            sim_id = (await response.json())['id']
            start_tasks.append(
                session.post(f'http://localhost:18000/api/v1/simulations/{sim_id}/start')
            )

        await asyncio.gather(*start_tasks)

# Run batch simulations
asyncio.run(run_simulations())
```

## 🐛 Troubleshooting

### Common Issues

1. **Container Failed to Start**
   ```bash
   # Check logs
   docker-compose logs

   # Rebuild
   docker-compose build --no-cache
   ```

2. **LAMMPS Cannot Find Potential Files**
   ```bash
   # Check potential directory
   docker-compose exec api ls -la /app/lammps/potentials/
   ```

3. **MPI Processes Fail to Start**
   ```bash
   # Check MPI installation
   docker-compose exec api mpirun --version
   ```

4. **Insufficient Memory**
   ```bash
   # Increase Docker memory limit
   # Edit mem_limit in docker-compose.yml
   ```

### Debugging Tips

- Use `docker-compose exec api bash` to enter the container
- View detailed logs: `docker-compose logs -f --tail=100 api`
- Check task status: visit http://localhost:5555

## 🤝 Contribution Guide

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

For questions or suggestions, contact us via:

- Create a GitHub Issue
- Send an email to the project maintainer

## 🔗 Related Resources

- [LAMMPS Official Docs](https://docs.lammps.org/)
- [LAMMPS Python Interface](https://docs.lammps.org/Python_head.html)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Celery Docs](https://docs.celeryproject.org/)
