# 国际象棋机械臂控制系统 - 项目开发文档

## 1. 项目概述

本项目是一个完整的国际象棋人机对弈系统，集成以下功能：
- 图形化棋盘UI（支持鼠标点击走棋）
- Stockfish AI引擎对弈
- 机械臂执行棋子移动
- 视觉棋子检测（YOLO）

## 2. 系统架构

```
┌─────────────────┐     ┌──────────────────┐
│   chess_ui.py   │────▶│ chess_arm_server│
│   (主控/UI)      │TCP  │   (树莓派)       │
└─────────────────┘     └──────────────────┘
        │                        │
        │                        ▼
        │                ┌──────────────┐
        │                │   机械臂      │
        │                │  (执行移动)   │
        │                └──────────────┘
        ▼
┌─────────────────┐
│  stockfish     │
│  (AI引擎)       │
└─────────────────┘
```

## 3. 文件清单

| 文件 | 用途 |
|------|------|
| `chess_ui.py` | 主UI界面，AI对弈，TCP指令发送 |
| `chess_arm_server.py` | 机械臂控制服务器（树莓派） |
| `board_to_robot.py` | 棋盘坐标→机器人坐标转换 |
| `ik.py` | 逆运动学求解器 |
| `detector.py` | YOLO视觉棋子检测 |
| `stockfish_server.py` | Stockfish HTTP API |
| `chess.pt` | YOLO检测模型 |

## 4. 模块详细说明

### 4.1 chess_ui.py

**功能**：
- Tkinter 8x8棋盘显示
- 鼠标点击选子移动
- Stockfish AI（depth=40）
- 白/黑选边，棋盘翻转
- 王车易位、兵升变、吃子检测
- TCP连接机械臂服务器

**关键类**：`ChessUI`

**关键方法**：
- `_ai_move()` - 获取AI走法，更新棋盘
- `_do_move()` - 执行普通移动
- `_do_castling()` - 执行王车易位
- `_send_to_arm()` - 发送TCP指令

**TCP指令格式**：
```
MOVE,x,y,z,x2,y2,z2,is_capture,move_desc
```

### 4.2 chess_arm_server.py

**功能**：
- 监听TCP端口5001
- 接收走法指令
- 控制4自由度机械臂
- 夹爪控制（舵机6）

**走法执行序列**（9步）：
1. 移动到目标上方（safe_height=13）
2. 一次下降（9.0）
3. 二次下降（piece_height）
4. 夹取
5. 抬升
6. 移动到放置位置上方
7. 下降放置
8. 抬升
9. 返回初始位置

**棋子参数表**：
| 棋子 | 高度(cm) | 夹爪角度 |
|------|---------|----------|
| 兵(P/p) | 4.0 | 161 |
| 车(R/r) | 4.0 | 157 |
| 马(N/n) | 5.2 | 164 |
| 象(B/b) | 6.5 | 161 |
| 王(K/k) | 7.2 | 152 |
| 后(Q/q) | 6.0 | 153 |

**Z坐标校正**：
```
z_corrected = z + 0.15 * sqrt(x² + y²)
```

### 4.3 board_to_robot.py

**功能**：将UCI坐标（如e2）转换为机器人坐标

**默认参数**：
```python
GRID_SIZE_CM = 3.1
board_origin_robot = [-12.4, 3, 2.0]
board_dir_x = [1, 0, 0]
board_dir_y = [0, 1, 0]
```

**计算公式**：
```python
x = -12.4 + (col + 0.55) * 3.1
y = 3 + (row + 0.55) * 3.1
z = z_height
```

### 4.4 ik.py

**功能**：4自由度机械臂逆运动学求解

**DH参数**：
- A1=12.1, A2=8.4, A3=12.6, A4=18.8, P=5

**输入**：x, y, z, alpha(90-180)
**输出**：j1, j2, j3, j4（关节角度）

**约束**：
- 关节角度：-30° ~ 180°
- alpha自动调整

### 4.5 detector.py

**功能**：
- YOLO实时棋子检测
- 绿色点=白棋，红色点=黑棋
- 输出FEN格式

**参数**：
```bash
python3 detector.py --conf 0.2 --model chess.pt
```

**快捷键**：V=快照，F=FEN输出，Q=退出

## 5. 依赖

```
pip install chess numpy ultralytics opencv-python
```

## 6. 启动顺序

1. 机械臂服务器（树莓派）：
   ```bash
   python3 chess_arm_server.py
   ```

2. Stockfish API：
   ```bash
   python3 stockfish_server.py
   ```

3. 棋盘UI：
   ```bash
   python3 chess_ui.py
   ```

4. 视觉检测（可选）：
   ```bash
   python3 detector.py --conf 0.2
   ```

## 7. 网络配置

| 服务 | IP | 端口 |
|------|-----|------|
| 机械臂服务器 | 192.168.137.60 | 5001 |
| Stockfish API | localhost | 8080 |

## 8. UI操作

| 按钮 | 功能 |
|------|------|
| 悔棋 | 撤销上一回合 |
| AI走法 | 获取AI建议并显示 |
| 执行走法 | 发送指令到机械臂 |
| 重置 | 恢复初始局面 |
| 连接机械臂 | 建立TCP连接 |
| 王车易位 | 进入手动走两步模式 |

## 9. 待优化项

1. Z坐标校正系数需实际测试调整
2. 视觉检测棋盘边界需实际标定
3. 执黑时王后位置显示确认
4. 更多棋子类型的夹爪角度标定