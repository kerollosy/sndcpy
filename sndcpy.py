import subprocess
import socket
import time
import pyaudio
import os
import sys
import argparse
import logging
from colorama import init, Fore, Style


init(autoreset=True)

logging.basicConfig(
    format='%(message)s',
    level=logging.INFO
)
logger = logging.getLogger("sndcpy")


def main():
    parser = argparse.ArgumentParser(description="Stream audio from Android device")
    parser.add_argument("apk_path", nargs="?", default="sndcpy.apk", help="Path to sndcpy APK file")
    parser.add_argument("device", nargs="?", help="Specific device serial number (if multiple devices connected)")
    parser.add_argument("-p", "--port", type=int, default=28200, help="Local port for forwarding")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    apk_path = args.apk_path
    port = args.port
    device = args.device
    debug = args.debug
    
    if debug:
        logger.setLevel(logging.DEBUG)
    
    adb_cmd = ["adb"]
    if device:
        adb_cmd.extend(["-s", device])
        logger.info(f"{Fore.CYAN}Using device: {device}{Style.RESET_ALL}")
    
    if not os.path.exists(apk_path):
        logger.error(f"{Fore.RED}Error: APK not found at {apk_path}{Style.RESET_ALL}")
        sys.exit(1)
    
    logger.info(f"{Fore.GREEN}Installing {apk_path}{Style.RESET_ALL}")
    result = subprocess.run(adb_cmd + ["install", "-t", "-r", "-g", apk_path], capture_output=True, text=True)
    
    logger.debug(f"Install output: {result.stdout}")
    if result.stderr:
        logger.debug(f"Install errors: {result.stderr}")
    
    # Monkey patch to grant permissions automatically
    logger.info(f"{Fore.GREEN}Granting permissions{Style.RESET_ALL}")
    result = subprocess.run(adb_cmd + ["shell", "appops", "set", "com.rom1v.sndcpy", "PROJECT_MEDIA", "allow"], 
                        capture_output=True, text=True)
    logger.debug(f"Permission output: {result.stdout}")
    if result.stderr:
        logger.debug(f"Permission errors: {result.stderr}")
    
    logger.info(f"{Fore.GREEN}Forwarding port {port}{Style.RESET_ALL}")
    result = subprocess.run(adb_cmd + ["forward", f"tcp:{port}", "localabstract:sndcpy"], 
                        capture_output=True, text=True)
    logger.debug(f"Port forwarding output: {result.stdout}")
    if result.stderr:
        logger.debug(f"Port forwarding errors: {result.stderr}")
    
    logger.info(f"{Fore.GREEN}Starting sndcpy{Style.RESET_ALL}")
    result = subprocess.run(adb_cmd + ["shell", "am", "start", "com.rom1v.sndcpy/.MainActivity"], 
                        capture_output=True, text=True)
    logger.debug(f"App start output: {result.stdout}")
    if result.stderr:
        logger.debug(f"App start errors: {result.stderr}")

    logger.debug("Waiting 3 seconds for app startup...")
    time.sleep(3)
    
    logger.info(f"{Fore.GREEN}Connecting to sndcpy{Style.RESET_ALL}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(("127.0.0.1", port))
        logger.info(f"{Fore.CYAN}Connected to audio stream{Style.RESET_ALL}")
    except socket.error as e:
        logger.error(f"{Fore.RED}Connection failed: {e}{Style.RESET_ALL}")
        sys.exit(1)
    
    pa = pyaudio.PyAudio()
    audio_stream = pa.open(
        format=pyaudio.paInt16,
        channels=2,
        rate=48000,
        output=True,
        frames_per_buffer=1024
    )
    
    logger.info(f"{Fore.CYAN}Streaming audio...{Style.RESET_ALL}")
    try:
        while True:
            audio_data = sock.recv(4096)
            if not audio_data:
                logger.info("Connection closed by device")
                break
            audio_stream.write(audio_data)
    except socket.error as e:
        logger.error(f"{Fore.RED}Socket error: {e}{Style.RESET_ALL}")
    finally:
        # Basic cleanup
        logger.debug("Cleaning up resources")
        if audio_stream:
            audio_stream.close()
        if pa:
            pa.terminate()
        if sock:
            sock.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info(f"{Fore.YELLOW}Program terminated by user{Style.RESET_ALL}")