#!/usr/bin/env python3
"""
sndcpy - Android Audio Streaming Client
Stream audio from Android devices to desktop in real-time.
"""

import subprocess
import socket
import time
import signal
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

import pyaudio
from colorama import init, Fore, Style

init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """Custom formatter for colored log output."""
    
    COLORS = {
        'DEBUG': Fore.BLUE,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)


class SndcpyClient:
    """Android audio streaming client using ADB and socket communication."""
    
    # Audio configuration
    AUDIO_FORMAT = pyaudio.paInt16
    CHANNELS = 2
    SAMPLE_RATE = 48000
    BUFFER_SIZE = 4096
    
    # App constants
    PACKAGE_NAME = "com.rom1v.sndcpy"
    ACTIVITY = f"{PACKAGE_NAME}/.MainActivity"
    
    def __init__(self, apk_path: Path, port: int = 28200, device_serial: Optional[str] = None, debug: bool = False):
        """
        Initialize the sndcpy client.
        
        Args:
            apk_path: Path to sndcpy APK file
            port: Local port for audio forwarding
            device_serial: Optional device serial for multiple devices
            debug: Enable debug logging
        """
        self.apk_path = apk_path
        self.port = port
        self.device_serial = device_serial
        
        # Setup logging
        self.logger = logging.getLogger("sndcpy")
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        
        handler = logging.StreamHandler()
        handler.setFormatter(ColoredFormatter(
            fmt='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        self.logger.addHandler(handler)
        self.logger.propagate = False
        
        # Resources
        self.socket = None
        self.pyaudio_instance = None
        self.audio_stream = None
        
        # Build ADB command prefix
        self.adb_cmd = ["adb"]
        if device_serial:
            self.adb_cmd.extend(["-s", device_serial])
        
        self.metadata_enabled = False
    
    def run(self):
        """Execute the complete streaming workflow."""
        self._check_adb()
        self._check_device()
        self._setup_app()
        self._connect()
        self._stream()

    def _check_adb(self):
        """Verify ADB is installed and accessible."""
        self.logger.info("Checking ADB installation...")
        try:
            result = subprocess.run(["adb", "version"], capture_output=True, text=True)
            if result.returncode != 0:
                raise FileNotFoundError
            self.logger.debug(f"ADB version: {result.stdout.strip()}")
        except FileNotFoundError:
            self.logger.error("ADB not found. Please install ADB and ensure it's in your PATH.")
            sys.exit(1)
    
    def _check_device(self):
        """Verify device is connected."""
        self.logger.info("Checking device connection...")
        result = subprocess.run(self.adb_cmd + ["get-state"], capture_output=True, text=True)
        
        if "device" not in result.stdout:
            self.logger.error("No device connected")
            sys.exit(1)
        
        if self.device_serial:
            self.logger.info(f"Using device: {self.device_serial}")
    
    def _setup_app(self):
        """Install and configure the sndcpy app."""
        if not self.apk_path.exists():
            self.logger.error(f"APK not found: {self.apk_path}")
            self.logger.error("Please download sndcpy.apk from https://github.com/rom1v/sndcpy/releases/")
            sys.exit(1)
        
        # Check if already installed
        result = subprocess.run(
            self.adb_cmd + ["shell", "pm", "list", "packages", self.PACKAGE_NAME],
            capture_output=True, text=True
        )
        
        if self.PACKAGE_NAME in result.stdout:
            self.logger.info("App already installed")
        else:
            self.logger.info(f"Installing {self.apk_path.name}...")
            result = subprocess.run(
                self.adb_cmd + ["install", "-t", "-r", "-g", str(self.apk_path)],
                capture_output=True, text=True
            )
            self.logger.debug(f"Install output: {result.stdout}")
        
        # Monkey patch to grant permission automatically
        self.logger.info("Granting permissions...")
        subprocess.run(
            self.adb_cmd + ["shell", "appops", "set", self.PACKAGE_NAME, "PROJECT_MEDIA", "allow"],
            capture_output=True
        )
        
        self.logger.info(f"Forwarding port {self.port}...")
        subprocess.run(
            self.adb_cmd + ["forward", f"tcp:{self.port}", "localabstract:sndcpy"],
            capture_output=True
        )
        
        self.logger.info("Starting app...")
        subprocess.run(
            self.adb_cmd + ["shell", "am", "start", self.ACTIVITY],
            capture_output=True
        )

        self.logger.debug("Waiting 1 second for app startup...")
        time.sleep(1)  # Wait for app startup

        if self._check_notification_permission():
            self.logger.info(f"{Fore.GREEN}Notification permission already granted{Style.RESET_ALL}")
            self.metadata_enabled = True
        else:
            self._wait_for_notification_permission()
    
    def _connect(self):
        """Connect to the audio stream."""
        self.logger.info("Connecting to audio stream...")
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect(("127.0.0.1", self.port))
            self.logger.info("Connected successfully")
        except socket.error as e:
            self.logger.error(f"Connection failed: {e}")
            sys.exit(1)
    
    def _stream(self):
        """Stream audio from device to desktop."""
        self.pyaudio_instance = pyaudio.PyAudio()
        self.audio_stream = self.pyaudio_instance.open(
            format=self.AUDIO_FORMAT,
            channels=self.CHANNELS,
            rate=self.SAMPLE_RATE,
            output=True
        )
        
        self.logger.info("Streaming audio... Press Ctrl+C to stop")
        
        try:
            while True:
                data = self.socket.recv(self.BUFFER_SIZE)
                if not data:
                    self.logger.info("Connection closed by device")
                    break
                self.audio_stream.write(data)
        except KeyboardInterrupt:
            self.logger.info("Stopping...")
        except socket.timeout:
            self.logger.error("Socket timeout while waiting for data")
        except socket.error as e:
            self.logger.error(f"Socket error: {e}")
        except Exception as e:
            self.logger.error(f"Error during playback: {e}")

    # Add these methods to the SndcpyClient class
    def _check_notification_permission(self):
        """Check if notification permission is granted for the app."""
        self.logger.info("Checking notification permission...")
        
        result = subprocess.run(
            self.adb_cmd + ["shell", "settings", "get", "secure", "enabled_notification_listeners"],
            capture_output=True, text=True
        )
        
        if self.PACKAGE_NAME in result.stdout:
            self.logger.debug("Found package in notification listeners")
            return True

        return False

    def _wait_for_notification_permission(self):
        """Wait for user to grant notification permission (blocking)."""
        self.logger.info(f"{Fore.CYAN}Waiting for notification permission (up to 30 seconds)...{Style.RESET_ALL}")
        self.logger.info(f"{Fore.YELLOW}Please grant notification permission on your device when prompted.{Style.RESET_ALL}")
        
        start_time = time.time()
        max_wait_time = 30  # seconds
        check_interval = 2  # seconds between checks
        
        while time.time() - start_time < max_wait_time:
            if self._check_notification_permission():
                self.logger.info(f"{Fore.GREEN}Notification permission granted!{Style.RESET_ALL}")
                self.metadata_enabled = True
                break
            
            # Wait before checking again
            time.sleep(check_interval)
        
        start_time = time.time()
        self.logger.info("Waiting for you to close the settings page...")
        while time.time() - start_time < max_wait_time:
            # Check if our app's service is running (means media projection was granted)
            service_result = subprocess.run(
                self.adb_cmd + ["shell", "dumpsys", "activity", "services", self.PACKAGE_NAME],
                capture_output=True,
                text=True
            )
            
            if "RecordService" in service_result.stdout:
                self.logger.info("{Fore.GREEN}Service detected, continuing...{Style.RESET_ALL}")
                break
            
            time.sleep(check_interval)
        else:
            self.logger.warning("⚠️ Timeout waiting for settings to close. Continuing anyway...")
        
        # Permission wasn't granted within the time limit
        # self.logger.warning(f"{Fore.YELLOW}Notification permission not granted, metadata features disabled.{Style.RESET_ALL}")
        return False
    
    def cleanup(self):
        """Release all resources."""
        self.logger.info("Cleaning up resources...")
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
        if self.socket:
            self.socket.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Stream audio from Android device to desktop"
    )
    parser.add_argument(
        "apk_path",
        nargs="?",
        default="sndcpy.apk",
        help="Path to sndcpy APK file"
    )
    parser.add_argument(
        "-s", "--serial",
        help="Device serial number (for multiple devices)"
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=28200,
        help="Local port for forwarding (default: 28200)"
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    client = SndcpyClient(
        apk_path=Path(args.apk_path),
        port=args.port,
        device_serial=args.serial,
        debug=args.debug
    )
    
    # Setup cleanup on exit
    def signal_handler(sig, frame):
        client.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        client.run()
    finally:
        client.cleanup()


if __name__ == "__main__":
    main()