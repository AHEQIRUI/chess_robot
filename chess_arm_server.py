#!/usr/bin/env python3
"""
国际象棋机械臂控制服务器
运行在树莓派上, 监听TCP连接接收指令并执行机械臂动作
使用夹爪(舵机6)抓取棋子
"""

import sys
import time
import socket

sys.path.insert(0, 'src')
sys.path.insert(0, 'ch_src')

try:
    from Arm_Lib import Arm_Device
except ImportError:
    print("警告: 无法导入Arm_Lib")
    Arm_Device = None

try:
    import ik
except ImportError:
    print("错误: 无法导入ik")
    ik = None


class ChessArmServer:
    """国际象棋机械臂控制服务器"""

    def __init__(self, host='0.0.0.0', port=5001):
        self.host = host
        self.port = port
        self.arm = None

        self.grasp_height = 8.0
        self.safe_height = 13.0

        # 夹爪角度
        self.gripper_open_angle = 135
        self.gripper_close_angle = 161  # 默认兵的角度

        # 夹爪闭合角度（根据棋子类型）
        self.gripper_close_angles = {
            'P': 161, 'p': 161,  # 兵
            'R': 157, 'r': 157,  # 车
            'N': 164, 'n': 164,  # 马
            'B': 161, 'b': 161,  # 象
            'K': 152, 'k': 152,  # 王
            'Q': 153, 'q': 153,  # 后
        }

        # 棋子高度（第二次下降高度）
        self.piece_heights = {
            'P': 4.0, 'p': 4.0,  # 兵
            'R': 3.8, 'r': 3.8,  # 车
            'N': 4.4, 'n': 4.4,  # 马
            'B': 5.0, 'b': 5.0,  # 象
            'K': 7.2, 'k': 7.2,  # 王
            'Q': 6.5, 'q': 6.5,  # 后
        }

        self.z_correction_factor = 0.15

        self.initial_pos = [179, 179, 0, 0, 90, 65]

        if Arm_Device:
            self.arm = Arm_Device()
            print("机械臂已连接")
            self.set_initial_position()
            self.gripper_open()
            time.sleep(2.5)
        else:
            print("警告: 机械臂未连接, 模拟模式")

    def get_piece_height(self, move_desc):
        """从走棋描述中解析棋子类型并返回对应高度"""
        if not move_desc:
            return 6.0  # 默认兵的高度

        # 解析棋子类型
        piece_chars = {'P': '兵', 'p': '兵', 'R': '车', 'r': '车', 'N': '马', 'n': '马',
                       'B': '象', 'b': '象', 'K': '王', 'k': '王', 'Q': '后', 'q': '后'}

        for piece, name in piece_chars.items():
            if name in move_desc:
                return self.piece_heights.get(piece, 6.0)

        # 尝试直接从描述中查找棋子字符
        for piece in self.piece_heights:
            if piece in move_desc:
                return self.piece_heights[piece]

        return 6.0  # 默认

    def get_gripper_close_angle(self, move_desc):
        """从走棋描述中解析棋子类型并返回对应的夹爪闭合角度"""
        if not move_desc:
            return 161  # 默认兵的角度

        # 解析棋子类型
        piece_chars = {'P': '兵', 'p': '兵', 'E': '象', 'e': '象', 'N': '马', 'n': '马',
                       'B': '象', 'b': '象', 'K': '王', 'k': '王', 'Q': '后', 'q': '后',
                       'R': '车', 'r': '车'}

        for piece, name in piece_chars.items():
            if name in move_desc:
                return self.gripper_close_angles.get(piece, 161)

        # 尝试直接从描述中查找棋子字符
        for piece in self.gripper_close_angles:
            if piece in move_desc:
                return self.gripper_close_angles[piece]

        return 161  # 默认

    def solve_ik(self, robot_pos):
        """使用IK求解器"""
        if ik is None:
            return None
        x, y, z = robot_pos
        z = self.get_corrected_z(x, y, z)
        valid, deg1, deg2, deg3, deg4 = ik.backward_kinematics(x, y, z)
        if valid:
            return [deg1, deg2, deg3, deg4, deg1, 0]  # 舵机5与舵机1角度相同，舵机6暂为0
        return None

    def get_corrected_z(self, x, y, z):
        """计算校正后的Z坐标

        公式: z_corrected = z + k * sqrt(x^2 + y^2)
        k初始值为0.0，可通过测试调整
        """
        import math
        distance = math.sqrt(x**2 + y**2)
        return z + self.z_correction_factor * distance

    def move_to_position(self, position, servo6_angle=None, retries=3):
        """移动到指定位置

        Args:
            position: [x, y, z] 目标位置
            servo6_angle: 夹爪角度, None=保持当前
            retries: 重试次数
        """
        angles = self.solve_ik(position)
        if angles is None:
            print(f"IK无解: {position}")
            return False

        if servo6_angle is not None:
            angles[5] = servo6_angle  # 只修改舵机6（夹爪），舵机5保持与舵机1同步

        if self.arm:
            for attempt in range(retries):
                try:
                    self.arm.Arm_serial_servo_write6(
                        angles[0], angles[1], angles[2],
                        angles[3], angles[4], angles[5], 2000
                    )
                    print(f"移动到 {position}: {[f'{a:.1f}' for a in angles]}")
                    return True
                except Exception as e:
                    print(f"I2C错误 ({attempt+1}/{retries}): {e}")
                    if attempt < retries - 1:
                        print("重新执行该步骤...")
                    time.sleep(2.5)
        else:
            print(f"[模拟] 移动到 {position}")
            return True
        return False

    def gripper_open(self):
        """张开夹爪"""
        if self.arm:
            self.arm.Arm_serial_servo_write(6, self.gripper_open_angle, 2000)
            print("夹爪: 张开")

    def gripper_close(self, angle=None):
        """闭合夹爪"""
        if self.arm:
            close_angle = angle if angle is not None else self.gripper_close_angle
            self.arm.Arm_serial_servo_write(6, close_angle, 2000)
            print(f"夹爪: 闭合 (角度: {close_angle})")

    def set_initial_position(self):
        """移动到初始位置"""
        if self.arm:
            self.arm.Arm_serial_servo_write6(
                self.initial_pos[0], self.initial_pos[1], self.initial_pos[2],
                self.initial_pos[3], self.initial_pos[4], self.initial_pos[5], 2000
            )
            print("移动到初始位置")

    def execute_move(self, from_robot, to_robot, is_capture=False, move_desc=""):
        """执行走棋序列: 初始位置 → 目标上方 → 一次下降 → 二次下降 → 夹取 → 抬升 → 放置位置上方 → 放置 → 放置位置上方 → 初始位置"""
        print(f"\n===== 执行走棋 =====")
        if move_desc:
            print(f"走棋描述: {move_desc}")
            # 解析走棋描述获取棋子信息
            if '吃' in move_desc:
                print("动作: 吃子")
            else:
                print("动作: 移动")
        else:
            print(f"从: {from_robot}")
            print(f"到: {to_robot}")
            print(f"吃子: {is_capture}")

        above_from = [from_robot[0], from_robot[1], self.safe_height]
        above_to = [to_robot[0], to_robot[1], self.safe_height]
        half_down = [from_robot[0], from_robot[1], 9.0]  # 一次下降高度固定为9

        # 获取棋子高度和夹爪角度
        piece_height = self.get_piece_height(move_desc)
        gripper_angle = self.get_gripper_close_angle(move_desc)

        # 1. 初始位置
        print("#1 初始位置")


        # 2. 目标上方
        print(f"#2 目标上方 {above_from}")
        self.move_to_position(above_from, servo6_angle=self.gripper_open_angle)
        time.sleep(2.5)

        # 3. 一次下降
        print(f"#3 一次下降 {half_down}")
        self.move_to_position(half_down, servo6_angle=self.gripper_open_angle)
        time.sleep(2.5)

        # 3.5. 二次下降（到位，使用棋子高度）
        from_ground = [from_robot[0], from_robot[1], piece_height]
        print(f"#3.5 二次下降 {from_ground} (棋子高度: {piece_height})")
        self.move_to_position(from_ground, servo6_angle=self.gripper_open_angle)
        time.sleep(2.5)

        # 4. 夹取
        print(f"#4 夹取 (夹爪角度: {gripper_angle})")
        self.gripper_close(gripper_angle)
        time.sleep(2.5)

        # 5. 抬升
        print(f"#5 抬升 {above_from}")
        self.move_to_position(above_from, servo6_angle=gripper_angle)
        time.sleep(2.5)

        # 6. 放置位置上方
        print(f"#6 放置位置上方 {above_to}")
        self.move_to_position(above_to, servo6_angle=gripper_angle)
        time.sleep(2.5)

        # 6.5. 一次下降
        half_down_to = [to_robot[0], to_robot[1], 9.0]
        print(f"#6.5 一次下降 {half_down_to}")
        self.move_to_position(half_down_to, servo6_angle=gripper_angle)
        time.sleep(2.5)

        # 6.7. 二次下降（到位）
        to_ground = [to_robot[0], to_robot[1], piece_height]
        print(f"#6.7 二次下降 {to_ground}")
        self.move_to_position(to_ground, servo6_angle=gripper_angle)
        time.sleep(2.5)

        # 7. 放置
        print("#7 放置")
        self.gripper_open()
        time.sleep(2.5)

        # 8. 抬升到放置位置上方
        print(f"#8 抬升到放置位置上方 {above_to}")
        self.move_to_position(above_to, servo6_angle=self.gripper_open_angle)
        time.sleep(2.5)

        # 9. 初始位置
        print("#9 初始位置")
        self.set_initial_position()
        self.gripper_open()
        time.sleep(2.5)

        print("===== 走棋完成 =====")
        return True

    def remove_captured_piece(self, to_robot, move_desc=""):
        """移除被吃棋子: 初始位置 → 目标上方 → 一次下降 → 二次下降 → 夹取 → 抬升 → 丢弃位置上方 → 下降 → 放置 → 抬升 → 初始位置"""
        print(f"\n===== 移除被吃棋子 =====")
        if move_desc:
            print(f"走棋描述: {move_desc}")
        else:
            print(f"位置: {to_robot}")

        discard_pos = [20, 6, 7]
        above_to = [to_robot[0], to_robot[1], self.safe_height]
        above_discard = [20, 6, self.safe_height]
        half_down_to = [to_robot[0], to_robot[1], 9.0]  # 一次下降高度固定为9

        # 获取棋子高度和夹爪角度
        piece_height = self.get_piece_height(move_desc)
        gripper_angle = self.get_gripper_close_angle(move_desc)

        # 1. 初始位置
        print("#1 初始位置")


        # 2. 目标上方
        print(f"#2 目标上方 {above_to}")
        self.move_to_position(above_to, servo6_angle=self.gripper_open_angle)
        time.sleep(2.5)

        # 3. 一次下降
        print(f"#3 一次下降 {half_down_to}")
        self.move_to_position(half_down_to, servo6_angle=self.gripper_open_angle)
        time.sleep(2.5)

        # 3.5. 二次下降（到位，使用棋子高度）
        to_ground = [to_robot[0], to_robot[1], piece_height]
        print(f"#3.5 二次下降 {to_ground} (棋子高度: {piece_height})")
        self.move_to_position(to_ground, servo6_angle=self.gripper_open_angle)
        time.sleep(2.5)

        # 4. 夹取
        print(f"#4 夹取 (夹爪角度: {gripper_angle})")
        self.gripper_close(gripper_angle)
        time.sleep(2.5)

        # 5. 抬升
        print(f"#5 抬升 {above_to}")
        self.move_to_position(above_to, servo6_angle=gripper_angle)
        time.sleep(2.5)

        # 6. 丢弃位置上方
        print(f"#6 丢弃位置上方 {above_discard}")
        self.move_to_position(above_discard, servo6_angle=gripper_angle)
        time.sleep(2.5)

        # 7. 下降到放置位置
        print(f"#7 下降到放置位置 {discard_pos}")
        self.move_to_position(discard_pos, servo6_angle=gripper_angle)
        time.sleep(2.5)

        # 8. 放置
        print("#8 放置")
        self.gripper_open()
        time.sleep(2.5)

        # 9. 抬升到丢弃位置上方
        print(f"#9 抬升到丢弃位置上方 {above_discard}")
        self.move_to_position(above_discard, servo6_angle=self.gripper_open_angle)
        time.sleep(2.5)

        print("===== 移除完成 =====")
        return True

    def handle_command(self, cmd):
        """处理命令"""
        try:
            parts = cmd.strip().split(',')
            action = parts[0]

            if action == 'MOVE':
                from_robot = [float(parts[1]), float(parts[2]), float(parts[3])]
                to_robot = [float(parts[4]), float(parts[5]), float(parts[6])]
                is_capture = parts[7].lower() == 'true'
                move_desc = parts[8] if len(parts) > 8 else ''

                if move_desc:
                    print(f"走棋描述: {move_desc}")

                if is_capture:
                    self.remove_captured_piece(to_robot, move_desc)

                self.execute_move(from_robot, to_robot, is_capture, move_desc)
                return "OK"

            elif action == 'HOME':
                self.set_initial_position()
                self.gripper_open()
                return "OK"

            elif action == 'GRIP_OPEN':
                self.gripper_open()
                return "OK"

            elif action == 'GRIP_CLOSE':
                self.gripper_close()
                return "OK"

            elif action == 'QUIT':
                return "QUIT"

            else:
                return f"UNKNOWN: {action}"

        except Exception as e:
            return f"ERROR: {e}"

    def run(self):
        """启动服务器"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(1)

        print(f"国际象棋机械臂服务器已启动, 监听 {self.host}:{self.port}")

        while True:
            try:
                client_socket, addr = server_socket.accept()
                print(f"连接来自: {addr}")

                while True:
                    data = client_socket.recv(1024).decode('utf-8')
                    if not data:
                        break

                    print(f"收到命令: {data}")
                    response = self.handle_command(data)
                    client_socket.sendall(response.encode('utf-8'))

                    if response == "QUIT":
                        client_socket.close()
                        print("客户端断开连接")
                        break

                client_socket.close()

            except KeyboardInterrupt:
                print("\n服务器关闭")
                break
            except Exception as e:
                print(f"错误: {e}")

        server_socket.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description='国际象棋机械臂控制服务器')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址 (默认0.0.0.0)')
    parser.add_argument('--port', '-p', type=int, default=5001, help='监听端口 (默认5001)')
    args = parser.parse_args()

    server = ChessArmServer(host=args.host, port=args.port)
    server.run()


if __name__ == '__main__':
    main()
