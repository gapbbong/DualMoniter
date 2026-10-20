import os
import sys
import socket
import time
import json
import io
import threading
import asyncio
import urllib.request
import shutil

# Package dependencies so PyInstaller bundles them
import requests
import mss
import PIL
import PIL.Image
import websockets

# Default fallback server IP
SERVER_IP = "10.128.56.41"

def get_my_room_prefix():
    """학생 PC 컴퓨터 이름에서 실습실 번호 추출 (예: 201-05 -> 201)"""
    try:
        hn = socket.gethostname()
        parts = hn.split("-")
        if len(parts) >= 2 and parts[0].isdigit():
            return parts[0]
    except Exception:
        pass
    return ""

def discover_teacher_server(timeout=1.5):
    """LAN UDP 브로드캐스트로 교사 서버 IP 자동 탐색 (Zero-Config)"""
    my_room = get_my_room_prefix()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)

        # 학생이 탐색 패킷 보낼 때 자기 실습실 번호도 함께 전송
        discover_msg = f"CIM_DISCOVER|{my_room}".encode("utf-8")
        try:
            sock.sendto(discover_msg, ("255.255.255.255", 8889))
        except Exception:
            pass

        start_t = time.time()
        fallback_ip = None
        while time.time() - start_t < timeout:
            try:
                data, addr = sock.recvfrom(1024)
                text = data.decode("utf-8", errors="ignore").strip()
                if text.startswith("CIM_RESPONSE|") or text.startswith("CIM_BEACON|"):
                    parts = text.split("|")
                    if len(parts) >= 2 and parts[1]:
                        teacher_ip = parts[1].strip()
                        teacher_room = parts[3].strip() if len(parts) >= 4 else ""

                        # 같은 실습실 번호인 교사 PC만 최우선 매칭 (실습실 간 혼선 100% 방지)
                        if my_room and teacher_room:
                            if my_room == teacher_room:
                                sock.close()
                                return teacher_ip
                            else:
                                continue
                        else:
                            fallback_ip = teacher_ip
            except socket.timeout:
                break
            except Exception:
                break
        sock.close()
        if fallback_ip:
            return fallback_ip
    except Exception:
        pass
    return None

def load_server_ip():
    global SERVER_IP
    # 1. 수동 지정 파일이 있을 경우 최우선
    if os.path.exists("server_ip.txt"):
        try:
            with open("server_ip.txt", "r", encoding="utf-8") as f:
                ip = f.read().strip()
                if ip:
                    SERVER_IP = ip
                    print(f"[Loader] Server IP loaded from server_ip.txt: {SERVER_IP}")
                    return
        except Exception as e:
            print(f"[Loader] Failed to read server_ip.txt: {e}")

    # 2. LAN 자동 탐색
    auto_ip = discover_teacher_server(timeout=1.2)
    if auto_ip:
        SERVER_IP = auto_ip
        print(f"[Loader] Teacher Server auto-discovered: {SERVER_IP}")
        return

    print(f"[Loader] Using default Server IP: {SERVER_IP}")

def main():
    global SERVER_IP
    try:
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        os.chdir(exe_dir)
        print(f"[Loader] Working directory set to: {exe_dir}")
    except Exception as e:
        print(f"[Loader] Failed to set working directory: {e}")

    load_server_ip()

    # 번들된 PyInstaller 임시 폴더에서 내장된 FINAL_AGENT_PRO.py 경로 확인
    bundled_py = None
    if hasattr(sys, '_MEIPASS'):
        bundle_path = os.path.join(sys._MEIPASS, "FINAL_AGENT_PRO.py")
        if os.path.exists(bundle_path):
            bundled_py = bundle_path

    # 로컬 작업 디렉터리에 FINAL_AGENT_PRO.py가 없으면 내장 번들 파일 자동 복사
    if not os.path.exists("FINAL_AGENT_PRO.py") and bundled_py:
        try:
            shutil.copyfile(bundled_py, "FINAL_AGENT_PRO.py")
            print("[Loader] Copied bundled FINAL_AGENT_PRO.py to local directory.")
        except Exception as e:
            print(f"[Loader] Failed to copy bundled script: {e}")

    # 절대 프로세스가 종료되지 않는 무한 상주 루프
    while True:
        # 혹시 아직 탐색 전이거나 연결이 안 될 때 자동 재탐색 시도
        if not os.path.exists("server_ip.txt"):
            auto_ip = discover_teacher_server(timeout=1.0)
            if auto_ip and auto_ip != SERVER_IP:
                SERVER_IP = auto_ip
                print(f"[Loader] Updated Teacher Server IP to: {SERVER_IP}")

        url = f"http://{SERVER_IP}:8888/download_agent"

        # 1. 서버가 켜져 있다면 최신 코드를 다운로드 시도
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=3) as response:
                code = response.read().decode('utf-8')
                if code and "def run():" in code:
                    with open("FINAL_AGENT_PRO.py", "w", encoding="utf-8") as f:
                        f.write(code)
                    print("[Loader] Updated to latest agent code from teacher server.")
        except Exception:
            # 교사 서버가 아직 안 켜져 있거나 네트워크 대기 상태
            pass

        # 2. 실행할 코드 확보 (로컬 캐시본 -> 내장 번들본)
        code_to_run = None
        if os.path.exists("FINAL_AGENT_PRO.py"):
            try:
                with open("FINAL_AGENT_PRO.py", "r", encoding="utf-8") as f:
                    code_to_run = f.read()
            except Exception as e:
                print(f"[Loader] Error reading FINAL_AGENT_PRO.py: {e}")

        if not code_to_run and bundled_py and os.path.exists(bundled_py):
            try:
                with open(bundled_py, "r", encoding="utf-8") as f:
                    code_to_run = f.read()
            except Exception:
                pass

        # 3. 코드가 있으면 실행!
        if code_to_run:
            print("[Loader] Launching agent...")
            try:
                global_namespace = globals().copy()
                global_namespace['__name__'] = '__main__'
                exec(code_to_run, global_namespace)
            except Exception as e:
                print(f"[Loader] Agent execution error: {e}")
                import traceback
                traceback.print_exc()

            # exec(run())이 종료되더라도 절대 프로세스를 끝내지 않고 3초 후 재시작!
            time.sleep(3)
        else:
            # 코드도 없고 서버도 안 켜져 있을 때 3초 후 재시도
            print(f"[Loader] Waiting for Teacher Server ({SERVER_IP}:8888)... retrying in 3s")
            time.sleep(3)

if __name__ == "__main__":
    main()
