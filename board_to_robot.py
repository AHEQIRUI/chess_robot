#!/usr/bin/env python3
"""
国际象棋棋盘坐标转机器人坐标模块
8x8棋盘, 格子尺寸3.1cm
将棋盘位置(col, row)转换为机器人工作空间坐标(厘米)
"""

import numpy as np
import json


def _path_exists(path):
    try:
        with open(path): return True
    except: return False


class BoardToRobotMapper:
    """国际象棋棋盘坐标到机器人坐标的映射器"""

    GRID_SIZE_CM = 3.1  # 棋盘格子宽度(厘米), 正方形

    def __init__(self, config_path=None):
        """
        初始化映射器

        Args:
            config_path: 配置文件路径, 包含相机内参
        """
        if config_path is None:
            config_path = 'config/camera_config.json'

        if _path_exists(config_path):
            with open(config_path, 'r') as f:
                calib = json.load(f)
                self.camera_matrix = np.array(calib['camera_matrix'])
                self.dist_coeffs = np.array(calib['dist_coeffs'])
        else:
            self.camera_matrix = np.array([
                [946.82, 0, 416.11],
                [0, 946.37, 259.55],
                [0, 0, 1]
            ])
            self.dist_coeffs = np.array([[-0.51, 0.75, -0.002, -0.003, -1.12]])

        # 相机位置(厘米)
        self.cam_pos = np.array([0.0, 14.0, 68.0])

        # 棋盘标定参数(厘米)
        # 棋盘a1 (col=0,row=0) 在机器人坐标系中的位置
        self.board_origin_robot = np.array([-12.4, 3, 2.0])
        # 棋盘X方向(col增加)对应机器人X轴
        self.board_dir_x = np.array([1, 0, 0])
        # 棋盘Y方向(row增加)对应机器人Y轴(向下为正)
        self.board_dir_y = np.array([0, 1, 0])

        # 棋盘尺寸(8列×8行)
        self.board_cols = 8
        self.board_rows = 8

    def set_board_calibration(self, origin, dir_x, dir_y, grid_size_cm):
        """
        设置棋盘标定参数

        Args:
            origin: 棋盘a1角在机器人坐标系中的位置 [x, y, z] (厘米)
            dir_x: 棋盘列方向的单位向量
            dir_y: 棋盘行方向的单位向量
            grid_size_cm: 格子大小(厘米)
        """
        self.board_origin_robot = np.array(origin)
        self.board_dir_x = np.array(dir_x)
        self.board_dir_y = np.array(dir_y)
        self.GRID_SIZE_CM = grid_size_cm

    def board_to_robot(self, col, row, z_height=8.5):
        """
        将棋盘坐标转换为机器人坐标(厘米)
        返回格子中心点(国际象棋棋子放在格子内)

        Args:
            col: 列索引(0-7, a-h)
            row: 行索引(0-7, rank 1-8)
            z_height: 高度(厘米)

        Returns:
            robot_pos: [x, y, z] 机器人坐标系中的位置(厘米)
        """
        x = self.board_origin_robot[0] + (col + 0.6) * self.GRID_SIZE_CM * self.board_dir_x[0]
        y = self.board_origin_robot[1] + (row + 0.6) * self.GRID_SIZE_CM * self.board_dir_y[1]
        z = z_height

        return np.array([x, y, z])

    def robot_to_board(self, robot_pos):
        """
        将机器人坐标(厘米)转换为棋盘坐标

        Args:
            robot_pos: [x, y, z] 机器人坐标系中的位置(厘米)

        Returns:
            (col, row): 最近的棋盘格坐标
        """
        rel = robot_pos - self.board_origin_robot

        col_float = np.dot(rel, self.board_dir_x) / self.GRID_SIZE_CM
        row_float = -rel[1] / self.GRID_SIZE_CM  # board_dir_y = [0, -1, 0]

        col = int(np.clip(round(col_float), 0, self.board_cols - 1))
        row = int(np.clip(round(row_float), 0, self.board_rows - 1))

        return col, row

    def board_to_robot_from_uci(self, uci_str, z_height=8.5):
        """
        将UCI格式坐标转换为机器人坐标

        Args:
            uci_str: UCI格式坐标 (如 'e2', 'h8')
            z_height: Z轴高度(厘米)

        Returns:
            list: [x, y, z] 机器人坐标 (厘米)
        """
        col = ord(uci_str[0].lower()) - ord('a')
        row = int(uci_str[1]) - 1
        return self.board_to_robot(col, row, z_height)

    def pixel_to_board(self, u, v, depth_cm=50.0):
        """
        将像素坐标转换为棋盘坐标

        Args:
            u, v: 像素坐标
            depth_cm: 目标物距相机距离(厘米)

        Returns:
            (col, row): 棋盘坐标
        """
        pixel_hom = np.array([u, v, 1.0])
        cam_intrinsic_inv = np.linalg.inv(self.camera_matrix)
        cam_coords = cam_intrinsic_inv @ pixel_hom
        cam_offsets = cam_coords[:2] * depth_cm / 1000.0

        cam_pos_m = self.cam_pos / 100.0

        robot_x = cam_pos_m[0] + cam_offsets[0]
        robot_y = cam_pos_m[1] - cam_offsets[1]
        robot_z = cam_pos_m[2] - depth_cm / 1000.0

        robot_pos = np.array([robot_x, robot_y, robot_z]) * 100.0
        return self.robot_to_board(robot_pos)


def test():
    """测试坐标映射"""
    mapper = BoardToRobotMapper()

    print("=" * 60)
    print("国际象棋棋盘坐标 -> 机器人坐标 (8x8 = 64个点, 3.1cm间距)")
    print("=" * 60)
    print(f"{'UCI':>4} {'Col':>3} {'Row':>3} {'Robot X':>8} {'Robot Y':>8}")
    print("-" * 60)

    for row in range(7, -1, -1):  # 从rank 8到rank 1
        for col in range(8):
            uci = f"{chr(ord('a') + col)}{row + 1}"
            pos = mapper.board_to_robot(col, row, z_height=8.5)
            print(f"{uci:>4} {col:>3} {row:>3} {pos[0]:>8.1f} {pos[1]:>8.1f}")

    print("\n" + "-" * 60)
    print("UCI -> 机器人坐标 测试")
    print("-" * 60)
    for uci in ['a1', 'e2', 'e4', 'h8', 'd4', 'g1']:
        pos = mapper.board_to_robot_from_uci(uci, z_height=8.5)
        print(f"  {uci} -> [{pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}]")


if __name__ == '__main__':
    test()
