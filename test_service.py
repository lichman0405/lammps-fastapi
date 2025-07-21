#!/usr/bin/env python3
"""
LAMMPS MCP服务测试脚本
用于验证服务的基本功能
"""

import requests
import time
import json
import os

# 配置
BASE_URL = "http://localhost:18000/api/v1"


def test_health_check():
    """测试健康检查"""
    print("🔍 测试健康检查...")
    response = requests.get(f"{BASE_URL.replace('/api/v1', '')}/health")
    assert response.status_code == 200
    print("✅ 健康检查通过")


def test_create_simulation():
    """测试创建模拟"""
    print("🔍 测试创建模拟...")
    
    # 读取示例输入文件
    with open('examples/lj_fluid.in', 'r') as f:
        input_script = f.read()
    
    payload = {
        "name": "测试LJ流体模拟",
        "description": "使用API创建的测试模拟",
        "input_script": input_script,
        "mpi_processes": 1
    }
    
    response = requests.post(f"{BASE_URL}/simulations", json=payload)
    assert response.status_code == 200
    
    result = response.json()
    simulation_id = result["id"]
    print(f"✅ 模拟创建成功: {simulation_id}")
    
    return simulation_id


def test_validate_script():
    """测试脚本验证"""
    print("🔍 测试脚本验证...")
    
    # 有效的脚本
    valid_script = """
    units lj
    atom_style atomic
    lattice fcc 0.8442
    region box block 0 5 0 5 0 5
    create_box 1 box
    create_atoms 1 box
    mass 1 1.0
    pair_style lj/cut 2.5
    pair_coeff 1 1 1.0 1.0 2.5
    run 100
    """
    
    payload = {"script_content": valid_script}
    response = requests.post(f"{BASE_URL}/validation/lammps", json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 脚本验证通过: {result}")
    else:
        print(f"⚠️  脚本验证失败: {response.text}")


def test_run_simulation(simulation_id):
    """测试运行模拟"""
    print("🔍 测试运行模拟...")
    
    response = requests.post(f"{BASE_URL}/simulations/{simulation_id}/start")
    assert response.status_code == 200
    
    print("✅ 模拟启动成功")
    
    # 等待模拟完成
    print("⏳ 等待模拟完成...")
    max_wait = 60  # 最多等待60秒
    waited = 0
    
    while waited < max_wait:
        response = requests.get(f"{BASE_URL}/simulations/{simulation_id}")
        result = response.json()
        
        if result["status"] == "COMPLETED":
            print("✅ 模拟完成")
            return True
        elif result["status"] == "FAILED":
            print(f"❌ 模拟失败: {result.get('error', '未知错误')}")
            return False
        
        time.sleep(5)
        waited += 5
        print(f"⏳ 已等待 {waited} 秒...")
    
    print("⚠️  模拟超时")
    return False


def test_get_logs(simulation_id):
    """测试获取日志"""
    print("🔍 测试获取日志...")
    
    response = requests.get(f"{BASE_URL}/simulations/{simulation_id}/logs")
    assert response.status_code == 200
    
    logs = response.json()
    print(f"✅ 获取日志成功，共 {len(logs)} 行")
    
    return logs


def test_get_results(simulation_id):
    """测试获取结果"""
    print("🔍 测试获取结果...")
    
    response = requests.get(f"{BASE_URL}/simulations/{simulation_id}/results")
    assert response.status_code == 200
    
    results = response.json()
    print(f"✅ 获取结果成功，共 {len(results.get('files', []))} 个文件")
    
    return results


def test_list_simulations():
    """测试获取模拟列表"""
    print("🔍 测试获取模拟列表...")
    
    response = requests.get(f"{BASE_URL}/simulations")
    assert response.status_code == 200
    
    result = response.json()
    print(f"✅ 获取模拟列表成功，共 {result.get('total', 0)} 个模拟")
    
    return result


def main():
    """主测试函数"""
    print("🧪 开始测试 LAMMPS MCP 服务...")
    print("=" * 50)
    
    try:
        # 测试健康检查
        test_health_check()
        
        # 测试脚本验证
        test_validate_script()
        
        # 测试创建模拟
        simulation_id = test_create_simulation()
        
        # 测试获取模拟列表
        test_list_simulations()
        
        # 测试运行模拟
        success = test_run_simulation(simulation_id)
        
        if success:
            # 测试获取日志
            logs = test_get_logs(simulation_id)
            
            # 测试获取结果
            results = test_get_results(simulation_id)
            
            print("\n🎉 所有测试通过！")
            print(f"模拟ID: {simulation_id}")
            print(f"日志行数: {len(logs)}")
            print(f"结果文件: {len(results.get('files', []))}")
            
        else:
            print("\n❌ 模拟运行失败，请检查日志")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到服务，请确保服务已启动")
        print("运行: ./start.sh")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")


if __name__ == "__main__":
    main()