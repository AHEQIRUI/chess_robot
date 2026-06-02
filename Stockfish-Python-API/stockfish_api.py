#!/usr/bin/env python3
"""
Stockfish Python API Wrapper
通过 FEN 码或走子序列调用 Stockfish 引擎

依赖: Python 3.7+
无需额外安装依赖

用法:
    from stockfish_api import Stockfish

    with Stockfish('./stockfish_bin/stockfish') as engine:
        engine.set_fen('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
        best_move = engine.get_best_move(depth=20)
"""

import subprocess
import threading
import queue
import time
from dataclasses import dataclass
from typing import Optional, List, Union


@dataclass
class MoveInfo:
    """走法信息"""
    best_move: str
    ponder: Optional[str] = None
    depth: Optional[int] = None
    score: Optional[int] = None
    nodes: Optional[int] = None
    nps: Optional[int] = None
    time_ms: Optional[int] = None


class Stockfish:
    """
    Stockfish 引擎 Python 封装

    使用示例:
        engine = Stockfish('./stockfish')
        engine.set_fen('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
        result = engine.get_best_move(depth=20)

    支持上下文管理器:
        with Stockfish('./stockfish') as engine:
            engine.set_fen('...')
            print(engine.get_best_move())
    """

    def __init__(self, executable_path: str = './stockfish', depth: int = 15):
        """
        初始化 Stockfish 引擎

        Args:
            executable_path: stockfish 可执行文件路径
            depth: 默认搜索深度
        """
        self.executable_path = executable_path
        self.default_depth = depth
        self._engine: Optional[subprocess.Popen] = None
        self._output_queue: queue.Queue = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._start_engine()

    def _start_engine(self):
        """启动引擎进程"""
        self._engine = subprocess.Popen(
            self.executable_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # 启动后台读取线程
        self._reader_thread = threading.Thread(
            target=self._read_output,
            daemon=True
        )
        self._reader_thread.start()

        # 初始化 UCI
        self._send_command('uci')
        self._wait_for('uciok')
        self._send_command('isready')
        self._wait_for('readyok')

    def _read_output(self):
        """后台线程持续读取输出到队列"""
        try:
            for line in iter(self._engine.stdout.readline, ''):
                if not line:
                    break
                self._output_queue.put(line.strip())
        except:
            pass

    def _send_command(self, cmd: str):
        """发送命令到引擎"""
        if self._engine:
            self._engine.stdin.write(cmd + '\n')
            self._engine.stdin.flush()

    def _wait_for(self, keyword: str, timeout: float = 30.0) -> str:
        """等待包含关键词的响应"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                line = self._output_queue.get(timeout=0.1)
                if keyword in line:
                    return line
            except queue.Empty:
                continue
        raise TimeoutError(f"等待 '{keyword}' 超时")

    def _read_until(self, keyword: str, timeout: float = 30.0) -> List[str]:
        """读取直到遇到关键词，返回所有行"""
        lines = []
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                line = self._output_queue.get(timeout=0.1)
                lines.append(line)
                if keyword in line:
                    break
            except queue.Empty:
                continue
        return lines

    def set_fen(self, fen: str) -> 'Stockfish':
        """
        设置 FEN 局面

        Args:
            fen: FEN 格式的局面字符串

        Returns:
            self, 支持链式调用

        示例:
            engine.set_fen('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
        """
        self._send_command(f'position fen {fen}')
        # position 命令不返回 readyok，直接返回
        return self

    def set_startpos(self, moves: Optional[List[str]] = None) -> 'Stockfish':
        """
        设置起始局面

        Args:
            moves: 可选的走子列表，如 ['e2e4', 'd7d5']

        Returns:
            self, 支持链式调用

        示例:
            engine.set_startpos()                    # 空开局
            engine.set_startpos(['e2e4'])            # 1. e4
            engine.set_startpos(['e2e4', 'e7e5'])     # 1. e4 e5
        """
        if moves:
            moves_str = ' '.join(moves)
            self._send_command(f'position startpos moves {moves_str}')
        else:
            self._send_command('position startpos')
        # position 命令不返回 readyok，直接返回
        return self

    def get_best_move(self, depth: Optional[int] = None, movetime_ms: Optional[int] = None) -> Optional[str]:
        """
        获取最佳走法

        Args:
            depth: 搜索深度（优先于 movetime_ms）
            movetime_ms: 搜索时间（毫秒）

        Returns:
            UCI 格式的走法，如 'e2e4'，无合法走法时返回 None

        示例:
            engine.get_best_move(depth=20)   # 搜索 20 层
            engine.get_best_move(movetime_ms=1000)  # 搜索 1 秒
        """
        depth = depth or self.default_depth

        if movetime_ms:
            self._send_command(f'go movetime {movetime_ms}')
        else:
            self._send_command(f'go depth {depth}')

        lines = self._read_until('bestmove')

        for line in lines:
            if line.startswith('bestmove'):
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1]
        return None

    def get_move_info(self, depth: Optional[int] = None, movetime_ms: Optional[int] = None) -> MoveInfo:
        """
        获取详细的走法信息

        Args:
            depth: 搜索深度（优先于 movetime_ms）
            movetime_ms: 搜索时间（毫秒）

        Returns:
            MoveInfo 对象，包含最佳走法、后续着想、评分等

        示例:
            info = engine.get_move_info(depth=20)
            print(f"最佳走法: {info.best_move}")
            print(f"评分: {info.score}")
        """
        depth = depth or self.default_depth

        if movetime_ms:
            self._send_command(f'go movetime {movetime_ms}')
        else:
            self._send_command(f'go depth {depth}')

        lines = self._read_until('bestmove')

        info = MoveInfo(best_move='')

        for line in lines:
            if line.startswith('bestmove'):
                parts = line.split()
                info.best_move = parts[1] if len(parts) >= 2 else ''
                info.ponder = parts[3] if len(parts) >= 4 else None
            elif 'depth' in line:
                for part in line.split():
                    if part.isdigit():
                        info.depth = int(part)
                        break
            elif 'score cp' in line:
                try:
                    info.score = int([p for p in line.split() if p.lstrip('-').isdigit()][-1])
                except:
                    pass
            elif 'nodes' in line:
                try:
                    info.nodes = int([p for p in line.split() if p.isdigit()][-1])
                except:
                    pass
            elif 'nps' in line:
                try:
                    info.nps = int([p for p in line.split() if p.isdigit()][-1])
                except:
                    pass
            elif 'time' in line:
                try:
                    info.time_ms = int([p for p in line.split() if p.isdigit()][-1])
                except:
                    pass

        return info

    def set_option(self, name: str, value: Union[str, int, bool]):
        """
        设置 UCI 选项

        Args:
            name: 选项名称
            value: 选项值

        示例:
            engine.set_option('Threads', 4)   # 设置 4 线程
            engine.set_option('Hash', 256)    # 设置 256MB 哈希
            engine.set_option('Ponder', False)  # 关闭思考
        """
        if isinstance(value, bool):
            value = 'true' if value else 'false'
        self._send_command(f'setoption name {name} value {value}')
        self._wait_for('readyok')

    def get_engine_info(self) -> dict:
        """
        获取引擎信息

        Returns:
            包含引擎名称、作者等信息的字典

        示例:
            info = engine.get_engine_info()
            print(f"引擎: {info['name']}")
        """
        self._send_command('uci')
        lines = self._read_until('uciok')

        info = {}
        for line in lines:
            if line.startswith('id name'):
                info['name'] = ' '.join(line.split()[2:])
            elif line.startswith('id author'):
                info['author'] = ' '.join(line.split()[2:])
        return info

    def close(self):
        """关闭引擎进程"""
        if self._engine:
            try:
                self._send_command('quit')
                self._engine.wait(timeout=2)
            except:
                self._engine.kill()
            self._engine = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()