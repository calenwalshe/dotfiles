"""FFmpeg-based video compositor for multi-webcam grid layouts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class GridLayout:
    rows: int
    cols: int
    width: int
    height: int

    @property
    def cell_width(self) -> int:
        return self.width // self.cols

    @property
    def cell_height(self) -> int:
        return self.height // self.rows

    @property
    def total_cells(self) -> int:
        return self.rows * self.cols

    def xstack_layout(self) -> str:
        """Generate the xstack layout string for FFmpeg.

        Format: positions separated by |, where each position is x_y.
        Uses symbolic references: w0, h0, etc. for cell dimensions.
        """
        positions = []
        for r in range(self.rows):
            for c in range(self.cols):
                x = f"w0*{c}" if c > 0 else "0"
                y = f"h0*{r}" if r > 0 else "0"
                # Simplify "0" cases
                if c == 0 and r == 0:
                    positions.append("0_0")
                elif c == 0:
                    positions.append(f"0_h0*{r}" if r > 1 else "0_h0")
                elif r == 0:
                    positions.append(f"w0*{c}_0" if c > 1 else "w0_0")
                else:
                    positions.append(f"w0*{c}_h0*{r}" if c > 1 or r > 1 else "w0_h0")
        return "|".join(positions)


class FFmpegCompositor:
    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height

    def build_command(
        self,
        sources: list[str],
        layout: GridLayout,
        rtmp_url: str,
        audio_source: Optional[str] = None,
    ) -> list[str]:
        if len(sources) < layout.total_cells:
            raise ValueError(
                f"Need {layout.total_cells} sources for {layout.rows}x{layout.cols} grid, "
                f"got {len(sources)}"
            )

        cmd = ["ffmpeg"]

        # Input sources (video feeds)
        for src in sources[: layout.total_cells]:
            cmd.extend(["-i", src])

        # Audio input if provided
        audio_index = None
        if audio_source:
            audio_index = layout.total_cells
            cmd.extend(["-i", audio_source])

        # Build filter_complex: scale each input then xstack
        filters = []
        for i in range(layout.total_cells):
            filters.append(
                f"[{i}:v]scale={layout.cell_width}:{layout.cell_height},"
                f"setsar=1[v{i}]"
            )

        # xstack
        inputs_str = "".join(f"[v{i}]" for i in range(layout.total_cells))
        xstack_layout = layout.xstack_layout()
        filters.append(
            f"{inputs_str}xstack=inputs={layout.total_cells}:"
            f"layout={xstack_layout}[vout]"
        )

        cmd.extend(["-filter_complex", ";".join(filters)])

        # Output mapping
        cmd.extend(["-map", "[vout]"])
        if audio_index is not None:
            cmd.extend(["-map", f"{audio_index}:a"])

        # Encoding settings for YouTube RTMP
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-b:v", "4500k",
            "-maxrate", "4500k",
            "-bufsize", "9000k",
            "-g", "60",
            "-keyint_min", "60",
        ])

        if audio_source:
            cmd.extend(["-c:a", "aac", "-b:a", "128k", "-ar", "44100"])

        cmd.extend(["-f", "flv", rtmp_url])

        return cmd

    def build_test_command(
        self,
        sources: list[str],
        layout: GridLayout,
        output_file: str,
        duration: int = 10,
    ) -> list[str]:
        """Build command for local testing (file output instead of RTMP)."""
        if len(sources) < layout.total_cells:
            raise ValueError(
                f"Need {layout.total_cells} sources for {layout.rows}x{layout.cols} grid, "
                f"got {len(sources)}"
            )

        cmd = ["ffmpeg", "-y"]

        for src in sources[: layout.total_cells]:
            cmd.extend(["-i", src])

        filters = []
        for i in range(layout.total_cells):
            filters.append(
                f"[{i}:v]scale={layout.cell_width}:{layout.cell_height},"
                f"setsar=1[v{i}]"
            )

        inputs_str = "".join(f"[v{i}]" for i in range(layout.total_cells))
        xstack_layout = layout.xstack_layout()
        filters.append(
            f"{inputs_str}xstack=inputs={layout.total_cells}:"
            f"layout={xstack_layout}[vout]"
        )

        cmd.extend(["-filter_complex", ";".join(filters)])
        cmd.extend(["-map", "[vout]"])
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-t", str(duration),
            output_file,
        ])

        return cmd
