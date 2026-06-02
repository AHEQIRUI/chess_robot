#!/usr/bin/env python3
"""
国际象棋坐标转换工具
UCI格式 (e2e4) <-> 数字坐标 (col, row)
col 0-7 = a-h, row 0-7 = rank 1-8 (白方视角)
"""


def numeric_to_uci(col, row):
    """
    将数字坐标转换为UCI格式

    Args:
        col: 列 (0-7 = a-h)
        row: 行 (0-7 = rank 1-8, 白方底线row=0)

    Returns:
        str: 如 'e2', 'a1'
    """
    if 0 <= col <= 7 and 0 <= row <= 7:
        return f"{chr(ord('a') + col)}{row + 1}"
    return "??"


def uci_to_numeric(uci_str):
    """
    将UCI格式转换为数字坐标

    Args:
        uci_str: 如 'e2', 'a1' - chess square notation

    Returns:
        tuple: (col, row) — col 0-7, row 0-7
    """
    if len(uci_str) != 2:
        return None
    col = ord(uci_str[0].lower()) - ord('a')
    try:
        row = int(uci_str[1]) - 1
        if 0 <= col <= 7 and 0 <= row <= 7:
            return (col, row)
    except ValueError:
        pass
    return None


def format_move(from_col, from_row, to_col, to_row):
    """
    格式化走棋为UCI字符串

    Args:
        from_col, from_row: 起始位置
        to_col, to_row: 目标位置

    Returns:
        str: 如 'e2e4'
    """
    return numeric_to_uci(from_col, from_row) + numeric_to_uci(to_col, to_row)


def parse_move(move_str):
    """
    解析UCI走法字符串

    Args:
        move_str: 如 'e2e4'

    Returns:
        tuple: ((from_col, from_row), (to_col, to_row)) 或 None
    """
    if len(move_str) < 4:
        return None
    from_pos = uci_to_numeric(move_str[:2])
    to_pos = uci_to_numeric(move_str[2:4])
    if from_pos and to_pos:
        return (from_pos, to_pos)
    return None


if __name__ == '__main__':
    print("坐标转换测试:")
    print(f"  numeric_to_uci(4, 1) = {numeric_to_uci(4, 1)}")  # e2
    print(f"  numeric_to_uci(4, 3) = {numeric_to_uci(4, 3)}")  # e4
    print(f"  numeric_to_uci(0, 0) = {numeric_to_uci(0, 0)}")  # a1
    print(f"  numeric_to_uci(7, 7) = {numeric_to_uci(7, 7)}")  # h8
    print(f"  uci_to_numeric('e2') = {uci_to_numeric('e2')}")
    print(f"  uci_to_numeric('h8') = {uci_to_numeric('h8')}")
    print(f"  format_move(4, 1, 4, 3) = {format_move(4, 1, 4, 3)}")
    print(f"  parse_move('e2e4') = {parse_move('e2e4')}")
    print(f"  parse_move('g1f3') = {parse_move('g1f3')}")
