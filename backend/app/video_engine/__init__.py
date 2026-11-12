"""AETHER video engine package.

Scene-based AI video generation engine per build.txt section 7.

Architecture:
  1. Understand the user's video idea (script generation via model chat)
  2. Divide the script into scenes with estimated durations
  3. Generate individual clips using available video providers
  4. Continue/extend clips when supported
  5. Generate narration and audio when available
  6. Assemble all clips with FFmpeg (transitions, sync, render)
  7. Export the final video

All runs as resumable background jobs tracked in SQLite so they survive
UI disconnections. Long durations are handled by combining multiple clips.
"""
from .service import VideoService, VideoError

__all__ = ["VideoService", "VideoError"]
