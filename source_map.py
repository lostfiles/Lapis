"""
Source mapping system for the Lapis Programming Language
Tracks file positions and provides span-to-line/column resolution
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import os

@dataclass
class Span:
    """Represents a source code span with start and end positions"""
    file_id: int
    start: int  # byte offset (inclusive)
    end: int    # byte offset (exclusive)
    
    def __post_init__(self):
        if self.start > self.end:
            raise ValueError(f"Invalid span: start ({self.start}) > end ({self.end})")
    
    def length(self) -> int:
        return self.end - self.start
    
    def contains(self, offset: int) -> bool:
        return self.start <= offset < self.end
    
    def overlaps(self, other: 'Span') -> bool:
        return (self.file_id == other.file_id and 
                self.start < other.end and other.start < self.end)

@dataclass
class Position:
    """Line/column position in source file (1-indexed)"""
    line: int
    column: int
    
    def __str__(self) -> str:
        return f"{self.line}:{self.column}"

@dataclass  
class SourceFile:
    """Represents a source file with its content and line index"""
    file_id: int
    path: str
    content: str
    line_starts: List[int]  # Byte offset of each line start
    
    def __init__(self, file_id: int, path: str, content: str):
        self.file_id = file_id
        self.path = path
        self.content = content
        self.line_starts = self._compute_line_starts()
    
    def _compute_line_starts(self) -> List[int]:
        """Compute byte offsets for each line start"""
        line_starts = [0]  # First line starts at 0
        for i, char in enumerate(self.content):
            if char == '\n':
                line_starts.append(i + 1)
        return line_starts
    
    def offset_to_position(self, offset: int) -> Position:
        """Convert byte offset to line/column position"""
        if offset < 0 or offset > len(self.content):
            raise ValueError(f"Offset {offset} out of bounds for file {self.path}")
        
        # Binary search for the line
        line_num = 1
        for i, line_start in enumerate(self.line_starts):
            if line_start > offset:
                line_num = i
                break
        else:
            line_num = len(self.line_starts)
        
        line_start = self.line_starts[line_num - 1]
        column = offset - line_start + 1
        
        return Position(line_num, column)
    
    def span_to_positions(self, span: Span) -> Tuple[Position, Position]:
        """Convert span to start and end positions"""
        if span.file_id != self.file_id:
            raise ValueError(f"Span file_id {span.file_id} doesn't match file {self.file_id}")
        
        start_pos = self.offset_to_position(span.start)
        end_pos = self.offset_to_position(max(span.start, span.end - 1))  # end is exclusive
        
        return start_pos, end_pos
    
    def get_line(self, line_num: int) -> str:
        """Get the content of a specific line (1-indexed)"""
        if line_num < 1 or line_num > len(self.line_starts):
            raise ValueError(f"Line {line_num} out of bounds")
        
        start = self.line_starts[line_num - 1]
        if line_num < len(self.line_starts):
            end = self.line_starts[line_num] - 1  # Exclude the newline
        else:
            end = len(self.content)
        
        return self.content[start:end]
    
    def get_span_text(self, span: Span) -> str:
        """Get the text content of a span"""
        if span.file_id != self.file_id:
            raise ValueError(f"Span file_id {span.file_id} doesn't match file {self.file_id}")
        
        return self.content[span.start:span.end]

class SourceMap:
    """Manages multiple source files and provides unified span resolution"""
    
    def __init__(self):
        self.files: Dict[int, SourceFile] = {}
        self.path_to_id: Dict[str, int] = {}
        self.next_id = 1
    
    def add_file(self, path: str, content: str) -> int:
        """Add a source file and return its ID"""
        abs_path = os.path.abspath(path)
        
        if abs_path in self.path_to_id:
            return self.path_to_id[abs_path]
        
        file_id = self.next_id
        self.next_id += 1
        
        source_file = SourceFile(file_id, abs_path, content)
        self.files[file_id] = source_file
        self.path_to_id[abs_path] = file_id
        
        return file_id
    
    def get_file(self, file_id: int) -> Optional[SourceFile]:
        """Get source file by ID"""
        return self.files.get(file_id)
    
    def resolve_span(self, span: Span) -> Tuple[SourceFile, Position, Position]:
        """Resolve a span to file and positions"""
        source_file = self.get_file(span.file_id)
        if not source_file:
            raise ValueError(f"Unknown file ID: {span.file_id}")
        
        start_pos, end_pos = source_file.span_to_positions(span)
        return source_file, start_pos, end_pos
    
    def get_span_text(self, span: Span) -> str:
        """Get the text content of a span"""
        source_file = self.get_file(span.file_id)
        if not source_file:
            raise ValueError(f"Unknown file ID: {span.file_id}")
        
        return source_file.get_span_text(span)
    
    def create_span(self, file_id: int, start: int, end: int) -> Span:
        """Create a span with validation"""
        if file_id not in self.files:
            raise ValueError(f"Unknown file ID: {file_id}")
        
        source_file = self.files[file_id]
        if start < 0 or end > len(source_file.content):
            raise ValueError(f"Span ({start}, {end}) out of bounds for file")
        
        return Span(file_id, start, end)

# Global source map instance
_source_map = SourceMap()

def get_source_map() -> SourceMap:
    """Get the global source map instance"""
    return _source_map

def reset_source_map():
    """Reset the global source map (useful for testing)"""
    global _source_map
    _source_map = SourceMap()