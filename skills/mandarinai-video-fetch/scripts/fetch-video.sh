#!/bin/bash
# Fetch a video's transcript: try platform subtitles first, fall back to
# downloading audio for local transcription.
#
# Usage: fetch-video.sh [-o OUTDIR] [-l SUB_LANGS] [-c BROWSER] URL
#   -o OUTDIR    output directory (default /tmp/video-fetch)
#   -l SUB_LANGS yt-dlp --sub-langs value (default "zh.*,zh-Hans,zh-CN,en.*,en")
#   -c BROWSER   pass cookies from a browser (chrome/safari/firefox);
#                needed for bilibili AI subs, xiaohongshu, members-only videos
#
# Prints one final line:  TRANSCRIPT: <path>   (subtitles found / transcribed)
#                    or:  AUDIO: <path>        (no subs, no transcriber available)
#
# Transcription priority for no-subtitle videos:
#   1. WHISPER_BASE_URL env -> remote whisper server (whisper_server.py API:
#      POST /transcribe multipart, poll GET /status/{job_id}); WHISPER_API_KEY
#      adds Bearer auth
#   2. local mlx_whisper, then local whisper
set -e

OUTDIR="/tmp/video-fetch"
LANGS="zh.*,zh-Hans,zh-CN,en.*,en"
COOKIES=()

while getopts "o:l:c:h" opt; do
    case $opt in
        o) OUTDIR="$OPTARG" ;;
        l) LANGS="$OPTARG" ;;
        c) COOKIES=(--cookies-from-browser "$OPTARG") ;;
        *) grep '^#' "$0" | head -12; exit 1 ;;
    esac
done
shift $((OPTIND-1))
URL="$1"
[ -n "$URL" ] || { echo "Error: no URL given" >&2; exit 1; }
command -v yt-dlp >/dev/null || { echo "Error: yt-dlp required (brew install yt-dlp)" >&2; exit 1; }

mkdir -p "$OUTDIR"

# Expand xiaohongshu/short share links to their final URL
case "$URL" in
    *xhslink.com*|*b23.tv*|*youtu.be*)
        URL=$(curl -sIL -o /dev/null -w '%{url_effective}' "$URL" || echo "$URL") ;;
esac

META=$(yt-dlp --no-playlist "${COOKIES[@]}" --print "%(id)s|%(title)s" "$URL" 2>/dev/null | head -1) || true
if [ -z "$META" ]; then
    echo "Error: could not read video metadata. If this is bilibili/xiaohongshu, retry with -c chrome (login cookies)." >&2
    exit 1
fi
ID="${META%%|*}"
TITLE="${META#*|}"
echo "video: $TITLE ($ID)" >&2

clean_subs() {  # vtt/srt -> ordered, deduped plain text
    sed -e 's/<[^>]*>//g' "$1" | awk '
        /^WEBVTT/ || /^Kind:/ || /^Language:/ || /-->/ || /^[0-9]+$/ || /^[[:space:]]*$/ { next }
        !seen[$0]++ { print }
    '
}

# 1) Try platform subtitles (manual + auto-generated)
yt-dlp --no-playlist "${COOKIES[@]}" --skip-download \
    --write-subs --write-auto-subs --sub-langs "$LANGS" \
    -o "$OUTDIR/${ID}.%(ext)s" "$URL" >/dev/null 2>&1 || true
SUB=$(ls -S "$OUTDIR/${ID}".*.vtt "$OUTDIR/${ID}".*.srt 2>/dev/null | head -1)
if [ -n "$SUB" ] && [ -s "$SUB" ]; then
    TXT="$OUTDIR/${ID}.txt"
    clean_subs "$SUB" > "$TXT"
    if [ -s "$TXT" ]; then
        echo "TRANSCRIPT: $TXT"
        exit 0
    fi
fi
echo "no subtitles available, downloading audio..." >&2

# 2) Fall back to audio + local transcription
yt-dlp --no-playlist "${COOKIES[@]}" -f "bestaudio/best" -x --audio-format m4a \
    -o "$OUTDIR/${ID}.%(ext)s" "$URL" >/dev/null 2>&1
AUDIO="$OUTDIR/${ID}.m4a"
[ -s "$AUDIO" ] || { echo "Error: audio download failed" >&2; exit 1; }

TXT="$OUTDIR/${ID}.txt"

transcribe_remote() {  # whisper server: POST /transcribe -> poll /status/{job_id}
    local base="${WHISPER_BASE_URL%/}" auth=() job st waited=0
    [ -n "$WHISPER_API_KEY" ] && auth=(-H "Authorization: Bearer $WHISPER_API_KEY")
    echo "transcribing via whisper server $base ..." >&2
    job=$(curl -sf "${auth[@]}" -F "file=@$AUDIO" "$base/transcribe" \
          | python3 -c 'import sys,json; print(json.load(sys.stdin)["job_id"])') || return 1
    while [ $waited -lt 1800 ]; do
        sleep 5; waited=$((waited+5))
        st=$(curl -sf "${auth[@]}" "$base/status/$job") || return 1
        case $(printf '%s' "$st" | python3 -c 'import sys,json; print(json.load(sys.stdin)["status"])') in
            done)
                printf '%s' "$st" | python3 -c 'import sys,json
for s in json.load(sys.stdin)["segments"]: print(s["text"])' > "$TXT"
                [ -s "$TXT" ] && return 0 || return 1 ;;
            error)
                printf '%s' "$st" | python3 -c 'import sys,json; print("server error:", json.load(sys.stdin).get("error"))' >&2
                return 1 ;;
        esac
    done
    echo "remote transcription timed out (30 min)" >&2
    return 1
}

if [ -n "$WHISPER_BASE_URL" ] && transcribe_remote; then
    echo "TRANSCRIPT: $TXT"
elif command -v mlx_whisper >/dev/null; then
    mlx_whisper "$AUDIO" --output-dir "$OUTDIR" --output-name "$ID" --output-format txt >&2
    echo "TRANSCRIPT: $TXT"
elif command -v whisper >/dev/null; then
    whisper "$AUDIO" --output_dir "$OUTDIR" --output_format txt >&2
    echo "TRANSCRIPT: $TXT"
else
    echo "AUDIO: $AUDIO"
    echo "No transcriber available. Set WHISPER_BASE_URL (+ WHISPER_API_KEY) for a remote whisper server, or: pip install mlx-whisper" >&2
fi
