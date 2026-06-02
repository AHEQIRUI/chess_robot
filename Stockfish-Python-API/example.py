#!/usr/bin/env python3
"""
Stockfish Python API 使用示例
"""

from stockfish_api import Stockfish


def basic_example():
    """基础用法：通过 FEN 获取最佳走法"""
    engine = Stockfish('./stockfish_bin/stockfish', depth=15)

    # 设置 FEN 局面（开局）
    fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    engine.set_fen(fen)

    # 获取最佳走法
    best_move = engine.get_best_move()
    print(f"开局最佳走法: {best_move}")

    engine.close()


def chain_example():
    """链式调用"""
    with Stockfish('./stockfish_bin/stockfish', depth=15) as engine:
        best_move = (
            engine
            .set_fen('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
            .get_best_move()
        )
        print(f"开局最佳走法: {best_move}")


def startpos_example():
    """从起始局面走子"""
    engine = Stockfish('./stockfish_bin/stockfish', depth=15)

    # 1. e4
    engine.set_startpos(moves=['e2e4'])
    print(f"1. e4 后最佳走法: {engine.get_best_move(depth=15)}")

    # 1. e4 e5
    engine.set_startpos(moves=['e2e4', 'e7e5'])
    print(f"1. e4 e5 后最佳走法: {engine.get_best_move(depth=15)}")

    engine.close()


def move_info_example():
    """获取详细走法信息"""
    engine = Stockfish('./stockfish_bin/stockfish', depth=15)

    engine.set_fen('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
    info = engine.get_move_info(depth=15)

    print(f"最佳走法: {info.best_move}")
    print(f"后续着想: {info.ponder}")
    print(f"搜索深度: {info.depth}")
    print(f"评分 (cp): {info.score}")
    print(f"搜索节点数: {info.nodes}")
    print(f"每秒节点数: {info.nps}")
    print(f"搜索时间 (ms): {info.time_ms}")

    engine.close()


def time_control_example():
    """限时搜索（毫秒）"""
    engine = Stockfish('./stockfish_bin/stockfish')

    engine.set_fen('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')

    # 搜索 1000ms
    best_move = engine.get_best_move(movetime_ms=1000)
    print(f"限时 1 秒后的走法: {best_move}")

    engine.close()


def set_options_example():
    """设置引擎选项"""
    engine = Stockfish('./stockfish_bin/stockfish', depth=15)

    # 设置线程数
    engine.set_option('Threads', 4)

    # 设置哈希大小 (MB)
    engine.set_option('Hash', 256)

    # 设置是否思考（ponder）
    engine.set_option('Ponder', False)

    engine.set_fen('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
    print(f"最佳走法: {engine.get_best_move(depth=15)}")

    engine.close()


def engine_info_example():
    """获取引擎信息"""
    engine = Stockfish('./stockfish_bin/stockfish')
    info = engine.get_engine_info()
    print(f"引擎名称: {info.get('name', 'Unknown')}")
    print(f"作者: {info.get('author', 'Unknown')}")
    engine.close()


if __name__ == '__main__':
    print("=" * 50)
    print("1. 基础示例")
    print("=" * 50)
    basic_example()

    print("\n" + "=" * 50)
    print("2. 链式调用示例")
    print("=" * 50)
    chain_example()

    print("\n" + "=" * 50)
    print("3. 起始局面走子示例")
    print("=" * 50)
    startpos_example()

    print("\n" + "=" * 50)
    print("4. 详细走法信息示例")
    print("=" * 50)
    move_info_example()

    print("\n" + "=" * 50)
    print("5. 限时搜索示例")
    print("=" * 50)
    time_control_example()

    print("\n" + "=" * 50)
    print("6. 引擎信息示例")
    print("=" * 50)
    engine_info_example()