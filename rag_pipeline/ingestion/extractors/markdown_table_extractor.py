from ...core.models import Document, ContentType, Chunk
from ..interfaces import BaseExtractor, BaseFilter
from typing import List, Tuple, Optional, Union
import re


class MarkdownTableExtractor(BaseExtractor):
    TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
    SEPARATOR_CELL_RE = re.compile(r"^\s*:?-{3,}:?\s*$")

    def __init__(self, filters: List[BaseFilter] = None):
        super().__init__(filters=filters)

    def extract(self, doc: Union[Document, Chunk]) -> Tuple[List[Chunk], Optional[Union[Document, Chunk]]]:
        lines = doc.page_content.splitlines()
        extracted_chunks: List[Chunk] = []
        remaining_lines: List[str] = []
        i = 0
        while i < len(lines):
            table_result = self._parse_table_at(lines, i)

            if table_result is None:
                remaining_lines.append(lines[i])
                i += 1
                continue

            header, separator, data_rows, next_index = table_result

            for row_idx, row in enumerate(data_rows, start=1):
                mini_table = f"{header}\n{separator}\n{row}"

                new_metadata = doc.metadata.pipeline_step(component_type=self._type,
                                                          component_name=self.name,
                                                          description=f"Table Row {row_idx}").copy(content=ContentType.TABLE)

                extracted_chunks.append(Chunk(page_content=mini_table,
                                              metadata=new_metadata,
                                              source_id=doc.source_id))
            i = next_index
        remaining_text = "\n".join(remaining_lines).strip()
        if not remaining_text:
            return extracted_chunks, None

        new_metadata = doc.metadata.pipeline_step(component_type=self._type,
                                                  component_name=self.name,
                                                  description="Extract tables and save them as new document").copy(content=ContentType.CHUNK)
        return self._apply_filters(extracted_chunks), self._create_doc(doc, remaining_text, new_metadata)

    def _parse_table_at(self, lines: List[str], start_idx: int) -> Optional[Tuple[str, str, List[str], int]]:
        if start_idx + 1 >= len(lines):
            return None

        first = lines[start_idx]
        second = lines[start_idx + 1]

        if not self._is_table_row(first):
            return None

        if self._is_separator_row(first):
            return None

        if not self._is_separator_row(second):
            return None

        # 1) Consume the whole contiguous table block first
        idx = start_idx
        block: List[str] = []
        while idx < len(lines) and self._is_table_row(lines[idx]):
            block.append(lines[idx])
            idx += 1

        if len(block) < 3:
            return None

        # 2) Determine canonical column count
        non_separator_rows = [row for row in block if not self._is_separator_row(row)]
        if not non_separator_rows:
            return None

        expected_col_count = max(len(self._split_cells(row)) for row in non_separator_rows)

        # 3) Detect the real header
        #    Standard markdown: first row is already the header
        #    Weird wiki tables: first row may be empty / placeholder, so search deeper
        first_cells = self._split_cells(block[0])
        if len(first_cells) == expected_col_count and self._count_non_empty(first_cells) >= 2:
            header_idx = 0
        else:
            header_idx = None
            for j in range(2, len(block)):
                cells = self._split_cells(block[j])
                if len(cells) == expected_col_count and self._count_non_empty(cells) >= 2:
                    header_idx = j
                    break

            if header_idx is None:
                return None

        header = self._join_cells(self._normalize_cells(self._split_cells(block[header_idx]), expected_col_count))
        separator = self._build_separator_row(expected_col_count)

        # 4) Collect and normalize data rows
        data_rows: List[str] = []
        for row in block[header_idx + 1:]:
            if self._is_separator_row(row):
                continue

            cells = self._split_cells(row)
            if not any(cells):
                continue

            # Skip section/title rows like:
            # | **Eagles Hall of Fame** | | | | |
            # | 1948 NFL Championship team | | | |
            if self._is_section_row(cells):
                continue

            normalized = self._normalize_cells(cells, expected_col_count)
            if normalized is None:
                continue

            if not all(cell == "" for cell in normalized):
                data_rows.append(self._join_cells(normalized))

        if not data_rows:
            return None

        return header, separator, data_rows, idx

    def _normalize_cells(self, cells: List[str], expected_col_count: int) -> Optional[List[str]]:
        if len(cells) == expected_col_count:
            return cells

        if len(cells) > expected_col_count:
            return None

        missing = expected_col_count - len(cells)
        non_empty_count = self._count_non_empty(cells)

        # Rows with exactly one non-empty cell are usually title/section rows.
        # Keep structure stable by padding right if needed.
        if non_empty_count <= 1:
            return cells + ([""] * missing)

        # In this dataset, shortened rows usually miss the left-most grouping column,
        # e.g. Year is omitted for repeated entries.
        return ([""] * missing) + cells

    def _is_table_row(self, line: str) -> bool:
        return bool(self.TABLE_ROW_RE.match(line))

    def _is_empty_row(self, line: str) -> bool:
        return all(cell == "" for cell in self._split_cells(line))

    def _is_separator_row(self, line: str) -> bool:
        cells = self._split_cells(line)
        if len(cells) < 2:
            return False

        return all(self.SEPARATOR_CELL_RE.match(cell) for cell in cells)

    @staticmethod
    def _split_cells(line: str) -> List[str]:
        stripped = line.strip()

        if stripped.startswith("|"):
            stripped = stripped[1:]
        if stripped.endswith("|"):
            stripped = stripped[:-1]

        return [cell.strip() for cell in stripped.split("|")]

    @staticmethod
    def _join_cells(cells: List[str]) -> str:
        return "| " + " | ".join(cells) + " |"

    @staticmethod
    def _build_separator_row(col_count: int) -> str:
        return "| " + " | ".join(["---"] * col_count) + " |"

    @staticmethod
    def _count_non_empty(cells: List[str]) -> int:
        return sum(1 for cell in cells if cell.strip())

    @staticmethod
    def _is_section_row(cells: List[str]) -> bool:
        non_empty = [cell for cell in cells if cell.strip()]
        return len(non_empty) == 1