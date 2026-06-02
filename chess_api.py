#!/usr/bin/env python3
"""Query chessdb.cn for best move, convert to arm coordinates, send to robot."""

import argparse
import socket
import sys
import urllib.request
import urllib.parse

try:
    from board_to_robot import BoardToRobotMapper
except ImportError:
    BoardToRobotMapper = None


def query_best_move(fen):
    """Query the best move for the given FEN from chessdb.cn."""
    encoded = urllib.parse.quote(fen, safe='')
    url = f"http://www.chessdb.cn/cdb.php?action=querypv&board={encoded}"

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            body = resp.read().decode('utf-8')
        if not body.strip():
            return {"success": False, "error": "Empty response"}

        fields = body.strip().split("|")
        if len(fields) < 1:
            return {"success": False, "error": f"Unexpected response: {body}"}

        if fields[0].startswith("pv:"):
            best_move = fields[0][3:]
        elif "pv:" in fields[0]:
            parts = fields[0].split(",")
            best_move = None
            for p in parts:
                if p.startswith("pv:"):
                    best_move = p[3:]
                    break
            if best_move is None:
                return {"success": False, "error": f"No pv found: {body}"}
        elif len(fields) >= 2:
            best_move = fields[1]
        else:
            return {"success": False, "error": f"Cannot parse: {body}"}

        return {"success": True, "best_move": best_move, "fen": fen, "raw": body}
    except Exception as e:
        return {"success": False, "error": str(e)}


def rotate_uci_180(uci):
    """Rotate a UCI move by 180 degrees for black-side play."""
    if len(uci) < 4:
        return uci

    def flip(sq):
        f = 7 - (ord(sq[0]) - ord('a'))
        r = 9 - int(sq[1])
        return f"{chr(ord('a') + f)}{r}"

    if len(uci) >= 5 and uci[4] in "qrbnQRBN":
        return flip(uci[:2]) + flip(uci[2:4]) + uci[4]
    return flip(uci[:2]) + flip(uci[2:4])


def uci_to_robot(uci, z_height=5.0):
    """Convert a UCI move to robot arm coordinates."""
    if BoardToRobotMapper is None:
        return None, None
    mapper = BoardToRobotMapper()
    from_robot = mapper.board_to_robot_from_uci(uci[:2], z_height=z_height)
    to_robot = mapper.board_to_robot_from_uci(uci[2:4], z_height=z_height)
    return from_robot, to_robot


def send_to_arm(host, port, from_robot, to_robot, is_capture=False):
    """Send a MOVE command to the arm server. Returns True on success."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        cmd = (f"MOVE,{from_robot[0]:.1f},{from_robot[1]:.1f},{from_robot[2]:.1f},"
               f"{to_robot[0]:.1f},{to_robot[1]:.1f},{to_robot[2]:.1f},"
               f"{str(is_capture).lower()}")
        sock.sendall((cmd + '\n').encode('utf-8'))
        resp = sock.recv(1024).decode('utf-8').strip()
        sock.close()
        print(f"Arm response: {resp}")
        return resp == "OK"
    except Exception as e:
        print(f"Arm error: {e}")
        return False


def confirm_send(move, from_robot, to_robot):
    """Ask user to confirm sending the move to the arm."""
    print(f"\n{'='*50}")
    print(f"Move:       {move}")
    print(f"From (arm): [{from_robot[0]:.1f}, {from_robot[1]:.1f}, {from_robot[2]:.1f}]")
    print(f"To   (arm): [{to_robot[0]:.1f}, {to_robot[1]:.1f}, {to_robot[2]:.1f}]")
    print(f"{'='*50}")
    while True:
        answer = input("Send to arm? [y/n]: ").strip().lower()
        if answer in ('y', 'yes'):
            return True
        elif answer in ('n', 'no'):
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Query chess API and optionally send move to robot arm."
    )
    parser.add_argument("fen", nargs="?", default=None,
                        help="FEN string (if omitted, uses standard opening)")
    parser.add_argument("--host", default="192.168.137.60",
                        help="Arm server IP (default: 192.168.137.60)")
    parser.add_argument("--port", type=int, default=5001,
                        help="Arm server port (default: 5001)")
    parser.add_argument("--side", type=str, default="white", choices=["white", "black"],
                        help="Side the ARM plays (default: white)")
    parser.add_argument("--no-arm", action="store_true",
                        help="Query only, don't send to arm")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Skip confirmation prompt")
    args = parser.parse_args()

    fen = args.fen or "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq"

    print(f"FEN: {fen}")
    result = query_best_move(fen)
    if not result["success"]:
        print(f"Error: {result['error']}")
        sys.exit(1)

    ai_move = result["best_move"]
    print(f"Best move: {ai_move}")

    # Rotate only for display, arm uses raw coords
    if args.side == "black":
        print(f"Display (rotated 180°): {rotate_uci_180(ai_move)}")

    if args.no_arm:
        return

    # Convert to robot coordinates
    if BoardToRobotMapper is None:
        print("Error: board_to_robot module not available")
        sys.exit(1)

    from_robot, to_robot = uci_to_robot(ai_move)
    print(f"From (arm): [{from_robot[0]:.1f}, {from_robot[1]:.1f}, {from_robot[2]:.1f}]")
    print(f"To   (arm): [{to_robot[0]:.1f}, {to_robot[1]:.1f}, {to_robot[2]:.1f}]")

    # Confirm and send
    if not args.yes:
        if not confirm_send(ai_move, from_robot, to_robot):
            print("Cancelled.")
            return

    send_to_arm(args.host, args.port, from_robot, to_robot)


if __name__ == "__main__":
    main()
