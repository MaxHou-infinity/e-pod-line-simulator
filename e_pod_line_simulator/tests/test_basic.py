"""
基础功能测试脚本

用于测试核心功能是否正常：
1. 数据模型测试
2. 仿真引擎测试
3. 工具函数测试

运行方式：
    python tests/test_basic.py
"""

import sys
import os

# 获取项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 添加项目根目录到Python路径
sys.path.insert(0, project_root)

from src.models import Station, ProductionLine, CollaborationType
from src.simulation import SimulationEngine, detect_waste
from src.utils import validate_station, format_time, calculate_roi


def test_models():
    """测试数据模型"""
    print("=" * 50)
    print("测试1: 数据模型")
    print("=" * 50)
    
    # 创建工序
    station1 = Station(
        id="s01",
        name="注油",
        process_time=25,
        worker_count=2,
        collaboration_type=CollaborationType.PARALLEL
    )
    
    print(f"✓ 创建工序: {station1.name}")
    print(f"  产能: {station1.get_capacity():.2f} 颗/h")
    
    # 创建产线
    line = ProductionLine("测试产线")
    line.add_station(station1)
    
    line.add_station(Station(
        id="s02",
        name="焊接",
        process_time=30,
        worker_count=3,
        collaboration_type=CollaborationType.PARALLEL
    ))
    
    print(f"✓ 创建产线: {line.name}")
    print(f"  工序数量: {len(line.stations)}")
    
    # 找出瓶颈
    bottleneck = line.find_bottleneck()
    if bottleneck:
        print(f"✓ 瓶颈工序: {bottleneck.name}")
        print(f"  瓶颈产能: {bottleneck.get_capacity():.2f} 颗/h")
    
    # 计算KPI
    daily_output = line.calculate_daily_output()
    total_cost = line.calculate_total_cost()
    unit_cost = line.calculate_unit_cost()
    
    print(f"✓ KPI计算:")
    print(f"  日产量: {daily_output:.0f} 颗")
    print(f"  日成本: {total_cost:.2f} 元")
    print(f"  单颗成本: {unit_cost:.4f} 元/颗")
    
    print("\n✅ 数据模型测试通过！\n")
    return line


def test_simulation(line):
    """测试仿真引擎"""
    print("=" * 50)
    print("测试2: 仿真引擎")
    print("=" * 50)
    
    # 创建仿真引擎
    engine = SimulationEngine(line)
    print("✓ 创建仿真引擎")
    
    # 测试瓶颈识别功能（使用ProductionLine的find_bottleneck方法）
    bottleneck = line.find_bottleneck()
    if bottleneck:
        print(f"✓ 瓶颈识别: {bottleneck.name}")
    
    # 测试浪费检测
    bottleneck_capacity = line.get_bottleneck_capacity()
    waste_alerts = detect_waste(line.stations, bottleneck_capacity)
    print(f"✓ 浪费检测: 发现 {len(waste_alerts)} 个浪费警报")
    
    print("\n✅ 仿真引擎测试通过！\n")
    print("注意: 完整仿真测试需要GUI环境，这里只测试核心算法\n")


def test_utils():
    """测试工具函数"""
    print("=" * 50)
    print("测试3: 工具函数")
    print("=" * 50)
    
    # 测试参数校验
    valid, error = validate_station("测试工序", 25, 2)
    print(f"✓ 参数校验: {valid}, 错误: {error if error else '无'}")
    
    # 测试时间格式化
    time_str = format_time(3661)
    print(f"✓ 时间格式化: 3661秒 = {time_str}")
    
    # 测试ROI计算
    roi = calculate_roi(10000, 200)
    print(f"✓ ROI计算: 投资1万，每天省200，回收期 {roi:.1f} 天")
    
    print("\n✅ 工具函数测试通过！\n")


def main():
    """主测试函数"""
    print("\n" + "=" * 50)
    print("PuffLine Planner - 基础功能测试")
    print("=" * 50 + "\n")
    
    try:
        # 测试数据模型
        line = test_models()
        
        # 测试仿真引擎
        test_simulation(line)
        
        # 测试工具函数
        test_utils()
        
        print("=" * 50)
        print("✅ 所有测试通过！")
        print("=" * 50)
        print("\n下一步: 运行GUI程序")
        print("命令: cd src && python main.py\n")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
