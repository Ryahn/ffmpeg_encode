# Track Detection

## Why automatic track detection?

MKV files—especially anime and multi-language releases—often contain several audio tracks (e.g. Japanese, English dub, commentary) and several subtitle tracks (full dialogue, Signs & Songs only, different languages). Manually picking the right tracks for every file would be tedious. The app **automatically** selects:

- An **English audio** track (for encoding)
- A **Signs & Songs**–style subtitle track (for burning in, when desired)

Detection uses configurable language tags, name patterns, and exclude patterns so you can adapt to different release naming conventions.

## How detection works

For **MKV** files, the app uses **mkvinfo** (from MKVToolNix) to read track metadata (type, language, name). It then applies your configured rules in this order:

1. **Language tags**: Match tracks whose language tag equals or starts with one of the configured tags (e.g. `en`, `eng`). For subtitles, you can match “English” or, if your setup supports it, a wildcard for any language (see note below).
2. **Name patterns**: For audio, regex patterns matched against the track name (e.g. `English`, `ENG`). For subtitles, name patterns identify “Signs & Songs”–style tracks (e.g. `Signs.*Songs`, `Signs$`, `English Signs`).
3. **Exclude patterns**: If a track matches an exclude pattern (e.g. `Japanese`, `日本語`), it is not selected even if it matched language or name.

The first audio track that qualifies as “English” (by language or name, and not excluded) is chosen. The first subtitle track that is both “English” (by language, with optional name/exclude checks) and matches the Signs/Songs name patterns is chosen. The app also records the **first audio track** in the file; when **Allow Japanese audio with English subs** is enabled in Settings and no English audio is found, that first audio track is used so you can encode with Japanese audio and English subtitles.

## The six pattern groups

All are configured in the **Settings** tab under Track Detection:

| Group | Purpose |
|-------|---------|
| **Audio Language Tags** | Language codes to treat as English audio (e.g. `en`, `eng`). |
| **Audio Name Patterns** | Regex patterns matched against audio track names (e.g. `English`, `ENG`). |
| **Audio Exclude Patterns** | Regex patterns that disqualify an audio track (e.g. `Japanese`, `日本語`). |
| **Subtitle Language Tags** | Language codes to treat as English (or acceptable) for subtitle selection (e.g. `en`, `eng`). |
| **Subtitle Name Patterns** | Regex patterns for “Signs & Songs”–style track names (e.g. `Signs.*Songs`, `Signs$`, `English Signs`). |
| **Subtitle Exclude Patterns** | Regex patterns that disqualify a subtitle track (e.g. `Japanese`, `JPN`). |

Patterns are comma-separated. Name and exclude patterns are regex; use `.*` for “any characters” and `$` for “end of string”.

## Default patterns

Out of the box, the app uses patterns like these (you can change them in Settings):

- **Audio**: Language tags `en`, `eng`; name patterns `English`, `ENG`; exclude `Japanese`, `JPN`, `日本語`.
- **Subtitle**: Language tags `en`, `eng`; name patterns such as `Signs.*Songs`, `Signs.*Song`, `Signs$`, `English Signs`, `^Signs\s*$`; exclude `Japanese`, `JPN`, `日本語`.

> **Note:** Some documentation mentions using `*` as a subtitle language tag to “match any language.” If your version supports that, it would allow selecting a Signs/Songs subtitle regardless of language tag. Verify in Settings or the source if you need that behavior.

## Using the Debug tab to troubleshoot

If the wrong track is selected (or none), use the **Debug** tab:

1. Click **Browse** and select the problematic MKV file.
2. Click **Analyze**.
3. Open **mkvinfo Output** to see the raw track list (language, name, type).
4. Open **Track Analysis** to see which audio and subtitle tracks were chosen and why, and what your current detection settings are.

From that you can adjust language tags, name patterns, or exclude patterns in Settings so the right track is selected. For example, if your files use “ENG” in the track name instead of “English,” add `ENG` to the audio name patterns.

## Common scenarios

### Anime with Japanese audio + English dub + Signs track

- **English dub**: Ensure “English” (or your release’s naming) is matched by audio language tags or name patterns; exclude patterns should not match the English track.
- **Signs & Songs only**: Subtitle name patterns should match the track name (e.g. “Signs & Songs,” “Signs and Songs”). Subtitle language tags can be `en`, `eng`, or whatever your files use.
- **Japanese audio + English subs**: Enable **Allow Japanese audio with English subs** in Settings. When no English audio is found, the app uses the first audio track (typically Japanese) and can still burn the selected English Signs/Songs subtitle.

### Multiple English subtitle tracks

The app selects the **first** subtitle track (by track ID) that matches both the subtitle language and the Signs/Songs name patterns. If you have “English (full)” and “English (Signs & Songs),” the name patterns should match only the Signs & Songs one so it is chosen. Adjust subtitle name patterns so they do not match the full dialogue track.
