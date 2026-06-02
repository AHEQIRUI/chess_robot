#!/usr/bin/env python3
"""国际象棋UI - Python本地版本，集成Stockfish AI"""

import sys
import json
import socket
import random
import tkinter as tk
from tkinter import messagebox, simpledialog
sys.path.insert(0, 'Stockfish-Python-API')
from stockfish_api import Stockfish
sys.path.insert(0, '.')
from board_to_robot import BoardToRobotMapper
import chess

BIN = 'Stockfish-Python-API/stockfish_bin/stockfish'

# 棋子SVG图形（简化为Unicode字符显示）
PIECES = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',
}

PIECE_NAMES = {
    'K': '王', 'Q': '后', 'R': '车', 'B': '象', 'N': '马', 'P': '兵',
    'k': '王', 'q': '后', 'r': '车', 'b': '象', 'n': '马', 'p': '兵',
}

INITIAL_POSITION = [
    ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
    ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
    ['', '', '', '', '', '', '', ''],
    ['', '', '', '', '', '', '', ''],
    ['', '', '', '', '', '', '', ''],
    ['', '', '', '', '', '', '', ''],
    ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
    ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
]

COLORS = {
    'light': '#f0d9b5',
    'dark': '#b58863',
    'selected': '#7f7',
}

class ChessUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("国际象棋")
        self.root.resizable(False, False)
        self.root.minsize(720,960 )

        self.board_state = [row[:] for row in INITIAL_POSITION]
        self.selected_square = None
        self.current_turn = 'white'
        self.move_history = []
        self.castling_rights = {'K': True, 'Q': True, 'k': True, 'q': True}
        self.mapper = BoardToRobotMapper()
        self.arm_host = '192.168.137.60'
        self.arm_port = 5001
        self.arm_connected = False
        self.arm_socket = None
        self.last_is_capture = False  # 保存上次AI走法是否吃子
        self.last_move_desc = ""  # 保存上次走棋描述
        self.manual_move_count = 0  # 手动走棋计数
        self.manual_move_mode = False  # 手动走棋模式

        # 选边
        self.player_color = self._ask_player_color()
        if self.player_color == 'black':
            # 黑方视角，旋转棋盘
            self.board_flipped = True
        else:
            self.board_flipped = False

        self._create_widgets()
        self._render_board()
        self._update_fen()

    def _ask_player_color(self):
        """询问玩家选择执白还是执黑"""
        result = messagebox.askquestion("选边", "是否选择黑方？\n\n选择'是'则执黑（后手），选择'否'则执白（先手）")
        return 'black' if result == 'yes' else 'white'

    def _flip_uci(self, uci):
        """将UCI坐标翻转180度（用于黑方视角）"""
        if not self.board_flipped:
            return uci

        col = ord(uci[0]) - 97  # a-h -> 0-7
        row = int(uci[1])  # 1-8

        flipped_col = 7 - col
        flipped_row = 9 - row  # 1->8, 2->7, etc.

        return chr(flipped_col + 97) + str(flipped_row)

    def _create_widgets(self):
        # 棋盘
        self.board_frame = tk.Frame(self.root)
        self.board_frame.grid(row=0, column=0, padx=10, pady=10)

        self.squares = []
        for row in range(8):
            row_squares = []
            for col in range(8):
                is_light = (row + col) % 2 == 0
                bg = COLORS['light'] if is_light else COLORS['dark']

                btn = tk.Button(
                    self.board_frame,
                    width=4,
                    height=2,
                    font=('Arial', 20),
                    bg=bg,
                    relief=tk.RIDGE,
                    command=lambda r=row, c=col: self._on_square_click(r, c)
                )
                btn.grid(row=row, column=col)
                row_squares.append(btn)
            self.squares.append(row_squares)

        # 控制按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.grid(row=1, column=0, pady=5)

        tk.Button(btn_frame, text="悔棋", command=self._undo_move).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="AI走法", command=self._ai_move).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="执行走法", command=self._execute_arm_move).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="重置", command=self._reset).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="连接机械臂", command=self._connect_arm).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="王车易位", command=self._do_castling_ui).pack(side=tk.LEFT, padx=2)

        # FEN显示
        fen_frame = tk.Frame(self.root)
        fen_frame.grid(row=2, column=0, pady=5, padx=10, sticky='ew')

        tk.Label(fen_frame, text="FEN:").pack(side=tk.LEFT)
        self.fen_entry = tk.Entry(fen_frame, width=50, font=('Courier', 10))
        self.fen_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(fen_frame, text="载入", command=self._load_fen).pack(side=tk.LEFT, padx=2)

        # 状态栏
        color_text = "白方（先手）" if self.player_color == 'white' else "黑方（后手）"
        self.status_label = tk.Label(self.root, text=f"{color_text} - 白方回合", anchor='w')
        self.status_label.grid(row=3, column=0, padx=10, sticky='w')

        # AI走法显示
        self.ai_move_label = tk.Label(self.root, text="", anchor='w', fg='#888')
        self.ai_move_label.grid(row=4, column=0, padx=10, sticky='w')

        # 连接状态
        self.arm_status_label = tk.Label(self.root, text="机械臂: 未连接", anchor='w', fg='#888')
        self.arm_status_label.grid(row=5, column=0, padx=10, sticky='w')

        # 发送给机械臂的命令
        self.arm_cmd_label = tk.Label(self.root, text="", anchor='w', fg='#00a', font=('Courier', 9))
        self.arm_cmd_label.grid(row=6, column=0, padx=10, sticky='w')

        # 绑定回车键到载入FEN
        self.fen_entry.bind('<Return>', lambda e: self._load_fen())

    def _render_board(self):
        for row in range(8):
            for col in range(8):
                # 根据视角计算实际显示的行和列
                if self.board_flipped:
                    display_row = 7 - row
                    display_col = 7 - col
                else:
                    display_row = row
                    display_col = col

                piece = self.board_state[display_row][display_col]
                btn = self.squares[row][col]

                # 清除选中状态
                btn.configure(relief=tk.RIDGE)

                if piece:
                    # 白棋用白色，黑棋用黑色
                    color = '#fff' if piece.isupper() else '#000'
                    btn.configure(text=PIECES.get(piece, ''), fg=color)
                else:
                    btn.configure(text='', fg='#000')

        # 高亮选中（转换为显示视角）
        if self.selected_square:
            r, c = self.selected_square
            if self.board_flipped:
                r, c = 7 - r, 7 - c
            self.squares[r][c].configure(relief=tk.SUNKEN)

    def _update_fen(self):
        fen = self._generate_fen()
        self.fen_entry.delete(0, tk.END)
        self.fen_entry.insert(0, fen)

        turn_text = "白方回合" if self.current_turn == 'white' else "黑方回合"
        color_text = "白方（先手）" if self.player_color == 'white' else "黑方（后手）"
        self.status_label.configure(text=f"{color_text} - {turn_text}")

    def _generate_fen(self):
        fen = ''
        for row in range(8):
            empty_count = 0
            for col in range(8):
                piece = self.board_state[row][col]
                if piece == '':
                    empty_count += 1
                else:
                    if empty_count > 0:
                        fen += str(empty_count)
                        empty_count = 0
                    fen += piece
            if empty_count > 0:
                fen += str(empty_count)
            if row < 7:
                fen += '/'

        side = 'w' if self.current_turn == 'white' else 'b'
        fen += f' {side} KQkq'
        return fen

    def _load_fen(self):
        fen = self.fen_entry.get().strip()
        if not fen:
            return

        try:
            parts = fen.split()
            position = parts[0]
            side = parts[1] if len(parts) > 1 else 'w'
            castling = parts[2] if len(parts) > 2 else 'KQkq'

            # 解析局面
            rows = position.split('/')
            if len(rows) != 8:
                raise ValueError("Invalid FEN: must have 8 ranks")

            new_state = []
            for row_str in rows:
                row = []
                for char in row_str:
                    if char.isdigit():
                        row.extend([''] * int(char))
                    else:
                        row.append(char)
                if len(row) != 8:
                    raise ValueError("Invalid FEN: rank must have 8 columns")
                new_state.append(row)

            self.board_state = new_state
            self.current_turn = 'white' if side == 'w' else 'black'

            # 解析易位权利
            self.castling_rights = {'K': 'K' in castling, 'Q': 'Q' in castling,
                                    'k': 'k' in castling, 'q': 'q' in castling}

            self.selected_square = None
            self.move_history = []
            self._render_board()
            self._update_fen()

        except Exception as e:
            messagebox.showerror("FEN错误", f"无法解析FEN码:\n{e}")

    def _on_square_click(self, row, col):
        # 转换为内部坐标
        if self.board_flipped:
            row, col = 7 - row, 7 - col

        piece = self.board_state[row][col]

        if self.selected_square is None:
            # 无选中，选择己方棋子
            if piece and self._get_piece_color(piece) == self.current_turn:
                self.selected_square = (row, col)
                self._render_board()
        else:
            from_row, from_col = self.selected_square
            from_piece = self.board_state[from_row][from_col]

            if (row, col) == (from_row, from_col):
                # 点击同一格，取消选中
                self.selected_square = None
                self._render_board()
            elif piece and self._get_piece_color(piece) == self.current_turn:
                # 点击另一枚己方棋子，可能王车易位
                if from_piece in ('K', 'k') and abs(col - from_col) == 2:
                    side = 'K' if col > from_col else 'Q'
                    if self._can_castle(self.current_turn, side):
                        self._do_castling(self.current_turn, side)
                        self.selected_square = None
                        return

                self.selected_square = (row, col)
                self._render_board()
            else:
                # 移动棋子
                self._do_move(from_row, from_col, row, col)
                self.selected_square = None

    def _get_piece_color(self, piece):
        if not piece:
            return None
        return 'white' if piece.isupper() else 'black'

    def _can_castle(self, color, side):
        row = 7 if color == 'white' else 0
        king = 'K' if color == 'white' else 'k'
        rook = 'R' if color == 'white' else 'r'

        if self.board_state[row][4] != king or self.board_state[row][7] != rook:
            return False

        right = 'K' if color == 'white' and side == 'K' else \
                'Q' if color == 'white' and side == 'Q' else \
                'k' if color == 'black' and side == 'K' else 'q'
        if not self.castling_rights.get(right, False):
            return False

        if side == 'K':
            if self.board_state[row][5] != '' or self.board_state[row][6] != '':
                return False
        else:
            if self.board_state[row][1] != '' or self.board_state[row][2] != '' or self.board_state[row][3] != '':
                return False

        return True

    def _do_castling_ui(self):
        """手动走两步模式"""
        self.manual_move_mode = True
        self.manual_move_count = 0
        self.status_label.configure(text=f"{self.player_color} - 手动走棋模式 (剩余{2 - self.manual_move_count}步)", fg='#f00')
        self._update_fen()

    def _needs_promotion(self, piece, row):
        if piece not in ('P', 'p'):
            return False
        return (piece == 'P' and row == 0) or (piece == 'p' and row == 7)

    def _do_move(self, from_row, from_col, to_row, to_col):
        from_piece = self.board_state[from_row][from_col]
        to_piece = self.board_state[to_row][to_col]

        # 记录历史
        self.move_history.append({
            'from': {'row': from_row, 'col': from_col},
            'to': {'row': to_row, 'col': to_col},
            'captured': to_piece,
            'prev_turn': self.current_turn,
            'prev_castling': dict(self.castling_rights)
        })

        # 更新易位权利
        if to_piece in ('R', 'r'):
            if to_row == 7 and to_col == 0: self.castling_rights['Q'] = False
            if to_row == 7 and to_col == 7: self.castling_rights['K'] = False
            if to_row == 0 and to_col == 0: self.castling_rights['q'] = False
            if to_row == 0 and to_col == 7: self.castling_rights['k'] = False

        if from_piece in ('K',):
            self.castling_rights['K'] = False
            self.castling_rights['Q'] = False
        if from_piece in ('k',):
            self.castling_rights['k'] = False
            self.castling_rights['q'] = False
        if from_piece == 'R':
            if from_row == 7 and from_col == 0: self.castling_rights['Q'] = False
            if from_row == 7 and from_col == 7: self.castling_rights['K'] = False
        if from_piece == 'r':
            if from_row == 0 and from_col == 0: self.castling_rights['q'] = False
            if from_row == 0 and from_col == 7: self.castling_rights['k'] = False

        # 移动棋子
        self.board_state[to_row][to_col] = from_piece
        self.board_state[from_row][from_col] = ''

        # 检查升变
        if self._needs_promotion(from_piece, to_row):
            self._show_promotion_dialog(to_row, to_col)
            return

        # 切换回合
        self.current_turn = 'black' if self.current_turn == 'white' else 'white'
        self._render_board()
        self._update_fen()

        # 手动走棋模式计数
        if self.manual_move_mode:
            self.manual_move_count += 1
            if self.manual_move_count >= 2:
                self.manual_move_mode = False
                self.status_label.configure(text=f"{self.player_color} - {'白方' if self.current_turn == 'white' else '黑方'}回合", fg='#000')

    def _show_promotion_dialog(self, row, col):
        def on_select(piece):
            self.board_state[row][col] = piece
            self.current_turn = 'black' if self.current_turn == 'white' else 'white'
            self._render_board()
            self._update_fen()
            dialog.destroy()

        dialog = tk.Toplevel(self.root)
        dialog.title("升变选择")
        dialog.grab_set()

        tk.Label(dialog, text="选择升变棋子:").pack(pady=5)

        color = 'white' if self.board_state[row][col] == 'P' else 'black'
        pieces = ['Q', 'R', 'B', 'N'] if color == 'white' else ['q', 'r', 'b', 'n']
        names = ['后', '车', '象', '马'] if color == 'white' else ['后', '车', '象', '马']

        frame = tk.Frame(dialog)
        frame.pack(pady=5)
        for p, name in zip(pieces, names):
            tk.Button(frame, text=f"{PIECES[p]} {name}",
                      font=('Arial', 14),
                      command=lambda p=p: on_select(p)).pack(side=tk.LEFT, padx=5)

    def _undo_move(self):
        if not self.move_history:
            return

        last_move = self.move_history.pop()

        if last_move.get('type') == 'castling':
            row = 7 if last_move['color'] == 'white' else 0
            if last_move['side'] == 'K':
                self.board_state[row][4] = self.board_state[row][6]
                self.board_state[row][6] = ''
                self.board_state[row][7] = self.board_state[row][5]
                self.board_state[row][5] = ''
            else:
                self.board_state[row][4] = self.board_state[row][2]
                self.board_state[row][2] = ''
                self.board_state[row][0] = self.board_state[row][3]
                self.board_state[row][3] = ''
            self.castling_rights = last_move['prev_castling']
        else:
            self.board_state[last_move['from']['row']][last_move['from']['col']] = \
                self.board_state[last_move['to']['row']][last_move['to']['col']]
            self.board_state[last_move['to']['row']][last_move['to']['col']] = last_move['captured']
            self.castling_rights = last_move['prev_castling']

        self.current_turn = last_move['prev_turn']
        self.selected_square = None
        self._render_board()
        self._update_fen()

    def _reset(self):
        self.board_state = [row[:] for row in INITIAL_POSITION]
        self.selected_square = None
        self.current_turn = 'white'
        self.move_history = []
        self.castling_rights = {'K': True, 'Q': True, 'k': True, 'q': True}
        self._render_board()
        self._update_fen()

    def _update_arm_status(self):
        if self.arm_connected:
            self.arm_status_label.configure(text=f"机械臂: 已连接 {self.arm_host}:{self.arm_port}", fg='#0a0')
        else:
            self.arm_status_label.configure(text="机械臂: 未连接", fg='#888')

    def _connect_arm(self):
        host = simpledialog.askstring("连接机械臂", "输入树莓派IP地址:", initialvalue=self.arm_host)
        if not host:
            return
        port = simpledialog.askinteger("连接机械臂", "输入端口:", initialvalue=self.arm_port)
        if not port:
            return

        self.arm_host = host
        self.arm_port = port

        try:
            self.arm_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.arm_socket.settimeout(30)
            self.arm_socket.connect((self.arm_host, self.arm_port))
            self.arm_connected = True
            self._update_arm_status()
            messagebox.showinfo("连接", f"已连接到机械臂 {self.arm_host}:{self.arm_port}")
        except Exception as e:
            self.arm_connected = False
            self.arm_socket = None
            self._update_arm_status()
            messagebox.showerror("连接失败", f"无法连接到机械臂:\n{e}")

    def _send_to_arm(self, from_pos, to_pos, is_capture=False, move_desc=""):
        if not self.arm_connected or self.arm_socket is None:
            try:
                self.arm_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.arm_socket.settimeout(30)
                self.arm_socket.connect((self.arm_host, self.arm_port))
                self.arm_connected = True
                self._update_arm_status()
            except Exception as e:
                messagebox.showwarning("未连接", f"请先连接机械臂:\n{e}")
                return False

        try:
            cmd = f"MOVE,{from_pos[0]:.1f},{from_pos[1]:.1f},{from_pos[2]:.1f},{to_pos[0]:.1f},{to_pos[1]:.1f},{to_pos[2]:.1f},{str(is_capture).lower()}"
            if move_desc:
                cmd += f",{move_desc}"

            # 在UI显示发送的命令
            self.arm_cmd_label.configure(text=f"> {cmd}")

            self.arm_socket.sendall((cmd + '\n').encode('utf-8'))
            self.arm_socket.settimeout(120)
            response = self.arm_socket.recv(1024).decode('utf-8').strip()
            if response == "OK":
                return True
            else:
                messagebox.showerror("执行失败", f"机械臂响应: {response}")
                self.arm_connected = False
                self.arm_socket.close()
                self.arm_socket = None
                self._update_arm_status()
                return False
        except Exception as e:
            messagebox.showerror("发送失败", f"无法发送指令:\n{e}")
            self.arm_connected = False
            if self.arm_socket:
                self.arm_socket.close()
            self.arm_socket = None
            self._update_arm_status()
            return False

    def _execute_arm_move(self):
        """执行已显示的AI走法"""
        text = self.ai_move_label.cget('text')
        if not text or 'Robot:' not in text:
            messagebox.showinfo("提示", "请先点击AI走法获取走法")
            return

        import re
        match = re.search(r'\[([-\d.]+),\s+([-\d.]+),\s+([-\d.]+)\]\s*->\s*\[([-\d.]+),\s+([-\d.]+),\s+([-\d.]+)\]', text)
        if not match:
            messagebox.showerror("错误", f"无法解析坐标: {text}")
            return

        from_pos = [float(match.group(i)) for i in range(1, 4)]
        to_pos = [float(match.group(i)) for i in range(4, 7)]

        # 解析走法信息
        move_line = text.split('\n')[0]  # AI: e2 -> e4
        from_sq = move_line.split('→')[0].replace('AI:', '').strip()
        to_sq = move_line.split('→')[1].strip().split()[0]

        # 黑方视角时转换回内部坐标
        internal_from_sq = self._flip_uci(from_sq) if self.board_flipped else from_sq
        internal_to_sq = self._flip_uci(to_sq) if self.board_flipped else to_sq

        from_row = 8 - int(internal_from_sq[1])
        from_col = ord(internal_from_sq[0]) - 97
        to_row = 8 - int(internal_to_sq[1])
        to_col = ord(internal_to_sq[0]) - 97

        # 使用AI走法时保存的吃子状态和走棋描述
        is_capture = self.last_is_capture
        move_desc = self.last_move_desc

        # 构建命令并提前显示
        cmd = f"MOVE,{from_pos[0]:.1f},{from_pos[1]:.1f},{from_pos[2]:.1f},{to_pos[0]:.1f},{to_pos[1]:.1f},{to_pos[2]:.1f},{str(is_capture).lower()}"
        if move_desc:
            cmd += f",{move_desc}"
        self.arm_cmd_label.configure(text=f"> {cmd}")

        if self._send_to_arm(from_pos, to_pos, is_capture, move_desc):
            messagebox.showinfo("成功", f"机械臂走棋完成\n{move_desc}")

    def _ai_move(self):
        fen = self._generate_fen()

        try:
            with Stockfish(BIN, depth=25) as engine:
                engine.set_fen(fen)
                move = engine.get_best_move(depth=25)

                # 如果没有AI走法，从合法着法中随机选一步
                if not move:
                    board = chess.Board(fen)
                    legal_moves = list(board.legal_moves)
                    if legal_moves:
                        move = random.choice(legal_moves).uci()
                        print(f"[!] AI无解，随机选择: {move}")
                    else:
                        messagebox.showinfo("AI", "没有合法走法")
                        return

                from_sq = move[:2]
                to_sq = move[2:4]

                # 黑方视角时翻转坐标
                display_from_sq = self._flip_uci(from_sq) if self.board_flipped else from_sq
                display_to_sq = self._flip_uci(to_sq) if self.board_flipped else to_sq

                from_row = 8 - int(from_sq[1])
                from_col = ord(from_sq[0]) - 97
                to_row = 8 - int(to_sq[1])
                to_col = ord(to_sq[0]) - 97

                # 计算机械臂坐标（使用翻转后的UCI坐标以匹配视觉坐标）
                robot_from_sq = display_from_sq if self.board_flipped else from_sq
                robot_to_sq = display_to_sq if self.board_flipped else to_sq
                from_pos = self.mapper.board_to_robot_from_uci(robot_from_sq, z_height=8.0)
                to_pos = self.mapper.board_to_robot_from_uci(robot_to_sq, z_height=8.0)

                # 提前获取棋子信息用于显示
                from_piece = self.board_state[from_row][from_col]
                to_piece = self.board_state[to_row][to_col]
                is_capture = bool(to_piece)
                piece_name = PIECE_NAMES.get(from_piece, from_piece)
                color_name = '白方' if from_piece.isupper() else '黑方'

                # 立即显示AI走法（使用翻转后的坐标）
                capture_text = " 吃子" if is_capture else ""
                move_display = f"AI: {display_from_sq} → {display_to_sq}{capture_text}"
                move_display += f"\n{color_name}{piece_name}{'吃子' if is_capture else '移动'}"
                promotion = move[4:] if len(move) > 4 else ''
                if promotion:
                    promotion_name = {'q': '后', 'r': '车', 'b': '象', 'n': '马'}.get(promotion.lower(), promotion)
                    move_display += f" 升变: {promotion_name}"
                move_display += f"\nRobot: [{from_pos[0]:.1f}, {from_pos[1]:.1f}, {from_pos[2]:.1f}] -> [{to_pos[0]:.1f}, {to_pos[1]:.1f}, {to_pos[2]:.1f}]"
                self.ai_move_label.configure(text=move_display)

                # 构建移动描述
                move_desc = f"{color_name}{piece_name}"
                if is_capture:
                    cap_name = PIECE_NAMES.get(to_piece, to_piece)
                    cap_color = '白方' if to_piece.isupper() else '黑方'
                    move_desc += f"吃{cap_color}{cap_name}"
                else:
                    move_desc += "移动"
                move_desc += f" ({display_from_sq} → {display_to_sq})"

                cmd = f"MOVE,{from_pos[0]:.1f},{from_pos[1]:.1f},{from_pos[2]:.1f},{to_pos[0]:.1f},{to_pos[1]:.1f},{to_pos[2]:.1f},{str(is_capture).lower()}"
                if move_desc:
                    cmd += f",{move_desc}"
                self.arm_cmd_label.configure(text=f"> {cmd}")

                # 保存吃子状态和走棋描述供后续执行使用
                self.last_is_capture = is_capture
                self.last_move_desc = move_desc

                # 执行AI走法
                self.selected_square = (from_row, from_col)
                self._render_board()
                self.root.update()
                self.root.after(500)  # 延迟以显示选中

                # 检测王车易位
                from_piece_check = self.board_state[from_row][from_col]
                if from_piece_check in ('K', 'k') and abs(to_col - from_col) == 2:
                    # 王车易位
                    side = 'K' if to_col > from_col else 'Q'
                    color = 'white' if from_piece_check.isupper() else 'black'
                    self._do_castling(color, side)
                else:
                    self._do_move(from_row, from_col, to_row, to_col)

                # 处理升变（AI通常升变为后）
                if promotion:
                    promoted = promotion.upper() if self.board_state[to_row][to_col].isupper() else promotion.lower()
                    self.board_state[to_row][to_col] = promoted
                    self._render_board()

        except Exception as e:
            messagebox.showerror("AI错误", f"无法获取AI走法:\n{e}")

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = ChessUI()
    app.run()
