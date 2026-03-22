"""Encoder wrapper for HandBrake and FFmpeg"""

import logging
import re
import shlex
import subprocess
import sys
import threading
import time
import os
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List, Tuple
from queue import Queue, Empty
import tempfile

from core.subprocess_utils import get_subprocess_kwargs
from core.ffmpeg_bitmap_subtitle_burn import rewrite_ffmpeg_args_for_bitmap_subtitle_overlay

logger = logging.getLogger(__name__)

OUTPUT_FILE_WAIT_MAX_RETRIES = 10
OUTPUT_FILE_INITIAL_DELAY_SEC = 0.1
OUTPUT_FILE_STABILITY_DELAY_SEC = 0.15

# Subtitle codec grouping
TEXT_SUBTITLE_CODECS = {"subrip", "ass", "ssa", "webvtt"}
BITMAP_SUBTITLE_CODECS = {"hdmv_pgs_subtitle", "pgssub", "dvd_subtitle"}

# Container compatibility for subtitle muxing
CONTAINER_SUBTITLE_SUPPORT = {
    # (codec, container) -> (supported, method, warning)
    ("subrip", "mp4"): (True, "mov_text", None),
    ("ass", "mp4"): (True, "mov_text", "ASS styling may be lost when muxed to MP4"),
    ("pgssub", "mp4"): (False, None, "PGS cannot be muxed into MP4"),
    ("pgssub", "mkv"): (True, "copy", None),
    ("ass", "mkv"): (True, "copy", None),
    ("subrip", "mkv"): (True, "copy", None),
}

# Subtitle action types
SUBTITLE_ACTION_TYPES = {"mux", "keep_external", "burn", "omit", "skip_file"}


def can_mux_to_container(codec: str, container: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Check if subtitle codec can be muxed to target container.

    Returns: (supported: bool, method: Optional[str], warning: Optional[str])
    """
    return CONTAINER_SUBTITLE_SUPPORT.get(
        (codec, container),
        (False, None, f"Muxing {codec} to {container} not supported")
    )


class SubtitleInfo:
    """Normalized subtitle information from file detection"""

    def __init__(self):
        self.external_text: Optional[Path] = None    # Path to .srt/.vtt file
        self.external_ass: Optional[Path] = None     # Path to .ass file
        self.embedded: List[Dict[str, Any]] = []     # List of embedded subtitle streams
                                                      # {"index": int, "codec": str, "type": "text"|"bitmap"}

    @property
    def has_any(self) -> bool:
        """True if any subtitle source exists"""
        return bool(self.external_text or self.external_ass or self.embedded)


class SubtitleDecision:
    """Result of applying subtitle policy to detected subtitles"""

    def __init__(self, action: str = "omit", reason: str = "No subtitles found"):
        self.action = action                         # One of SUBTITLE_ACTION_TYPES
        self.reason = reason                         # Explanation of the decision
        self.warnings: List[str] = []                # Warnings about the decision
        self.source: Optional[str] = None            # "embedded_text"|"embedded_bitmap"|"external_text"|"external_ass"
        self.stream_index: Optional[int] = None      # Index of embedded stream (if applicable)
        self.codec: Optional[str] = None             # Codec name (subrip, ass, pgssub, etc.)

# Try to import psutil for better process management (optional)
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def _windows_taskkill_path() -> str:
    exe = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "taskkill.exe"
    return str(exe) if exe.is_file() else "taskkill"


def format_cli_argv(argv: List[str]) -> str:
    """Format argument list for display (Windows uses cmd-style quoting)."""
    if not argv:
        return ""
    if sys.platform == "win32":
        return subprocess.list2cmdline(argv)
    return shlex.join(argv)


def detect_subtitles(video_file: Path, ffprobe_path: Optional[str] = None) -> SubtitleInfo:
    """Detect all subtitle sources in a video file.

    Checks for:
    - External subtitle files (.srt, .ass) in the same directory
    - Embedded subtitle streams using ffprobe

    Args:
        video_file: Path to the video file
        ffprobe_path: Optional path to ffprobe executable. If None, uses "ffprobe" from PATH

    Returns:
        SubtitleInfo with detected external and embedded subtitle sources
    """
    info = SubtitleInfo()

    # Check for external subtitle files
    srt = video_file.with_suffix('.srt')
    ass = video_file.with_suffix('.ass')

    if srt.exists():
        info.external_text = srt
    if ass.exists():
        info.external_ass = ass

    # Probe for embedded subtitle streams
    try:
        ffprobe = ffprobe_path or "ffprobe"
        cmd = [
            ffprobe,
            "-select_streams", "s",
            "-show_entries", "stream=index,codec_name",
            "-of", "json",
            str(video_file)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )

        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            streams = data.get("streams", [])

            for stream in streams:
                index = stream.get("index")
                codec = stream.get("codec_name", "unknown")

                if codec in TEXT_SUBTITLE_CODECS:
                    subtitle_type = "text"
                elif codec in BITMAP_SUBTITLE_CODECS:
                    subtitle_type = "bitmap"
                else:
                    # Unknown subtitle codec, treat as text
                    subtitle_type = "text"

                info.embedded.append({
                    "index": index,
                    "codec": codec,
                    "type": subtitle_type
                })

    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError) as e:
        # If ffprobe fails, we silently continue with just external file detection
        logger.debug(f"FFprobe failed to detect embedded subtitles: {e}")

    return info


def process_file_subtitles(
    video_file: Path,
    config: Dict[str, Any],
    ffmpeg_path: str,
    ffprobe_path: Optional[str] = None,
    log_callback: Optional[Callable[[str, str], None]] = None
) -> SubtitleDecision:
    """Detect and decide subtitle handling for a file.

    Integrates subtitle detection with policy application.

    Args:
        video_file: Path to the video file
        config: Configuration dict with subtitle_handling settings
        ffmpeg_path: Path to ffmpeg executable
        ffprobe_path: Optional path to ffprobe executable
        log_callback: Optional callback for logging decisions

    Returns:
        SubtitleDecision with the chosen action
    """
    # Import here to avoid circular imports
    from core.subtitle_policy import decide_subtitle_action

    # Detect subtitles
    subtitle_info = detect_subtitles(video_file, ffprobe_path)

    # Apply policy
    decision = decide_subtitle_action(subtitle_info, config)

    # Log if callback provided
    if log_callback:
        log_callback("INFO", f"Subtitle handling for {video_file.name}: {decision.reason}")
        for warning in decision.warnings:
            log_callback("WARNING", warning)

    return decision


def build_subtitle_ffmpeg_args(
    decision: SubtitleDecision,
    subtitle_info: SubtitleInfo,
    base_args: List[str]
) -> List[str]:
    """Modify FFmpeg arguments based on subtitle decision.

    Handles:
    - Removing subtitle filters for mux/omit decisions
    - Adding -map arguments for muxing
    - Setting subtitle codec for muxing

    Args:
        decision: The subtitle decision from policy
        subtitle_info: Detected subtitle sources
        base_args: Original FFmpeg argument list

    Returns:
        Modified FFmpeg arguments
    """
    args = base_args.copy()

    # Handle different actions
    if decision.action == "mux":
        # Remove subtitle burning filters
        args = [arg for arg in args if not (
            isinstance(arg, str) and (
                arg.startswith("subtitles=") or
                "subtitles=" in arg or
                "-vf" in arg and "subtitles" in args[args.index(arg)+1] if args.index(arg)+1 < len(args) else False
            )
        )]

        # Determine which subtitle stream to mux
        if decision.source == "external_text":
            # Will be added separately with -i
            pass
        elif decision.source in ("embedded_text", "embedded_ass"):
            # Add -map argument for embedded stream
            stream_index = decision.stream_index
            if stream_index is not None:
                # Add mapping for subtitle stream
                if "-map" in args:
                    # Insert after last -map
                    last_map_idx = len(args) - 1 - args[::-1].index("-map") - 1
                    args.insert(last_map_idx + 2, f"0:s:{stream_index}")
                    args.insert(last_map_idx + 1, "-map")
            # Add subtitle codec for muxing
            if "-c:s" not in args:
                args.extend(["-c:s", "mov_text"])

    elif decision.action == "omit":
        # Remove subtitle-related arguments and filters
        new_args = []
        skip_next = False
        for i, arg in enumerate(args):
            if skip_next:
                skip_next = False
                continue
            if arg == "-map" and i + 1 < len(args) and "0:s" in args[i + 1]:
                skip_next = True
                continue
            if arg.startswith("subtitles=") or "subtitles=" in arg:
                continue
            new_args.append(arg)
        args = new_args

    elif decision.action == "skip_file":
        # Return empty args as signal to skip
        return []

    return args


class EncodingProgress:
    """Represents encoding progress"""
    
    def __init__(self):
        self.percent: Optional[float] = None
        self.time: Optional[str] = None
        self.speed: Optional[float] = None
        self.eta: Optional[str] = None
        self.fps: Optional[float] = None


class Encoder:
    """Handles encoding with HandBrake or FFmpeg"""
    
    def __init__(
        self,
        ffmpeg_path: str,
        handbrake_path: str,
        progress_callback: Optional[Callable[[EncodingProgress], None]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None
    ):
        self.ffmpeg_path = ffmpeg_path
        self.handbrake_path = handbrake_path
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self._stop_event = threading.Event()
        self._input_duration: Optional[float] = None  # Duration in seconds
        self._current_process: Optional[subprocess.Popen] = None
        self._process_lock = threading.Lock()  # Thread-safe access to process
        self._stdout_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None

    def build_handbrake_argv(
        self,
        input_file: Path,
        output_file: Path,
        preset_file: Path,
        preset_name: str,
        audio_track: int,
        subtitle_track: Optional[int] = None,
    ) -> List[str]:
        """Argument vector for HandBrakeCLI (same order as ``encode_with_handbrake``)."""
        args = [
            self.handbrake_path,
            "--preset-import-file", str(preset_file),
            "--preset", preset_name,
            "--input", str(input_file),
            "--output", str(output_file),
            "--audio", str(audio_track),
        ]
        if subtitle_track is not None:
            args.extend(["--subtitle", str(subtitle_track + 1)])
            args.append("--subtitle-burned")
        return args

    def encode_with_handbrake(
        self,
        input_file: Path,
        output_file: Path,
        preset_file: Path,
        preset_name: str,
        audio_track: int,
        subtitle_track: Optional[int] = None,
        dry_run: bool = False
    ) -> bool:
        """Encode using HandBrake"""
        if dry_run:
            self._log("INFO", f"DRY RUN: Would encode {input_file} to {output_file}")
            return True

        args = self.build_handbrake_argv(
            input_file=input_file,
            output_file=output_file,
            preset_file=preset_file,
            preset_name=preset_name,
            audio_track=audio_track,
            subtitle_track=subtitle_track,
        )
        return self._run_encoder(args, "HandBrake", output_file)
    
    def encode_with_ffmpeg(
        self,
        input_file: Path,
        output_file: Path,
        ffmpeg_args: list,
        subtitle_file: Optional[Path] = None,
        subtitle_stream_index: Optional[int] = None,
        *,
        skip_bitmap_subtitle_overlay_rewrite: bool = False,
        dry_run: bool = False,
    ) -> bool:
        """Encode using FFmpeg"""
        if dry_run:
            self._log("INFO", f"DRY RUN: Would encode {input_file} to {output_file}")
            return True
        
        if not ffmpeg_args:
            self._log("ERROR", "FFmpeg args list is empty")
            return False
        
        # Replace placeholder paths in args
        args = []
        for arg in ffmpeg_args:
            if arg == "ffmpeg":
                args.append(self.ffmpeg_path)
            else:
                args.append(arg)

        if (
            not skip_bitmap_subtitle_overlay_rewrite
            and (subtitle_file is not None or subtitle_stream_index is not None)
        ):
            rewritten = rewrite_ffmpeg_args_for_bitmap_subtitle_overlay(
                args,
                main_subtitle_stream_index=subtitle_stream_index,
                sidecar_sub_path=Path(subtitle_file).expanduser() if subtitle_file else None,
            )
            if rewritten is not None:
                if subtitle_stream_index is not None:
                    self._log(
                        "INFO",
                        "PGS/bitmap subtitles: filter_complex overlay from main file stream "
                        f"{subtitle_stream_index} (avoids sidecar timeline drift).",
                    )
                else:
                    self._log(
                        "INFO",
                        "PGS/bitmap subtitles: filter_complex overlay from sidecar (subtitles= is text-only).",
                    )
                args = rewritten

        self._log("INFO", f"Prepared FFmpeg command with {len(args)} arguments")
        return self._run_encoder(args, "FFmpeg", output_file)

    def run_ffmpeg_argv(
        self,
        argv: List[str],
        output_file: Optional[Path] = None,
    ) -> bool:
        """Run an FFmpeg argument vector (first element may be the literal token ``ffmpeg``)."""
        if not argv:
            self._log("ERROR", "FFmpeg argv is empty")
            return False
        args: List[str] = []
        for arg in argv:
            if arg == "ffmpeg":
                args.append(self.ffmpeg_path)
            else:
                args.append(arg)
        self._log("INFO", f"Prepared FFmpeg command with {len(args)} arguments")
        return self._run_encoder(args, "FFmpeg", output_file)
    
    def _run_encoder(self, args: list, encoder_name: str, output_file: Optional[Path]) -> bool:
        """Run the encoder process"""
        try:
            # Reset duration for new encoding
            self._input_duration = None
            
            self._log("INFO", f"Starting {encoder_name} encoding...")
            # Format command for display (quote paths with spaces for readability)
            cmd_display = []
            for arg in args:
                if ' ' in arg and not (arg.startswith('"') and arg.endswith('"')):
                    cmd_display.append(f'"{arg}"')
                else:
                    cmd_display.append(arg)
            self._log("INFO", f"Command: {' '.join(cmd_display)}")
            
            # Check if encoder executable exists
            encoder_exe = args[0] if args else None
            if encoder_exe:
                # Strip quotes that may have been added by shlex.quote()
                encoder_exe_check = encoder_exe.strip("'\"")
                if not encoder_exe_check.startswith("ffmpeg") and not Path(encoder_exe_check).exists():
                    self._log("ERROR", f"Encoder executable not found: {encoder_exe_check}")
                    return False
            
            self._log("INFO", f"Launching {encoder_name} process...")
            try:
                # Hide console window on Windows (for release builds)
                popen_kwargs = {
                    'args': args,
                    'stdin': subprocess.DEVNULL,
                    'stdout': subprocess.PIPE,
                    'stderr': subprocess.PIPE,
                    'text': True,
                    'encoding': 'utf-8',
                    'errors': 'replace',
                    'bufsize': 1,
                    'shell': False,
                }
                popen_kwargs.update(get_subprocess_kwargs())
                
                process = subprocess.Popen(**popen_kwargs)
                self._log("INFO", f"Process started (PID: {process.pid})")
                
                # Store process reference for forceful termination
                with self._process_lock:
                    self._current_process = process
            except FileNotFoundError as e:
                self._log("ERROR", f"Encoder executable not found: {args[0] if args else 'unknown'}")
                self._log("ERROR", f"Error details: {str(e)}")
                return False
            except OSError as e:
                self._log("ERROR", f"Failed to start subprocess: {str(e)}")
                import traceback
                self._log("ERROR", f"Traceback: {traceback.format_exc()}")
                return False
            
            stdout_queue: Queue = Queue()
            stderr_queue: Queue = Queue()
            stdout_thread = threading.Thread(
                target=self._read_output,
                args=(process.stdout, stdout_queue),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=self._read_output,
                args=(process.stderr, stderr_queue),
                daemon=True
            )
            self._stdout_thread = stdout_thread
            self._stderr_thread = stderr_thread
            try:
                stdout_thread.start()
                stderr_thread.start()
            except RuntimeError as e:
                self._log("ERROR", f"Failed to start output reader threads: {e}")
                self._terminate_orphan_encoder_process(process)
                with self._process_lock:
                    self._current_process = None
                return False

            while process.poll() is None:
                if self._stop_event.is_set():
                    self._log("INFO", "Stop event set, terminating process...")
                    # Kill before closing pipes (closing first can deadlock with reader threads)
                    self._ensure_encoder_dead(process)
                    self._close_pipes(process)
                    with self._process_lock:
                        self._current_process = None
                    return False

                self._drain_stdout_queue(stdout_queue, encoder_name)
                self._drain_stderr_queue(stderr_queue, encoder_name)
                time.sleep(0.05)

            # stop() may have taskkilled from another thread while we were sleeping
            if self._stop_event.is_set():
                self._log("INFO", "Encode stopped (process ended after stop request)")
                self._close_pipes(process)
                with self._process_lock:
                    self._current_process = None
                if stdout_thread.is_alive():
                    stdout_thread.join(timeout=1)
                if stderr_thread.is_alive():
                    stderr_thread.join(timeout=1)
                return False
            
            # Get remaining output
            self._log("INFO", f"Process finished with return code: {process.returncode}")
            
            # Clear process reference
            with self._process_lock:
                self._current_process = None
            
            # Close pipes to unblock reading threads
            self._close_pipes(process)
            
            # Wait for threads with timeout to prevent hanging
            if stdout_thread.is_alive():
                stdout_thread.join(timeout=1)
            if stderr_thread.is_alive():
                stderr_thread.join(timeout=1)
            
            stderr_lines: List[str] = []
            self._drain_stdout_queue(stdout_queue, encoder_name)
            self._drain_stderr_queue(stderr_queue, encoder_name, stderr_lines)
            
            # If process failed, log all stderr as error
            if process.returncode != 0:
                error_output = '\n'.join(stderr_lines)
                if error_output:
                    self._log("ERROR", f"{encoder_name} error output:\n{error_output}")
                self._log("ERROR", f"{encoder_name} exited with code {process.returncode}")
                return False

            if output_file is None:
                self._log("SUCCESS", f"{encoder_name} completed")
                return True
            if self._wait_for_file(output_file):
                self._log("SUCCESS", f"Encoding completed: {output_file.name}")
                return True
            self._log("ERROR", "Process completed but output file not found or not stable")
            return False
                
        except Exception as e:
            self._log("ERROR", f"Error encoding: {str(e)}")
            import traceback
            self._log("ERROR", f"Traceback: {traceback.format_exc()}")
            with self._process_lock:
                proc = self._current_process
                if proc:
                    try:
                        self._close_pipes(proc)
                        if sys.platform == 'win32':
                            self._kill_process_tree_windows(proc.pid)
                        else:
                            proc.kill()
                    except OSError:
                        pass
                self._current_process = None
            return False
    
    def _terminate_orphan_encoder_process(self, process: subprocess.Popen) -> None:
        """Stop a started encoder if reader threads failed to start."""
        if process.poll() is not None:
            return
        self._close_pipes(process)
        try:
            process.terminate()
        except OSError:
            pass
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            try:
                if sys.platform == 'win32':
                    self._kill_process_tree_windows(process.pid)
                else:
                    process.kill()
            except OSError:
                pass

    def _drain_stdout_queue(self, stdout_queue: Queue, encoder_name: str) -> None:
        while True:
            try:
                line = stdout_queue.get_nowait()
                self._log("INFO", f"[{encoder_name}] {line}")
            except Empty:
                break

    def _drain_stderr_queue(
        self, stderr_queue: Queue, encoder_name: str, stderr_lines: Optional[List[str]] = None
    ) -> None:
        while True:
            try:
                line = stderr_queue.get_nowait()
                if stderr_lines is not None:
                    stderr_lines.append(line)
                self._parse_progress(line, encoder_name)
                self._log("DEBUG", f"[{encoder_name}] {line}")
            except Empty:
                break

    def _read_output(self, pipe, queue: Queue):
        """Read output from pipe and put in queue"""
        try:
            for line in iter(pipe.readline, ''):
                if line:
                    queue.put(line.strip())
        except OSError:
            pass
    
    def _time_to_seconds(self, time_str: str) -> float:
        """Convert time string (HH:MM:SS.mm) to seconds"""
        try:
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        except (ValueError, IndexError):
            return 0.0
    
    def _parse_duration_from_line(self, line: str) -> Optional[float]:
        """Parse duration from FFmpeg output line like 'Duration: 00:23:45.67'"""
        duration_match = re.search(r'Duration:\s*(\d{2}:\d{2}:\d{2}\.\d{2})', line)
        if duration_match:
            return self._time_to_seconds(duration_match.group(1))
        return None
    
    def _parse_progress(self, line: str, encoder_name: str):
        """Parse progress from encoder output"""
        progress = EncodingProgress()
        
        if encoder_name == "FFmpeg":
            # Try to extract duration from initial FFmpeg output
            if self._input_duration is None:
                duration = self._parse_duration_from_line(line)
                if duration:
                    self._input_duration = duration
                    self._log("DEBUG", f"Detected video duration: {duration:.2f} seconds")
            
            # Parse FFmpeg progress: time=00:00:05.12 speed=1.5x fps=40.0
            time_match = re.search(r'time=(\d{2}:\d{2}:\d{2}\.\d{2})', line)
            speed_match = re.search(r'speed=\s*([\d.]+)x', line)
            fps_match = re.search(r'fps=\s*([\d.]+)', line)
            
            if time_match:
                progress.time = time_match.group(1)
                current_time_sec = self._time_to_seconds(progress.time)
                
                # Calculate percentage if we have duration
                if self._input_duration and self._input_duration > 0:
                    progress.percent = min(100.0, (current_time_sec / self._input_duration) * 100.0)
            
            if speed_match:
                try:
                    progress.speed = float(speed_match.group(1))
                    # Calculate ETA if we have both duration and current time
                    if time_match and self._input_duration and self._input_duration > 0:
                        current_time_sec = self._time_to_seconds(progress.time)
                        # Only calculate ETA if speed is valid and non-zero
                        if progress.speed and progress.speed > 0:
                            remaining_time_sec = (self._input_duration - current_time_sec) / progress.speed
                            if remaining_time_sec > 0:
                                hours = int(remaining_time_sec // 3600)
                                minutes = int((remaining_time_sec % 3600) // 60)
                                seconds = int(remaining_time_sec % 60)
                                progress.eta = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                except (ValueError, ZeroDivisionError):
                    # Skip ETA calculation if speed is invalid or zero
                    pass
            
            if fps_match:
                progress.fps = float(fps_match.group(1))
        
        elif encoder_name == "HandBrake":
            # Parse HandBrake progress: Encoding: task 1 of 1, 45.67 % (12.34 fps, avg 11.23 fps, ETA 00:05:30)
            percent_match = re.search(r'Encoding: task \d+ of \d+, ([\d.]+) %', line)
            eta_match = re.search(r'ETA (\d{2}:\d{2}:\d{2})', line)
            fps_match = re.search(r'([\d.]+) fps', line)
            
            if percent_match:
                progress.percent = float(percent_match.group(1))
            if eta_match:
                progress.eta = eta_match.group(1)
            if fps_match:
                progress.fps = float(fps_match.group(1))
        
        if self.progress_callback:
            self.progress_callback(progress)
    
    def _wait_for_file(self, file_path: Path, max_retries: int = OUTPUT_FILE_WAIT_MAX_RETRIES) -> bool:
        """Wait until output exists, is non-empty, and size is stable briefly (not mid-write)."""
        retry_count = 0
        while retry_count < max_retries:
            if file_path.exists():
                try:
                    size_first = file_path.stat().st_size
                except OSError:
                    size_first = 0
                if size_first > 0:
                    time.sleep(OUTPUT_FILE_STABILITY_DELAY_SEC)
                    try:
                        size_second = file_path.stat().st_size
                    except OSError:
                        size_second = 0
                    if size_first == size_second and size_second > 0:
                        return True
            retry_count += 1
            delay = OUTPUT_FILE_INITIAL_DELAY_SEC * (2 ** (retry_count - 1))
            time.sleep(delay)
        return False
    
    def _log(self, level: str, message: str):
        """Log a message"""
        if self.log_callback:
            self.log_callback(level, message)
    
    def _kill_process_tree_windows(self, pid: int):
        """Kill process tree on Windows using taskkill or Windows API"""
        try:
            if HAS_PSUTIL:
                # Use psutil for clean process tree killing
                try:
                    parent = psutil.Process(pid)
                    children = parent.children(recursive=True)
                    for child in children:
                        try:
                            child.terminate()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    try:
                        parent.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    # Wait a bit, then force kill
                    gone, alive = psutil.wait_procs(children + [parent], timeout=2)
                    for proc in alive:
                        try:
                            proc.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    return
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Fallback: Use taskkill command on Windows (full path for frozen/PATH-less runs)
            try:
                run_kw: Dict[str, Any] = {
                    "args": [_windows_taskkill_path(), "/F", "/T", "/PID", str(pid)],
                    "stdin": subprocess.DEVNULL,
                    "capture_output": True,
                    "timeout": 5,
                }
                run_kw.update(get_subprocess_kwargs())
                subprocess.run(**run_kw)
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                pass
        except OSError:
            pass
    
    def _close_pipes(self, process: subprocess.Popen):
        """Close process pipes to unblock reading threads"""
        try:
            if process.stdout:
                process.stdout.close()
        except OSError:
            pass
        try:
            if process.stderr:
                process.stderr.close()
        except OSError:
            pass

    def _ensure_encoder_dead(self, process: subprocess.Popen) -> None:
        """Force-kill encoder until reaped. Windows: taskkill /F /T (full System32 path); Unix: SIGKILL."""
        pid = process.pid
        if pid is None:
            return
        if sys.platform == "win32":
            taskkill_exe = _windows_taskkill_path()
            for attempt in range(30):
                if process.poll() is not None:
                    return
                try:
                    run_kw: Dict[str, Any] = {
                        "args": [taskkill_exe, "/F", "/T", "/PID", str(pid)],
                        "stdin": subprocess.DEVNULL,
                        "capture_output": True,
                        "text": True,
                        "encoding": "utf-8",
                        "errors": "replace",
                        "timeout": 45,
                    }
                    run_kw.update(get_subprocess_kwargs())
                    result = subprocess.run(**run_kw)
                    if process.poll() is not None:
                        return
                    err = (result.stderr or result.stdout or "").strip()
                    if err and attempt == 0:
                        self._log("WARNING", f"taskkill PID {pid} rc={result.returncode}: {err[:300]}")
                    elif result.returncode != 0 and attempt == 0:
                        self._log("WARNING", f"taskkill PID {pid} exited {result.returncode}")
                except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
                    self._log("WARNING", f"taskkill PID {pid} attempt {attempt + 1}: {e}")
                time.sleep(0.2)
            if process.poll() is None:
                self._log("ERROR", f"Encoder PID {pid} still running after repeated taskkill; try Task Manager")
        else:
            for _ in range(25):
                if process.poll() is not None:
                    return
                try:
                    process.kill()
                except OSError:
                    pass
                time.sleep(0.15)
            if process.poll() is None and HAS_PSUTIL:
                try:
                    p = psutil.Process(pid)
                    for child in p.children(recursive=True):
                        try:
                            child.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    p.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
    
    def stop(self):
        """Stop the current encoding with forceful termination"""
        self._stop_event.set()
        with self._process_lock:
            proc = self._current_process
        # Do NOT call _close_pipes here: it can block/deadlock with reader threads on Windows
        # and would prevent the killer thread from ever starting. Killer runs taskkill first.
        if proc:
            threading.Thread(
                target=lambda p=proc: self._ensure_encoder_dead(p),
                daemon=True,
            ).start()
    
    def reset_stop_event(self):
        """Reset the stop event"""
        self._stop_event.clear()
        with self._process_lock:
            self._current_process = None


def extract_subtitle_stream(
    ffmpeg_path: str,
    input_file: Path,
    subtitle_stream_id: int,
    output_file: Optional[Path] = None
) -> Tuple[Optional[Path], Optional[str]]:
    """Extract one subtitle stream with stream copy into a temporary Matroska file.

    PGS / HDMV and most embedded subs are not ASS text; muxing them into ``.ass``
    fails. Matroska accepts these codecs, and FFmpeg's ``subtitles=`` filter can
    read subtitle streams from such a file.

    Returns ``(path, None)`` on success, or ``(None, error_summary)`` on failure.
    """
    if output_file is None:
        temp_fd, temp_path = tempfile.mkstemp(suffix=".mkv")
        os.close(temp_fd)
        output_file = Path(temp_path)

    def _fail(stderr: Optional[str], exc: Optional[BaseException] = None) -> Tuple[Optional[Path], Optional[str]]:
        if output_file.exists():
            try:
                output_file.unlink()
            except OSError:
                pass
        detail = (stderr or "").strip()
        if exc is not None:
            detail = f"{type(exc).__name__}: {exc}" + (f" | {detail}" if detail else "")
        if len(detail) > 1200:
            detail = detail[:1200] + "…"
        if detail:
            logger.error("Subtitle extraction failed: %s", detail)
        else:
            logger.error("Subtitle extraction failed (no stderr)")
        return None, detail or None

    try:
        args = [
            ffmpeg_path,
            "-i", str(input_file),
            "-map", f"0:{subtitle_stream_id}",
            "-c", "copy",
            "-y",
            str(output_file),
        ]

        run_kwargs = {
            "args": args,
            "stdin": subprocess.DEVNULL,
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "timeout": 120,
        }
        run_kwargs.update(get_subprocess_kwargs())

        result = subprocess.run(**run_kwargs)

        if result.returncode == 0 and output_file.exists():
            if output_file.stat().st_size > 0:
                return output_file, None
            output_file.unlink()
            return _fail(result.stderr, None)

        return _fail(result.stderr, None)
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError) as e:
        return _fail(None, e)


def extract_text_subtitle_to_file(
    ffmpeg_path: str,
    input_file: Path,
    subtitle_codec: str,
    subtitle_stream_id: int,
    output_file: Path
) -> Tuple[Optional[Path], Optional[str]]:
    """Extract a text-based subtitle stream to .srt or .ass file.

    Only works for text subtitle codecs (subrip, ass, webvtt, ssa).
    Skips bitmap subtitles (pgssub, hdmv_pgs_subtitle, dvd_subtitle).

    Args:
        ffmpeg_path: Path to ffmpeg executable
        input_file: Source video file
        subtitle_codec: Codec name (subrip, ass, ssa, webvtt, etc.)
        subtitle_stream_id: Global FFmpeg stream index (as in ffprobe ``stream.index`` / ``Stream #0:N``)
        output_file: Output file path (should be .srt or .ass based on codec)

    Returns:
        (output_file_path, None) on success, or (None, error_message) on failure
    """
    # Skip bitmap subtitles - they cannot be extracted to text files
    if subtitle_codec in BITMAP_SUBTITLE_CODECS:
        return None, f"Cannot extract bitmap subtitle codec '{subtitle_codec}' to text file"

    # Map codec to output format
    codec_to_format = {
        "subrip": "srt",
        "ass": "ass",
        "ssa": "ass",
        "webvtt": "vtt",
    }

    if subtitle_codec not in codec_to_format:
        return None, f"Unsupported subtitle codec '{subtitle_codec}'"

    def _fail(stderr: Optional[str], exc: Optional[BaseException] = None) -> Tuple[Optional[Path], Optional[str]]:
        if output_file.exists():
            try:
                output_file.unlink()
            except OSError:
                pass
        detail = (stderr or "").strip()
        if exc is not None:
            detail = f"{type(exc).__name__}: {exc}" + (f" | {detail}" if detail else "")
        if len(detail) > 1200:
            detail = detail[:1200] + "…"
        if detail:
            logger.error("Text subtitle extraction failed: %s", detail)
        else:
            logger.error("Text subtitle extraction failed (no stderr)")
        return None, detail or None

    try:
        args = [
            ffmpeg_path,
            "-i", str(input_file),
            "-map", f"0:{subtitle_stream_id}",
            "-c:s", "copy",
            "-y",
            str(output_file),
        ]

        run_kwargs = {
            "args": args,
            "stdin": subprocess.DEVNULL,
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "timeout": 120,
        }
        run_kwargs.update(get_subprocess_kwargs())

        result = subprocess.run(**run_kwargs)

        if result.returncode == 0 and output_file.exists():
            if output_file.stat().st_size > 0:
                logger.info(f"Extracted {subtitle_codec} subtitle to {output_file}")
                return output_file, None
            output_file.unlink()
            return _fail(result.stderr, None)

        return _fail(result.stderr, None)
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError) as e:
        return _fail(None, e)

