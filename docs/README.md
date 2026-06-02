# 国际象棋机械臂控制系统

## 项目概述

本项目是一个完整的国际象棋人机对弈系统，集成了 Stockfish AI 引擎、棋盘UI界面、机械臂控制服务器和视觉检测模块。

## 项目结构

```
ch_ws/
├── chess_ui.py              # 主UI界面（Tkinter）
├── chess_arm_server.py     # 机械臂控制服务器（运行在树莓派上）
├── chess_arm_client.py     # 机械臂客户端
├── board_to_robot.py        # 棋盘坐标到机器人坐标转换
├── ik.py                    # 逆运动学求解器
├── detector.py             # YOLO视觉棋子检测
├── stockfish_server.py      # Stockfish HTTP API服务器
├── chess.pt                # YOLO棋子检测模型
├── Stockfish-Python-API/   # Stockfish Python接口
│   └── stockfish_bin/stockfish  # Stockfish引擎
└── docs/                   # 文档目录
```

## 核心模块

### 1. chess_ui.py - 棋盘UI

**功能**：
- Tkinter图形界面显示8x8棋盘
- 支持鼠标点击走棋
- 集成Stockfish AI（depth=40）
- 支持白方/黑方选边，棋盘180度旋转
- 王车易位、兵升变、吃子检测
- TCP连接机械臂服务器发送走法指令

**主要类**：
- `ChessUI` - 主窗口类

**关键方法**：
- `_ai_move()` - 获取AI走法并更新棋盘
- `_do_move()` - 执行移动
- `_do_castling()` - 执行王车易位
- `_send_to_arm()` - 发送指令到机械臂

**命令格式**：
```
MOVE,x,y,z,x2,y2,z2,is_capture,move_desc
```

### 2. chess_arm_server.py - 机械臂服务器

**功能**：
- 运行在树莓派上监听TCP端口5001
- 接收走法指令并控制机械臂执行
- 夹爪控制（舵机6）
- 两步下降取棋/放棋
- 支持不同棋子不同高度和夹爪角度

**棋子参数**：
| 棋子 | 高度 | 夹爪角度 |
|------|------|----------|
| 兵(P) | 4.0 | 161 |
| 车(R) | 4.0 | 157 |
| 马(N) | 5.2 | 164 |
| 象(B) | 6.5 | 161 |
| 王(K) | 7.2 | 152 |
| 后(Q) | 6.0 | 153 |

**走法执行序列**：
1. 初始位置
2. 移动到目标上方（safe_height=13）
3. 一次下降到9.0
4. 二次下降到piece_height
5. 夹取
6. 抬升到目标上方
7. 移动到放置位置上方
8. 下降到放置位置
9. 放置
10. 抬升
11. 返回初始位置

**Z坐标校正**：
```
z_corrected = z + k * sqrt(x^2 + y^2)
```
当前k值：0.15

### 3. board_to_robot.py - 坐标转换

**功能**：
- 将棋盘UCI坐标（如e2）转换为机器人坐标
- 支持标定参数配置

**计算公式**：
```python
x = board_origin_robot[0] + (col + 0.55) * GRID_SIZE_CM * board_dir_x[0]
y = board_origin_robot[1] + (row + 0.55) * GRID_SIZE_CM * board_dir_y[1]
z = z_height
```

**默认参数**：
- `GRID_SIZE_CM = 3.1`
- `board_origin_robot = [-12.4, 3, 2.0]`
- `board_dir_x = [1, 0, 0]`
- `board_dir_y = [0, 1, 0]`

### 4. ik.py - 逆运动学求解

**功能**：
- 4自由度机械臂逆运动学求解
- 输入：x, y, z, alpha（末端姿态角）
- 输出：j1, j2, j3, j4 四个关节角度

**参数**：
- A1=12.1, A2=12.1, A3=8.4, A4=12.6, A4=18.8
- P=5（Y轴偏移）

**约束**：
- 关节角度范围：-30度到180度
- alpha范围：90度到180度（自动调整）

### 5. detector.py - 视觉检测

**功能**：
- YOLO模型实时检测棋盘上的棋子
- 绿色点=白棋，红色点=黑棋
- 输出FEN格式局面

**参数**：
- `--conf` - 置信度阈值（默认0.2）
- `--model` - YOLO模型路径（默认chess.pt）
- 分辨率：640x480

## 网络配置

| 服务 | IP | 端口 |
|------|-----|------|
| 机械臂服务器 | 192.168.137.60 | 5001 |
| Stockfish API | localhost | 8080 |

## 启动顺序

1. 启动机械臂服务器（树莓派）：
   ```bash
   python3 chess_arm_server.py
   ```

2. 启动Stockfish API服务器：
   ```bash
   python3 stockfish_server.py
   ```

3. 启动棋盘UI：
   ```bash
   python3 chess_ui.py
   ```

4. （可选）启动视觉检测：
   ```bash
   python3 detector.py --conf 0.2
   ```

## 使用说明

### UI操作
- 点击"选边"选择执白或执黑
- 点击"AI走法"获取AI建议
- 点击"执行走法"发送指令到机械臂
- "王车易位"按钮可进入手动走棋模式（连续走两步）
- "悔棋"撤销上一回合
- "重置"恢复初始局面

### 机械臂操作
- 点击"连接机械臂"输入树莓派IP
- UI自动发送MOVE指令
- 格式：`MOVE,x,y,z,x2,y2,z2,is_capture,move_desc`

## 已知问题

1. 执黑时王和后位置在UI中显示可能需要确认
2. Z坐标需要根据实际测试调整z_correction_factor
3. 视觉检测棋盘边界参数需要根据实际标定调整

## 依赖

- Python 3.7+
- tkinter（Python内置）
- numpy
- chess（python-chess库）
- ultralytics（YOLO）
- OpenCV

## 作者

项目创建者：AHEQIRUI