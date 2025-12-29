"""Package manager integration for auto-installing dependencies"""

import os
import platform
import subprocess
import shutil
import sys
from pathlib import Path
from typing import Optional, Tuple


def _get_subprocess_kwargs() -> dict:
    """Get subprocess kwargs with hidden console window on Windows"""
    kwargs = {}
    if sys.platform == 'win32':
        # Use CREATE_NO_WINDOW constant (0x08000000) to prevent console window
        # This works with both Popen and run, and still allows stdout/stderr capture
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        else:
            # Fallback to constant value if attribute not available
            kwargs['creationflags'] = 0x08000000
    return kwargs


class PackageManager:
    """Handles detection and installation of required tools"""
    
    def __init__(self):
        self.system = platform.system()
        self.is_windows = self.system == "Windows"
        self.is_mac = self.system == "Darwin"
    
    def find_executable(self, name: str, paths: Optional[list] = None) -> Optional[str]:
        """Find an executable in PATH or specified paths"""
        if paths is None:
            paths = []
        
        # Check PATH first
        exe = shutil.which(name)
        if exe:
            return exe
        
        # Check specified paths
        for path in paths:
            exe_path = Path(path) / name
            if exe_path.exists():
                return str(exe_path)
        
        return None
    
    def check_ffmpeg(self) -> Tuple[bool, Optional[str]]:
        """Check if FFmpeg is installed"""
        if self.is_windows:
            # Check common Windows paths
            paths = [
                "C:\\ffmpeg\\bin",
                "C:\\Program Files\\ffmpeg\\bin",
                os.path.expanduser("~\\AppData\\Local\\UniGetUI\\Chocolatey\\bin"),
            ]
            exe_name = "ffmpeg.exe"
        else:
            paths = [
                "/usr/local/bin",
                "/opt/homebrew/bin",
            ]
            exe_name = "ffmpeg"
        
        exe = self.find_executable(exe_name, paths)
        if exe:
            return True, exe
        
        # Check PATH
        exe = shutil.which(exe_name)
        if exe:
            return True, exe
        
        return False, None
    
    def check_handbrake(self) -> Tuple[bool, Optional[str]]:
        """Check if HandBrake CLI is installed"""
        if self.is_windows:
            paths = [
                "C:\\Program Files\\HandBrake",
            ]
            exe_name = "HandBrakeCLI.exe"
        else:
            paths = [
                "/usr/local/bin",
                "/opt/homebrew/bin",
            ]
            exe_name = "HandBrakeCLI"
        
        exe = self.find_executable(exe_name, paths)
        if exe:
            return True, exe
        
        # Check PATH
        exe = shutil.which(exe_name)
        if exe:
            return True, exe
        
        return False, None
    
    def check_mkvinfo(self) -> Tuple[bool, Optional[str]]:
        """Check if mkvinfo is installed"""
        if self.is_windows:
            paths = [
                "C:\\Program Files\\MKVToolNix",
            ]
            exe_name = "mkvinfo.exe"
        else:
            paths = [
                "/usr/local/bin",
                "/opt/homebrew/bin",
            ]
            exe_name = "mkvinfo"
        
        exe = self.find_executable(exe_name, paths)
        if exe:
            return True, exe
        
        # Check PATH
        exe = shutil.which(exe_name)
        if exe:
            return True, exe
        
        return False, None
    
    def install_ffmpeg(self) -> Tuple[bool, str]:
        """Install FFmpeg via package manager"""
        if self.is_windows:
            return self._install_via_chocolatey("ffmpeg")
        elif self.is_mac:
            return self._install_via_homebrew("ffmpeg")
        else:
            return False, "Unsupported operating system"
    
    def install_handbrake(self) -> Tuple[bool, str]:
        """Install HandBrake CLI via package manager"""
        if self.is_windows:
            return self._install_via_chocolatey("handbrake.cli")
        elif self.is_mac:
            return self._install_via_homebrew("handbrake")
        else:
            return False, "Unsupported operating system"
    
    def install_mkvtoolnix(self) -> Tuple[bool, str]:
        """Install MKVToolNix via package manager"""
        if self.is_windows:
            return self._install_via_chocolatey("mkvtoolnix")
        elif self.is_mac:
            return self._install_via_homebrew("mkvtoolnix")
        else:
            return False, "Unsupported operating system"
    
    def _install_via_chocolatey(self, package: str) -> Tuple[bool, str]:
        """Install package via Chocolatey"""
        try:
            # Check if Chocolatey is installed
            choco = shutil.which("choco")
            if not choco:
                return False, "Chocolatey is not installed. Please install it from https://chocolatey.org/"
            
            # Install package
            # Hide console window on Windows (for release builds)
            run_kwargs = {
                'args': [choco, "install", package, "-y"],
                'capture_output': True,
                'text': True,
                'timeout': 600  # 10 minute timeout
            }
            run_kwargs.update(_get_subprocess_kwargs())
            
            result = subprocess.run(**run_kwargs)
            
            if result.returncode == 0:
                return True, f"Successfully installed {package}"
            else:
                return False, f"Failed to install {package}: {result.stderr}"
        except subprocess.TimeoutExpired:
            return False, f"Installation of {package} timed out"
        except Exception as e:
            return False, f"Error installing {package}: {str(e)}"
    
    def _install_via_homebrew(self, package: str) -> Tuple[bool, str]:
        """Install package via Homebrew"""
        try:
            # Check if Homebrew is installed
            brew = shutil.which("brew")
            if not brew:
                return False, "Homebrew is not installed. Please install it from https://brew.sh/"
            
            # Install package
            # Hide console window on Windows (for release builds)
            run_kwargs = {
                'args': [brew, "install", package],
                'capture_output': True,
                'text': True,
                'timeout': 600  # 10 minute timeout
            }
            run_kwargs.update(_get_subprocess_kwargs())
            
            result = subprocess.run(**run_kwargs)
            
            if result.returncode == 0:
                return True, f"Successfully installed {package}"
            else:
                return False, f"Failed to install {package}: {result.stderr}"
        except subprocess.TimeoutExpired:
            return False, f"Installation of {package} timed out"
        except Exception as e:
            return False, f"Error installing {package}: {str(e)}"

