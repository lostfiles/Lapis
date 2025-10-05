"""
Diagnostic formatting and reporting for the Lapis Programming Language
Provides pretty-printed error messages with code frames and ANSI colors
"""

import sys
import os
from typing import Optional, List, Dict, TextIO
from dataclasses import dataclass
from enum import Enum

from errors import Diagnostic, LabeledSpan, Severity
from source_map import get_source_map, Span, SourceFile, Position

class ColorMode(Enum):
    """Color output modes"""
    NEVER = "never"
    ALWAYS = "always" 
    AUTO = "auto"

class DiagnosticFormatter:
    """Formats diagnostics for human-readable output"""
    
    def __init__(self, color_mode: ColorMode = ColorMode.AUTO, max_errors: int = 20):
        self.color_mode = color_mode
        self.max_errors = max_errors
        self.error_count = 0
        self.warning_count = 0
        
        # ANSI color codes
        self.colors = {
            'reset': '\033[0m',
            'bold': '\033[1m',
            'red': '\033[31m',
            'yellow': '\033[33m',
            'blue': '\033[34m',
            'cyan': '\033[36m',
            'white': '\033[37m',
            'bright_red': '\033[91m',
            'bright_yellow': '\033[93m',
            'bright_blue': '\033[94m',
            'bright_cyan': '\033[96m',
        }
    
    def should_use_colors(self, file: TextIO = sys.stderr) -> bool:
        """Determine if we should use ANSI colors"""
        if self.color_mode == ColorMode.NEVER:
            return False
        elif self.color_mode == ColorMode.ALWAYS:
            return True
        else:  # AUTO
            return file.isatty() and os.getenv('NO_COLOR') is None
    
    def colorize(self, text: str, color: str, file: TextIO = sys.stderr) -> str:
        """Apply color to text if colors are enabled"""
        if not self.should_use_colors(file):
            return text
        return f"{self.colors.get(color, '')}{text}{self.colors['reset']}"
    
    def format_diagnostic(self, diagnostic: Diagnostic, file: TextIO = sys.stderr) -> str:
        """Format a single diagnostic with code frame"""
        output_lines = []
        source_map = get_source_map()
        
        # Update counts
        if diagnostic.severity == Severity.ERROR:
            self.error_count += 1
        elif diagnostic.severity == Severity.WARNING:
            self.warning_count += 1
        
        # Check max errors limit
        if self.error_count > self.max_errors:
            return self.colorize("... (too many errors, stopping)\n", 'red', file)
        
        try:
            # Get primary span for header
            primary_span = diagnostic.primary_span()
            if not primary_span:
                # No span - simple message
                severity_color = self._get_severity_color(diagnostic.severity)
                header = f"{diagnostic.severity.value.title()} [{diagnostic.code}]: {diagnostic.message}"
                output_lines.append(self.colorize(header, severity_color, file))
            else:
                # Format with file location
                source_file, start_pos, end_pos = source_map.resolve_span(primary_span)
                output_lines.extend(self._format_diagnostic_with_span(
                    diagnostic, source_file, start_pos, end_pos, file
                ))
            
            # Add help if present
            if diagnostic.help:
                help_line = f"   = help: {diagnostic.help}"
                output_lines.append(self.colorize(help_line, 'cyan', file))
            
            # Add notes
            for note in diagnostic.notes:
                note_line = f"   = note: {note}"
                output_lines.append(self.colorize(note_line, 'blue', file))
            
            output_lines.append("")  # Empty line after diagnostic
            
        except Exception as e:
            # Fallback for span resolution errors
            severity_color = self._get_severity_color(diagnostic.severity)
            fallback = f"{diagnostic.severity.value.title()} [{diagnostic.code}]: {diagnostic.message} (span resolution failed: {e})"
            output_lines.append(self.colorize(fallback, severity_color, file))
            output_lines.append("")
        
        return "\n".join(output_lines)
    
    def _format_diagnostic_with_span(self, diagnostic: Diagnostic, source_file: SourceFile, 
                                   start_pos: Position, end_pos: Position, file: TextIO) -> List[str]:
        """Format diagnostic with code frame and spans"""
        lines = []
        severity_color = self._get_severity_color(diagnostic.severity)
        
        # Header: ErrorType [CODE]: message
        header = f"{diagnostic.severity.value.title()} [{diagnostic.code}]: {diagnostic.message}"
        lines.append(self.colorize(header, severity_color, file))
        
        # File location: --> path:line:column
        file_name = os.path.relpath(source_file.path) if os.path.exists(source_file.path) else source_file.path
        location = f"  --> {file_name}:{start_pos.line}:{start_pos.column}"
        lines.append(self.colorize(location, 'bright_blue', file))
        lines.append(self.colorize("   |", 'bright_blue', file))
        
        # Code frame with labels
        lines.extend(self._format_code_frame(diagnostic, source_file, file))
        
        return lines
    
    def _format_code_frame(self, diagnostic: Diagnostic, source_file: SourceFile, file: TextIO) -> List[str]:
        """Format the code frame with line numbers and labels"""
        lines = []
        source_map = get_source_map()
        
        # Collect all spans and their line ranges
        span_info = []
        for label in diagnostic.labels:
            try:
                _, start_pos, end_pos = source_map.resolve_span(label.span)
                span_info.append((label, start_pos, end_pos))
            except:
                continue
        
        if not span_info:
            return lines
        
        # Determine line range to show
        all_lines = [info[1].line for info in span_info] + [info[2].line for info in span_info]
        min_line = max(1, min(all_lines) - 1)
        max_line = min(len(source_file.line_starts), max(all_lines) + 1)
        
        # Calculate gutter width
        gutter_width = len(str(max_line))
        
        # Show lines
        for line_num in range(min_line, max_line + 1):
            try:
                line_content = source_file.get_line(line_num)
                
                # Check if this line has any spans
                line_labels = []
                for label, start_pos, end_pos in span_info:
                    if start_pos.line <= line_num <= end_pos.line:
                        line_labels.append((label, start_pos, end_pos))
                
                # Format line number and content
                gutter = f"{line_num:>{gutter_width}}"
                if line_labels:
                    # Line with spans - show with highlighting
                    lines.append(self._format_line_with_spans(
                        gutter, line_content, line_labels, line_num, gutter_width, file
                    ))
                else:
                    # Regular line
                    line_display = f"{self.colorize(gutter, 'bright_blue', file)} {self.colorize('|', 'bright_blue', file)} {line_content}"
                    lines.append(line_display)
                    
            except ValueError:
                # Line out of bounds
                continue
        
        return lines
    
    def _format_line_with_spans(self, gutter: str, line_content: str, line_labels: List, 
                              line_num: int, gutter_width: int, file: TextIO) -> str:
        """Format a line that contains labeled spans"""
        output_lines = []
        
        # Show the line itself
        gutter_colored = self.colorize(gutter, 'bright_blue', file)
        pipe_colored = self.colorize('|', 'bright_blue', file)
        line_display = f"{gutter_colored} {pipe_colored} {line_content}"
        output_lines.append(line_display)
        
        # Create underlines and labels
        underline_chars = [' '] * len(line_content)
        label_positions = []
        
        for label, start_pos, end_pos in line_labels:
            if start_pos.line == line_num:
                # Calculate span within this line
                start_col = max(0, start_pos.column - 1)  # Convert to 0-indexed
                if end_pos.line == line_num:
                    end_col = min(len(line_content), end_pos.column - 1)
                else:
                    end_col = len(line_content)
                
                # Determine underline character
                underline_char = '^' if label.is_primary else '-'
                
                # Fill underline
                for i in range(start_col, max(start_col + 1, end_col)):
                    if i < len(underline_chars):
                        underline_chars[i] = underline_char
                
                # Store label position
                if label.label:
                    label_positions.append((start_col, label.label, label.is_primary))
        
        # Show underline
        if any(c != ' ' for c in underline_chars):
            underline = ''.join(underline_chars).rstrip()
            gutter_spaces = ' ' * gutter_width
            pipe_colored = self.colorize('|', 'bright_blue', file)
            
            # Color the underline
            colored_underline = self._colorize_underline(underline, file)
            underline_display = f"{gutter_spaces} {pipe_colored} {colored_underline}"
            output_lines.append(underline_display)
            
            # Show labels
            for col, label_text, is_primary in label_positions:
                if label_text:
                    label_line = ' ' * (gutter_width + 3 + col)  # Position at column
                    label_color = 'bright_red' if is_primary else 'bright_yellow'
                    label_display = label_line + self.colorize(label_text, label_color, file)
                    output_lines.append(label_display)
        
        return '\n'.join(output_lines)
    
    def _colorize_underline(self, underline: str, file: TextIO) -> str:
        """Color underline characters appropriately"""
        result = []
        for char in underline:
            if char == '^':
                result.append(self.colorize(char, 'bright_red', file))
            elif char == '-':
                result.append(self.colorize(char, 'bright_yellow', file))
            else:
                result.append(char)
        return ''.join(result)
    
    def _get_severity_color(self, severity: Severity) -> str:
        """Get color for severity level"""
        color_map = {
            Severity.ERROR: 'bright_red',
            Severity.WARNING: 'bright_yellow',
            Severity.NOTE: 'bright_blue',
            Severity.HELP: 'bright_cyan'
        }
        return color_map.get(severity, 'white')
    
    def emit_diagnostic(self, diagnostic: Diagnostic, file: TextIO = sys.stderr):
        """Emit a diagnostic to the given file"""
        formatted = self.format_diagnostic(diagnostic, file)
        file.write(formatted)
        file.flush()
    
    def print_summary(self, file: TextIO = sys.stderr):
        """Print error/warning summary"""
        if self.error_count == 0 and self.warning_count == 0:
            return
        
        parts = []
        if self.error_count > 0:
            error_text = f"{self.error_count} error{'s' if self.error_count != 1 else ''}"
            parts.append(self.colorize(error_text, 'bright_red', file))
        
        if self.warning_count > 0:
            warning_text = f"{self.warning_count} warning{'s' if self.warning_count != 1 else ''}"
            parts.append(self.colorize(warning_text, 'bright_yellow', file))
        
        summary = ", ".join(parts) + " generated"
        file.write(f"\n{summary}\n")
        file.flush()

# Global formatter instance
_formatter = DiagnosticFormatter()

def get_formatter() -> DiagnosticFormatter:
    """Get the global diagnostic formatter"""
    return _formatter

def emit_diagnostic(diagnostic: Diagnostic):
    """Emit a diagnostic using the global formatter"""
    _formatter.emit_diagnostic(diagnostic)

def set_color_mode(mode: ColorMode):
    """Set the global color mode"""
    _formatter.color_mode = mode

def set_max_errors(max_errors: int):
    """Set the maximum number of errors to show"""
    _formatter.max_errors = max_errors