# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

国际象棋机械臂控制系统，包含棋盘UI、AI对弈、机械臂控制、视觉检测四个模块。

## 系统架构

```
chess_ui.py (主控/UI)  ──TCP──▶  chess_arm_server.py (树莓派:5001)
       │                              │
       ▼                              ▼
stockfish (AI)                   机械臂 (执行)
```

**职责分工**：
- `chess_ui.py` - 主控端，运行在PC，发送走法指令
- `chess_arm_server.py` - 执行端，运行在树莓派，接收指令控制机械臂
- `board_to_robot.py` + `ik.py` - 坐标转换和逆运动学（可运行在任一方）

## 核心文件

| 文件 | 职责 |
|------|------|
| [chess_ui.py](chess_ui.py) | 主UI，AI对弈，TCP发送MOVE指令 |
| [chess_arm_server.py](chess_arm_server.py) | 机械臂服务器，执行走法 |
| [chess_arm_client.py](chess_arm_client.py) | TCP客户端封装 |
| [board_to_robot.py](board_to_robot.py) | UCI坐标 → 机器人坐标 |
| [ik.py](ik.py) | 逆运动学（4自由度） |
| [detector.py](detector.py) | YOLO视觉检测 |
| [stockfish_server.py](stockfish_server.py) | Stockfish HTTP API |
| [Arm_Lib/](Arm_Lib/) | 机械臂底层舵机库 |

## 技术栈

- **UI**: tkinter (Python内置)
- **AI**: Stockfish depth=40 (HTTP API → localhost:8080)
- **机械臂**: 4自由度 (TCP → 192.168.137.60:5001)
- **视觉**: YOLO + OpenCV
- **棋盘坐标**: UCI (a1-h8)

## 网络配置

| 服务 | 地址 | 端口 |
|------|------|------|
| 机械臂服务器 | 192.168.137.60 | 5001 |
| Stockfish API | localhost | 8080 |

## 机械臂指令格式

```
MOVE,x,y,z,x2,y2,z2,is_capture,move_desc
```

## 棋子参数

| 棋子 | 高度(cm) | 夹爪角度 |
|------|----------|----------|
| 兵(P/p) | 4.0 | 161 |
| 车(R/r) | 4.0 | 157 |
| 马(N/n) | 5.2 | 164 |
| 象(B/b) | 6.5 | 161 |
| 王(K/k) | 7.2 | 152 |
| 后(Q/q) | 6.0 | 153 |

## 常用命令

```bash
python3 chess_ui.py              # 启动主UI（先运行）
python3 chess_arm_server.py     # 启动机械臂服务器（树莓派）
python3 stockfish_server.py     # 启动Stockfish API
python3 detector.py --conf 0.2  # 启动视觉检测
```

**启动顺序**: UI → Stockfish API → Arm Server

## 机械臂执行序列（9步）

1. 移动到目标上方（safe_height=13）
2. 一次下降（9.0cm）
3. 二次下降（棋子高度）
4. 夹取
5. 抬升
6. 移动到放置位置上方
7. 下降放置
8. 抬升
9. 返回初始位置

## 坐标系统

- **棋盘**: UCI格式（e2, a1），a1在左下角
- **转换**: `board_to_robot.py` 将UCI转为机器人坐标
- **Z校正**: `z + 0.15 * sqrt(x² + y²)` （补偿远端下沉）
- **逆运动学**: `ik.py` - 输入x,y,z,alpha → 输出j1-j4角度

## 注意事项

1. Z坐标校正系数需根据实际测试调整
2. 棋盘边界参数需实际标定
3. UI支持白/黑选边，棋盘翻转
4. 王车易位通过UI按钮触发两步模式