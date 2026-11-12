"""AETHER video editor package.

Phase 6: Automatic video editor with timeline, transitions, subtitles, audio sync.

Features:
- Multi-track timeline (video, audio, subtitle tracks)
- Clip trimming, positioning, transitions
- Subtitle/caption support with styling
- Multi-track audio mixing with volume, fade
- Color grading and effects per clip
- Automatic editing modes (AI-assisted)
- FFmpeg-based rendering with export presets
"""
from .service import VideoEditorService, VideoEditorError

__all__ = ["VideoEditorService", "VideoEditorError"]