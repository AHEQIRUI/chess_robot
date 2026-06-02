# 国际象棋机械臂控制系统 - 项目交接文档

## 项目信息

| 项目 | 内容 |
|------|------|
| 项目名称 | 国际象棋机械臂控制系统 |
| 创建时间 | 2026-06-02 |
| 维护者 | AHEQIRUI |

## 系统概述

这是一个完整的国际象棋人机对弈系统，用户可以在电脑端下棋，AI（Stockfish）作为对手，机械臂（运行在树莓派上）负责执行真实的棋子移动。

## 硬件配置

### 电脑端
- 运行 `chess_ui.py` 棋盘UI
- 运行 `stockfish_server.py` Stockfish API
- （可选）运行 `detector.py` 视觉检测

### 树莓派端
- 运行 `chess_arm_server.py` 机械臂控制服务器
- 连接4自由度机械臂
- 监听端口：5001

### 机械臂
- 4自由度机械臂（4个舵机 + 夹爪）
- 夹爪连接在舵机6

## 快速开始

### 1. 树莓派端启动

```bash
cd /path/to/project
python3 chess_arm_server.py
```

服务器启动后会：
- 移动机械臂到初始位置
- 张开夹爪
- 监听5001端口

### 2. 电脑端启动UI

```bash
cd /path/to/project
python3 chess_ui.py
```

### 3. 操作流程

1. 弹出选边对话框，选择执白或执黑
2. 点击"连接机械臂"按钮，输入树莓派IP
3. 点击"AI走法"获取AI建议
4. AI走法会显示在UI中
5. 点击"执行走法"发送指令到机械臂
6. 机械臂执行走法

## 棋子参数配置

位于 `chess_arm_server.py`：

```python
# 棋子高度（夹取时的下降高度）
self.piece_heights = {
    'P': 4.0, 'R': 4.0, 'N': 5.2, 'B': 6.5, 'K': 7.2, 'Q': 6.0
}

# 夹爪角度
self.gripper_close_angles = {
    'P': 161, 'R': 157, 'N': 164, 'B': 161, 'K': 152, 'Q': 153
}
```

## Z坐标校正

机械臂在不同位置的实际高度不同，通过以下公式校正：

```python
z_corrected = z + k * sqrt(x**2 + y**2)
# 当前 k = 0.15
```

如需调整，修改 `chess_arm_server.py` 第63行：
```python
self.z_correction_factor = 0.15
```

## 棋盘坐标系统

- 使用UCI坐标（a1-h8）
- a1在棋盘左下角
- 转换公式见 `board_to_robot.py`

## 机械臂执行序列

1. 初始位置 → 目标上方（13cm）
2. 一次下降（9cm）
3. 二次下降（棋子高度）
4. 夹取
5. 抬升
6. 移动到放置位置上方（13cm）
7. 一次下降（9cm）
8. 二次下降（棋子高度）
9. 放置
10. 抬升
11. 返回初始位置

## 常见问题

### 1. 夹爪抓不住棋子
- 检查 `gripper_close_angle` 是否合适
- 可能是棋子高度设置过低

### 2. 棋子位置不准确
- 检查 `z_correction_factor` 值
- 检查 `board_to_robot.py` 中的标定参数

### 3. 机械臂无法到达目标
- 检查IK求解是否有解
- 目标位置可能超出机械臂范围

## 文件传输

需要将以下文件传输到树莓派：
- `chess_arm_server.py`
- `ik.py`
- `Arm_Lib/` 目录（机械臂库）
- `src/` 目录（如需要）
- `ch_src/` 目录（如需要）

## 后续维护

### 调整棋子高度
修改 `piece_heights` 字典

### 添加新棋子
同时修改 `piece_heights` 和 `gripper_close_angles`

### 标定棋盘位置
修改 `board_to_robot.py` 中的：
- `board_origin_robot`
- `board_dir_x`
- `board_dir_y`

