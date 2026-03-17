"""Encoder wrapper for HandBrake and FFmpeg"""

import re
import subprocess
import sys
import threading
import time
import os
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from queue import Queue, Empty
import tempfile

from core.subprocess_utils import get_subprocess_kwargs

OUTPUT_FILE_WAIT_MAX_RETRIES = 10
OUTPUT_FILE_INITIAL_DELAY_SEC = 0.1

# Try to import psutil for better process management (optional)
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


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
        
        args = [
            self.handbrake_path,
            "--preset-import-file", str(preset_file),
            "--preset", preset_name,
            "--input", str(input_file),
            "--output", str(output_file),
            "--audio", str(audio_track)
        ]
        
        if subtitle_track is not None:
            # HandBrake CLI uses 1-based track numbers
            args.extend(["--subtitle", str(subtitle_track + 1)])
            args.append("--subtitle-burned")
        
        return self._run_encoder(args, "HandBrake", output_file)
    
    def encode_with_ffmpeg(
        self,
        input_file: Path,
        output_file: Path,
        ffmpeg_args: list,
        subtitle_file: Optional[Path] = None,
        dry_run: bool = False
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
        
        self._log("INFO", f"Prepared FFmpeg command with {len(args)} arguments")
        return self._run_encoder(args, "FFmpeg", output_file)
    
    def _run_encoder(self, args: list, encoder_name: str, output_file: Path) -> bool:
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
            if encoder_exe and not encoder_exe.startswith("ffmpeg") and not Path(encoder_exe).exists():
                self._log("ERROR", f"Encoder executable not found: {encoder_exe}")
                return False
            
            self._log("INFO", f"Launching {encoder_name} process...")
            try:
                # Hide console window on Windows (for release builds)
                popen_kwargs = {
                    'args': args,
                    'stdout': subprocess.PIPE,
                    'stderr': subprocess.PIPE,
                    'text': True,
                    'bufsize': 1,
                    'universal_newlines': True,
                    'shell': False
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
                    with self._process_lock:
                        self._current_process = None
                    return False

                self._drain_stdout_queue(stdout_queue, encoder_name)
                self._drain_stderr_queue(stderr_queue, encoder_name)
                time.sleep(0.05)
            
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
            
            if process.returncode == 0:
                # Wait for output file to be created (with retry)
                if self._wait_for_file(output_file):
                    self._log("SUCCESS", f"Encoding completed: {output_file.name}")
                    return True
                else:
                    self._log("ERROR", "Process completed but output file not found")
                    return False
            else:
                self._log("ERROR", f"{encoder_name} exited with code {process.returncode}")
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
        """Wait for output file to be created"""
        retry_count = 0
        while retry_count < max_retries:
            if file_path.exists():
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
            
            # Fallback: Use taskkill command on Windows
            try:
                run_kw: Dict[str, Any] = {
                    "args": ["taskkill", "/F", "/T", "/PID", str(pid)],
                    "capture_output": True,
                    "timeout": 5,
                }
                run_kw.update(get_subprocess_kwargs())
                subprocess.run(**run_kw)
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                pass
        except OSError:
            pass
    
    def _force_kill_process(self, process: subprocess.Popen):
        """Forcefully kill a process and its children (runs in separate thread)"""
        try:
            if process.poll() is None:
                # Process is still running, wait a bit for graceful termination
                time.sleep(0.5)
                
                if process.poll() is None:
                    # Still running, force kill
                    if sys.platform == 'win32':
                        # On Windows, kill the process tree
                        self._kill_process_tree_windows(process.pid)
                    else:
                        # On Unix, try kill first, then SIGKILL
                        try:
                            process.kill()
                        except OSError:
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
    
    def stop(self):
        """Stop the current encoding with forceful termination"""
        self._stop_event.set()
        
        with self._process_lock:
            if self._current_process:
                try:
                    # Close pipes to unblock reading threads
                    self._close_pipes(self._current_process)
                    
                    # Terminate immediately, don't wait
                    try:
                        self._current_process.terminate()
                    except OSError:
                        pass
                    threading.Thread(
                        target=self._force_kill_process,
                        args=(self._current_process,),
                        daemon=True
                    ).start()
                except OSError:
                    pass
    
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
) -> Optional[Path]:
    """Extract subtitle stream to temporary file"""
    if output_file is None:
        # Create temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.ass')
        os.close(temp_fd)
        output_file = Path(temp_path)
    
    try:
        args = [
            ffmpeg_path,
            "-i", str(input_file),
            "-map", f"0:{subtitle_stream_id}",
            "-c", "copy",
            "-y",
            str(output_file)
        ]
        
        # Hide console window on Windows (for release builds)
        run_kwargs = {
            'args': args,
            'capture_output': True,
            'text': True,
            'timeout': 30
        }
        run_kwargs.update(get_subprocess_kwargs())
        
        result = subprocess.run(**run_kwargs)
        
        if result.returncode == 0 and output_file.exists():
            # Verify file is not empty
            if output_file.stat().st_size > 0:
                return output_file
            else:
                # Empty file, remove it
                output_file.unlink()
                return None
        else:
            # Log extraction failure
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Subtitle extraction failed: returncode={result.returncode}")
            if result.stderr:
                logger.error(f"FFmpeg error: {result.stderr}")
            if output_file.exists():
                output_file.unlink()
            return None
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError) as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Subtitle extraction exception: {e}")
        if output_file.exists():
            output_file.unlink()
        return None

