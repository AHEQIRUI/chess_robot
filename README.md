# Chess Robot Arm Control System

An integrated chess human-vs-AI system with Stockfish engine, graphical UI, robotic arm execution, and visual piece detection.

## Features

- **Graphical Chess UI** - Tkinter-based 8x8 board with mouse click moves
- **Stockfish AI** - High-depth chess engine (depth=40) as opponent
- **Robotic Arm Execution** - 4-DOF arm executes moves on real board
- **Visual Detection** - YOLO-based chess piece recognition
- **Castling & Pawn Promotion** - Full chess rule support

## System Architecture

```
┌─────────────────┐     ┌──────────────────────┐
│   chess_ui.py   │────▶│  chess_arm_server.py │
│   (Main/UI)     │TCP  │  (Raspberry Pi:5001)  │
└────────┬────────┘     └──────────────────────┘
         │                         │
         ▼                         ▼
┌─────────────────┐         ┌─────────────┐
│  stockfish      │         │   Robot Arm │
│  (AI Engine)    │         │  (Executes) │
└─────────────────┘         └─────────────┘
```

## Quick Start

### 1. Raspberry Pi - Arm Server

```bash
python3 chess_arm_server.py
```

### 2. PC - Stockfish API

```bash
python3 stockfish_server.py
```

### 3. PC - Chess UI

```bash
python3 chess_ui.py
```

(Optional) Visual detection:

```bash
python3 detector.py --conf 0.2
```

## Network Configuration

| Service | IP | Port |
|---------|-----|------|
| Arm Server | 192.168.137.60 | 5001 |
| Stockfish API | localhost | 8080 |

## Project Structure

| File | Description |
|------|-------------|
| `chess_ui.py` | Main UI, AI opponent, TCP command sender |
| `chess_arm_server.py` | Arm control server (runs on Raspberry Pi) |
| `chess_arm_client.py` | Arm client, TCP communication |
| `board_to_robot.py` | UCI coordinates → robot coordinates |
| `ik.py` | Inverse kinematics (4-DOF) |
| `detector.py` | YOLO visual piece detection |
| `stockfish_server.py` | Stockfish HTTP API server |
| `chess.pt` | YOLO detection model |

## Robot Arm Command Format

```
MOVE,x,y,z,x2,y2,z2,is_capture,move_desc
```

## Piece Parameters

| Piece | Height (cm) | Gripper Angle |
|-------|-------------|---------------|
| Pawn (P/p) | 4.0 | 161 |
| Rook (R/r) | 4.0 | 157 |
| Knight (N/n) | 5.2 | 164 |
| Bishop (B/b) | 6.5 | 161 |
| King (K/k) | 7.2 | 152 |
| Queen (Q/q) | 6.0 | 153 |

## Coordinate System

- **Board**: UCI notation (e2, a1, etc.), a1 at bottom-left
- **Robot coords**: Converted via `board_to_robot.py`
- **Z correction**: `z_corrected = z + 0.15 * sqrt(x² + y²)`
- **IK solver**: `ik.py` - inputs x,y,z,alpha → outputs j1-j4 joint angles

