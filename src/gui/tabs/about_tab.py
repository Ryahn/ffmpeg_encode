"""About tab displaying application information"""

import customtkinter as ctk
import sys
import platform
from pathlib import Path
from core.package_manager import PackageManager
from utils.config import config

# Get version - try multiple methods
def _get_version():
    """Get version from src/__init__.py"""
    # Method 1: Try relative import
    try:
        from ... import __version__
        return __version__
    except ImportError:
        pass
    
    # Method 2: Try absolute import (if src is in path)
    try:
        import importlib.util
        init_path = Path(__file__).parent.parent.parent / "__init__.py"
        spec = importlib.util.spec_from_file_location("src_init", init_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, '__version__', 'Unknown')
    except Exception:
        pass
    
    # Method 3: Read version directly from file
    try:
        init_file = Path(__file__).parent.parent.parent / "__init__.py"
        with open(init_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('__version__'):
                    version = line.split('=')[1].strip().strip('"').strip("'")
                    return version
    except Exception:
        pass
    
    return "Unknown"

__version__ = _get_version()


class AboutTab(ctk.CTkFrame):
    """Tab displaying application information"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.package_manager = PackageManager()
        
        # Create scrollable frame
        scrollable = ctk.CTkScrollableFrame(self)
        scrollable.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Application info section
        app_frame = ctk.CTkFrame(scrollable)
        app_frame.pack(fill="x", pady=10)
        
        app_header = ctk.CTkFrame(app_frame)
        app_header.pack(anchor="w", padx=10, pady=10, fill="x")
        
        ctk.CTkLabel(
            app_header,
            text="Application Information",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left", padx=5)
        
        # Application name and version
        name_frame = ctk.CTkFrame(app_frame)
        name_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            name_frame,
            text="Video Encoder GUI",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkLabel(
            name_frame,
            text=f"Version {__version__}",
            font=ctk.CTkFont(size=14)
        ).pack(anchor="w", padx=10, pady=2)
        
        # Description
        desc_frame = ctk.CTkFrame(app_frame)
        desc_frame.pack(fill="x", padx=10, pady=5)
        
        desc_text = (
            "A cross-platform Python GUI application for encoding video files "
            "using HandBrake or FFmpeg. Features automatic track detection, "
            "preset management, and real-time progress tracking."
        )
        
        desc_label = ctk.CTkLabel(
            desc_frame,
            text=desc_text,
            anchor="w",
            justify="left",
            wraplength=700
        )
        desc_label.pack(anchor="w", padx=10, pady=5)
        
        # Copyright and License
        copyright_frame = ctk.CTkFrame(app_frame)
        copyright_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            copyright_frame,
            text="Copyright © 2025 Ryan Carr",
            anchor="w"
        ).pack(anchor="w", padx=10, pady=2)
        
        ctk.CTkLabel(
            copyright_frame,
            text="Licensed under the MIT License",
            anchor="w"
        ).pack(anchor="w", padx=10, pady=2)
        
        # System Information
        system_frame = ctk.CTkFrame(scrollable)
        system_frame.pack(fill="x", pady=10)
        
        system_header = ctk.CTkFrame(system_frame)
        system_header.pack(anchor="w", padx=10, pady=10, fill="x")
        
        ctk.CTkLabel(
            system_header,
            text="System Information",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left", padx=5)
        
        # Python version
        python_frame = ctk.CTkFrame(system_frame)
        python_frame.pack(fill="x", padx=10, pady=5)
        
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        ctk.CTkLabel(
            python_frame,
            text=f"Python Version: {python_version}",
            anchor="w"
        ).pack(anchor="w", padx=10, pady=2)
        
        # Platform information
        platform_frame = ctk.CTkFrame(system_frame)
        platform_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            platform_frame,
            text=f"Platform: {platform.system()} {platform.release()}",
            anchor="w"
        ).pack(anchor="w", padx=10, pady=2)
        
        ctk.CTkLabel(
            platform_frame,
            text=f"Architecture: {platform.machine()}",
            anchor="w"
        ).pack(anchor="w", padx=10, pady=2)
        
        # Dependencies section
        deps_frame = ctk.CTkFrame(scrollable)
        deps_frame.pack(fill="x", pady=10)
        
        deps_header = ctk.CTkFrame(deps_frame)
        deps_header.pack(anchor="w", padx=10, pady=10, fill="x")
        
        ctk.CTkLabel(
            deps_header,
            text="Dependencies",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left", padx=5)
        
        # External tools
        tools_frame = ctk.CTkFrame(deps_frame)
        tools_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            tools_frame,
            text="External Tools:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=10, pady=5)
        
        # Store tool info labels for refresh functionality
        self.tool_labels = {}
        
        # FFmpeg
        ffmpeg_info = self._get_tool_info("FFmpeg", self.package_manager.check_ffmpeg)
        self.tool_labels["FFmpeg"] = self._create_tool_label(tools_frame, "FFmpeg", ffmpeg_info)
        
        # HandBrake
        handbrake_info = self._get_tool_info("HandBrake CLI", self.package_manager.check_handbrake)
        self.tool_labels["HandBrake CLI"] = self._create_tool_label(tools_frame, "HandBrake CLI", handbrake_info)
        
        # mkvinfo
        mkvinfo_info = self._get_tool_info("mkvinfo (MKVToolNix)", self.package_manager.check_mkvinfo)
        self.tool_labels["mkvinfo (MKVToolNix)"] = self._create_tool_label(tools_frame, "mkvinfo (MKVToolNix)", mkvinfo_info)
        
        # Python packages
        packages_frame = ctk.CTkFrame(deps_frame)
        packages_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            packages_frame,
            text="Python Packages:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=10, pady=5)
        
        # Get Python package versions
        try:
            import customtkinter
            ctk_version = customtkinter.__version__
        except:
            ctk_version = "Unknown"
        
        try:
            from PIL import __version__ as pillow_version
        except:
            pillow_version = "Unknown"
        
        self._create_package_label(packages_frame, "CustomTkinter", ctk_version)
        self._create_package_label(packages_frame, "Pillow", pillow_version)
        
        # Refresh button
        refresh_frame = ctk.CTkFrame(scrollable)
        refresh_frame.pack(fill="x", pady=20)
        
        refresh_button = ctk.CTkButton(
            refresh_frame,
            text="Refresh Dependencies",
            command=self._refresh_dependencies,
            width=150,
            height=35
        )
        refresh_button.pack(pady=10)
    
    def _get_tool_info(self, name, check_func):
        """Get information about an external tool"""
        found, path = check_func()
        if found:
            # Try to get version
            version = self._get_tool_version(name, path)
            if version:
                return f"✓ Installed ({version}) - {path}"
            else:
                return f"✓ Installed - {path}"
        else:
            return "✗ Not found"
    
    def _get_tool_version(self, tool_name, path):
        """Get version of an external tool"""
        try:
            import subprocess
            if tool_name == "FFmpeg":
                result = subprocess.run(
                    [path, "-version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    # Extract version from first line
                    first_line = result.stdout.split('\n')[0]
                    if 'version' in first_line.lower():
                        parts = first_line.split()
                        for i, part in enumerate(parts):
                            if 'version' in part.lower() and i + 1 < len(parts):
                                return parts[i + 1]
            elif tool_name == "HandBrake CLI":
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    # Extract version from first line
                    first_line = result.stdout.split('\n')[0]
                    if 'HandBrake' in first_line:
                        parts = first_line.split()
                        for i, part in enumerate(parts):
                            if part.replace('.', '').isdigit() and i > 0:
                                return part
            elif tool_name == "mkvinfo (MKVToolNix)":
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    # Extract version from first line
                    first_line = result.stdout.split('\n')[0]
                    if 'mkvinfo' in first_line.lower():
                        parts = first_line.split()
                        for i, part in enumerate(parts):
                            if part.replace('.', '').isdigit() and i > 0:
                                return part
        except Exception:
            pass
        return None
    
    def _create_tool_label(self, parent, name, info):
        """Create a label for an external tool"""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=2)
        
        ctk.CTkLabel(
            frame,
            text=f"{name}:",
            width=150,
            anchor="w"
        ).pack(side="left", padx=5)
        
        info_label = ctk.CTkLabel(
            frame,
            text=info,
            anchor="w",
            wraplength=500
        )
        info_label.pack(side="left", padx=5, fill="x", expand=True)
        
        return info_label
    
    def _create_package_label(self, parent, name, version):
        """Create a label for a Python package"""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=2)
        
        ctk.CTkLabel(
            frame,
            text=f"{name}:",
            width=150,
            anchor="w"
        ).pack(side="left", padx=5)
        
        ctk.CTkLabel(
            frame,
            text=f"Version {version}",
            anchor="w"
        ).pack(side="left", padx=5)
    
    def _refresh_dependencies(self):
        """Refresh dependency information"""
        # Re-check all tools
        self.package_manager = PackageManager()
        
        # Update tool labels
        tool_checks = {
            "FFmpeg": self.package_manager.check_ffmpeg,
            "HandBrake CLI": self.package_manager.check_handbrake,
            "mkvinfo (MKVToolNix)": self.package_manager.check_mkvinfo
        }
        
        for tool_name, check_func in tool_checks.items():
            if tool_name in self.tool_labels:
                new_info = self._get_tool_info(tool_name, check_func)
                self.tool_labels[tool_name].configure(text=new_info)
        
        from tkinter import messagebox
        messagebox.showinfo(
            "Refresh Complete",
            "Dependency information has been refreshed."
        )

