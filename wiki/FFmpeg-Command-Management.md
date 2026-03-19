# FFmpeg Command Management

## Lifecycle: preset → command → edit → save → reuse

1. **Preset**: Select or load a HandBrake preset in the FFmpeg tab. The app generates an FFmpeg command from it (resolution, CRF, codecs, audio, subtitle filter, etc.).
2. **Edit**: Change the command in the text area—add filters, change options, or use the placeholder buttons to insert `{INPUT}`, `{OUTPUT}`, `{AUDIO_TRACK}`, `{SUBTITLE_TRACK}`, `{SUBTITLE_FILE}`.
3. **Save**: Click **Save** and give the command a name. It is stored in config and appears in the **Saved Commands** dropdown for future sessions.
4. **Reuse**: Pick a saved command from the dropdown to load it, or use **Load** to choose from the list. You can also **Load from File** to import a command from a text file, or **Save to File** to export the current command for backup or sharing.

**Reset** restores the command to the one generated from the **currently selected** preset, discarding unsaved edits. **Delete** removes the currently selected saved command from the dropdown and from config.

---

## Placeholder reference

At encode time, the app replaces these placeholders for each file:

| Placeholder | Replaced with |
|-------------|----------------|
| `{INPUT}` | Absolute path to the source file |
| `{OUTPUT}` | Absolute path to the output file |
| `{AUDIO_TRACK}` | Detected English audio track number (1-based for HandBrake/mkvmerge-style mapping; the app converts to stream index where needed) |
| `{SUBTITLE_TRACK}` | Detected subtitle track number |
| `{SUBTITLE_FILE}` | Path to the extracted subtitle file when burning subtitles; if no subtitle file is available, the subtitle filter is removed from the filter chain |

**PGS / HDMV (bitmap) subtitles:** FFmpeg’s `subtitles=` filter only supports **text** subs (libass). At encode time the app rewrites `-vf` to **`filter_complex`** with **`overlay`**, **`setpts=PTS-STARTPTS`**, **`eof_action=pass`**, **`shortest=0`**, and **`ts_sync_mode=nearest`** so sparse PGS frames stay aligned with the video. When a subtitle **stream index** is known, overlay uses **`[0:N]`** from the **same** file as the video (one `-i`) to avoid sidecar timeline drift; otherwise it falls back to a second `-i` on the extracted `.mkv` sidecar. Your preset can still use `subtitles='{SUBTITLE_FILE}'` in `-vf`; that segment is stripped when the rewrite runs.

The literals `input.mkv` and `output.mp4` in the command are also replaced with the actual paths. Angle-bracket variants (e.g. `<INPUT>`) are supported the same way.

---

## Audio loudness normalization (Settings)

In **Settings → Encoding Settings**, **Apply loudness normalization to audio (FFmpeg, single-pass loudnorm)** adds `-af loudnorm=I=…:TP=…:LRA=…` to commands **built by the preset translator** when the option is enabled. Defaults are **I=-16**, **TP=-1.5**, **LRA=11** (integrated single-pass mode, not a separate measure pass).

- **Scope:** FFmpeg tab only; HandBrake CLI encoding is unaffected.
- **Stale commands:** Toggling the setting does not rewrite the command text box. Click **Reset** on the FFmpeg tab (or reload the preset) to regenerate the command. Saved commands and manual edits keep whatever `-af` you wrote.
- **PGS / bitmap subs:** The bitmap overlay rewrite replaces `-vf` with `-filter_complex` for video only; **`-af` and audio encoding options are preserved** in the argument tail.

Optional numeric overrides (for power users) live in config as `audio_normalize_loudnorm_I`, `audio_normalize_loudnorm_TP`, and `audio_normalize_loudnorm_LRA`.

---

## Saving commands with custom names

- Click **Save**, enter a name (e.g. “Anime 1080p”), and the current command text is stored under that name in config (`saved_ffmpeg_commands`).
- Saved commands persist across sessions and appear in the **Saved Commands** dropdown.

---

## Loading: dropdown vs file

- **Dropdown**: Select a saved command by name to load it into the editor. This loads from config.
- **Load from File**: Opens a file dialog so you can load a command from a text file (e.g. a backup or a command shared by someone else). The loaded text replaces the current command in the editor; it is not automatically saved as a named command unless you click **Save**.

---

## Save to file

- **Save to File**: Writes the current command (as plain text) to a file you choose. Use this to back up commands or share them. The file is independent of the app’s saved-commands list.

---

## Reset and delete

- **Reset**: Rebuilds the FFmpeg command from the preset currently selected in the **HandBrake Preset** dropdown and replaces the contents of the command editor. Any unsaved edits are lost.
- **Delete**: Removes the **currently selected** saved command from the dropdown and from config. The editor content is not changed; you can save it again under a new name if you want to keep it.
