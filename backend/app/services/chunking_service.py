import re
import statistics
from typing import List, Dict, Any, Optional, Tuple
from app.core.config import settings
from app.utils.hashing import compute_text_hash
from app.services.tokenizer_service import TokenizerService


class ChunkData:
    def __init__(
        self,
        chunk_index: int,
        content: str,
        token_count: int,
        character_start: int,
        character_end: int,
        source_location: Dict[str, Any],
        heading_path: List[str],
        content_hash: str,
        split_reason: str = "target_size_limit",
        token_count_model: str = TokenizerService.TOKENIZER_NAME,
        overlap_tokens: int = 0
    ):
        self.chunk_index = chunk_index
        self.content = content
        self.token_count = token_count
        self.character_start = character_start
        self.character_end = character_end
        self.source_location = source_location
        self.heading_path = heading_path
        self.content_hash = content_hash
        self.split_reason = split_reason
        self.token_count_model = token_count_model
        self.overlap_tokens = overlap_tokens


class ChunkingService:
    MAX_CHUNK_TOKENS: int = TokenizerService.EFFECTIVE_MAX_TOKENS  # 510

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Counts real tokens using the official model tokenizer."""
        return TokenizerService.count_tokens(text)

    @classmethod
    def chunk_document(
        cls,
        raw_text: str,
        file_extension: str,
        pages: Optional[List[Dict[str, Any]]] = None,
        headings: Optional[List[Dict[str, Any]]] = None,
        target_tokens: Optional[int] = None,
        overlap_tokens: Optional[int] = None,
        enforce_limit: bool = True
    ) -> List[ChunkData]:
        if not raw_text or not raw_text.strip():
            return []

        target = target_tokens or settings.TARGET_CHUNK_TOKENS
        overlap = overlap_tokens if overlap_tokens is not None else settings.CHUNK_OVERLAP_TOKENS

        ext = file_extension.lower().lstrip(".")

        if ext == "pdf" and pages and len(pages) > 0:
            chunks = cls._chunk_pdf(raw_text, pages, target, overlap)
        elif ext == "md":
            chunks = cls._chunk_markdown(raw_text, target, overlap)
        else:
            chunks = cls._chunk_text(raw_text, target, overlap)

        if enforce_limit:
            return cls._enforce_embedding_limits(chunks, raw_text, max_tokens=cls.MAX_CHUNK_TOKENS)
        return chunks

    @classmethod
    def _split_into_structural_blocks(cls, text: str) -> List[Dict[str, Any]]:
        """
        Splits text into structural atomic blocks:
        - Paragraphs separated by \n\n
        - If text has single newlines with list bullets or role titles, preserves boundaries.
        Returns list of dicts: {'text': str, 'start': int, 'end': int, 'type': str}
        """
        blocks = []
        # Find paragraphs separated by 2+ newlines
        pos = 0
        para_pattern = re.compile(r"\n{2,}")
        splits = list(para_pattern.finditer(text))

        if not splits:
            # Single block or line-based text
            # Check if lines look like list items or sections
            lines = text.split("\n")
            if len(lines) > 5 and any(re.match(r"^\s*([•\-\*]|\d+\.|\b[A-Z\s]{4,}\b)", l) for l in lines):
                curr_start = 0
                curr_lines = []
                for line in lines:
                    line_len = len(line) + 1
                    is_bullet = bool(re.match(r"^\s*([•\-\*]|\d+\.|\b[A-Z\s]{4,}\b)", line))
                    if is_bullet and curr_lines:
                        block_txt = "\n".join(curr_lines).strip()
                        if block_txt:
                            blocks.append({
                                "text": block_txt,
                                "start": curr_start,
                                "end": curr_start + len(block_txt),
                                "type": "paragraph"
                            })
                        curr_start = curr_start + len("\n".join(curr_lines)) + 1
                        curr_lines = [line]
                    else:
                        curr_lines.append(line)
                if curr_lines:
                    block_txt = "\n".join(curr_lines).strip()
                    if block_txt:
                        blocks.append({
                            "text": block_txt,
                            "start": curr_start,
                            "end": curr_start + len(block_txt),
                            "type": "paragraph"
                        })
                return blocks if blocks else [{"text": text.strip(), "start": 0, "end": len(text.strip()), "type": "paragraph"}]
            else:
                return [{"text": text.strip(), "start": 0, "end": len(text.strip()), "type": "paragraph"}]

        last_end = 0
        for m in splits:
            seg = text[last_end:m.start()].strip()
            if seg:
                # find exact start in text
                exact_start = text.find(seg, last_end)
                blocks.append({
                    "text": seg,
                    "start": exact_start,
                    "end": exact_start + len(seg),
                    "type": "paragraph"
                })
            last_end = m.end()

        if last_end < len(text):
            seg = text[last_end:].strip()
            if seg:
                exact_start = text.find(seg, last_end)
                blocks.append({
                    "text": seg,
                    "start": exact_start,
                    "end": exact_start + len(seg),
                    "type": "paragraph"
                })

        return blocks

    @classmethod
    def _chunk_text(cls, text: str, target_tokens: int, overlap_tokens: int) -> List[ChunkData]:
        blocks = cls._split_into_structural_blocks(text)
        return cls._assemble_chunks_from_blocks(text, blocks, target_tokens, overlap_tokens)

    @classmethod
    def _chunk_markdown(cls, text: str, target_tokens: int, overlap_tokens: int) -> List[ChunkData]:
        # Parse Markdown headings, fenced code blocks, and text paragraphs
        lines = text.split("\n")
        blocks: List[Dict[str, Any]] = []
        in_code = False
        code_lines: List[str] = []
        code_start = 0
        current_lines: List[str] = []
        current_start = 0
        char_offset = 0

        for line in lines:
            line_len = len(line) + 1
            fence_match = re.match(r"^(\s*```[a-zA-Z0-9_-]*)", line)
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)

            if fence_match and not in_code:
                if current_lines:
                    txt = "\n".join(current_lines).strip()
                    if txt:
                        blocks.append({"type": "paragraph", "text": txt, "start": current_start, "end": current_start + len(txt), "heading": []})
                    current_lines = []
                in_code = True
                code_start = char_offset
                code_lines = [line]
                char_offset += line_len
                continue
            elif in_code and line.strip().startswith("```"):
                code_lines.append(line)
                txt = "\n".join(code_lines).strip()
                blocks.append({"type": "code", "text": txt, "start": code_start, "end": code_start + len(txt), "heading": []})
                in_code = False
                code_lines = []
                char_offset += line_len
                continue
            elif in_code:
                code_lines.append(line)
                char_offset += line_len
                continue

            if heading_match and not in_code:
                if current_lines:
                    txt = "\n".join(current_lines).strip()
                    if txt:
                        blocks.append({"type": "paragraph", "text": txt, "start": current_start, "end": current_start + len(txt), "heading": []})
                    current_lines = []
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                blocks.append({
                    "type": "heading",
                    "text": line.strip(),
                    "start": char_offset,
                    "end": char_offset + len(line.strip()),
                    "heading": [title],
                    "level": level
                })
                char_offset += line_len
                continue

            if not current_lines:
                current_start = char_offset
            current_lines.append(line)
            char_offset += line_len

        if in_code and code_lines:
            txt = "\n".join(code_lines).strip()
            blocks.append({"type": "code", "text": txt, "start": code_start, "end": code_start + len(txt), "heading": []})
        elif current_lines:
            txt = "\n".join(current_lines).strip()
            if txt:
                blocks.append({"type": "paragraph", "text": txt, "start": current_start, "end": current_start + len(txt), "heading": []})

        return cls._assemble_chunks_from_blocks(text, blocks, target_tokens, overlap_tokens)

    @classmethod
    def _chunk_pdf(
        cls,
        text: str,
        pages: List[Dict[str, Any]],
        target_tokens: int,
        overlap_tokens: int
    ) -> List[ChunkData]:
        # Form structural blocks with page numbers
        blocks: List[Dict[str, Any]] = []
        for p in pages:
            page_num = p["page_number"]
            page_text = p["text"].strip()
            if not page_text:
                continue

            page_blocks = cls._split_into_structural_blocks(page_text)
            for pb in page_blocks:
                exact_start = text.find(pb["text"], p["char_start"])
                if exact_start == -1:
                    exact_start = p["char_start"]
                blocks.append({
                    "type": "paragraph",
                    "text": pb["text"],
                    "start": exact_start,
                    "end": exact_start + len(pb["text"]),
                    "page": page_num
                })

        return cls._assemble_chunks_from_blocks(text, blocks, target_tokens, overlap_tokens)

    @classmethod
    def _assemble_chunks_from_blocks(
        cls,
        full_text: str,
        blocks: List[Dict[str, Any]],
        target_tokens: int,
        overlap_tokens: int
    ) -> List[ChunkData]:
        chunks: List[ChunkData] = []
        if not blocks:
            tokens = TokenizerService.count_tokens(full_text)
            return [ChunkData(
                chunk_index=0,
                content=full_text,
                token_count=tokens,
                character_start=0,
                character_end=len(full_text),
                source_location={"character_start": 0, "character_end": len(full_text)},
                heading_path=[],
                content_hash=compute_text_hash(full_text),
                split_reason="document_end"
            )]

        # Prepare blocks with their exact token count
        prepared_blocks = []
        for b in blocks:
            b_txt = b["text"].strip()
            if not b_txt:
                continue
            b_tokens = TokenizerService.count_tokens(b_txt)
            # If a single block exceeds target_tokens, split it by sentence or lines
            if b_tokens > target_tokens:
                sub_sentences = re.split(r"(?<=[.!?])\s+", b_txt)
                if len(sub_sentences) <= 1:
                    # fallback to lines
                    sub_sentences = [l.strip() for l in b_txt.split("\n") if l.strip()]

                curr_sub_start = b["start"]
                for sent in sub_sentences:
                    s_tokens = TokenizerService.count_tokens(sent)
                    exact_s_start = full_text.find(sent, curr_sub_start)
                    if exact_s_start == -1:
                        exact_s_start = curr_sub_start
                    prepared_blocks.append({
                        "text": sent,
                        "tokens": s_tokens,
                        "start": exact_s_start,
                        "end": exact_s_start + len(sent),
                        "type": "sentence",
                        "heading": b.get("heading", []),
                        "page": b.get("page")
                    })
                    curr_sub_start = exact_s_start + len(sent)
            else:
                prepared_blocks.append({
                    "text": b_txt,
                    "tokens": b_tokens,
                    "start": b["start"],
                    "end": b["end"],
                    "type": b.get("type", "paragraph"),
                    "heading": b.get("heading", []),
                    "page": b.get("page")
                })

        # Assemble into chunks
        accum_blocks: List[Dict[str, Any]] = []
        accum_tokens = 0
        active_headings: List[str] = []

        for idx, block in enumerate(prepared_blocks):
            if block.get("heading"):
                active_headings = block["heading"]

            is_heading = block.get("type") == "heading"
            next_tokens = accum_tokens + block["tokens"]

            # Decide whether to split
            should_split = False
            split_reason = "target_size_limit"

            if is_heading and accum_tokens >= (target_tokens // 2):
                should_split = True
                split_reason = "heading_boundary"
            elif next_tokens > target_tokens and accum_blocks:
                should_split = True
                split_reason = "target_size_limit"

            if should_split and accum_blocks:
                # Flush current chunk
                chunk_obj = cls._build_chunk(
                    full_text=full_text,
                    chunk_index=len(chunks),
                    accum_blocks=accum_blocks,
                    split_reason=split_reason,
                    heading_path=list(active_headings)
                )
                chunks.append(chunk_obj)

                # Overlap calculation
                overlap_accum: List[Dict[str, Any]] = []
                overlap_toks = 0
                if overlap_tokens > 0:
                    for prev_b in reversed(accum_blocks):
                        if overlap_toks + prev_b["tokens"] <= overlap_tokens:
                            overlap_accum.insert(0, prev_b)
                            overlap_toks += prev_b["tokens"]
                        else:
                            break

                accum_blocks = overlap_accum + [block]
                accum_tokens = overlap_toks + block["tokens"]
            else:
                accum_blocks.append(block)
                accum_tokens += block["tokens"]

        if accum_blocks:
            chunk_obj = cls._build_chunk(
                full_text=full_text,
                chunk_index=len(chunks),
                accum_blocks=accum_blocks,
                split_reason="document_end",
                heading_path=list(active_headings)
            )
            chunks.append(chunk_obj)

        return chunks

    @classmethod
    def _build_chunk(
        cls,
        full_text: str,
        chunk_index: int,
        accum_blocks: List[Dict[str, Any]],
        split_reason: str,
        heading_path: List[str]
    ) -> ChunkData:
        start_char = accum_blocks[0]["start"]
        end_char = accum_blocks[-1]["end"]
        content = full_text[start_char:end_char].strip()
        tokens = TokenizerService.count_tokens(content)

        pages = [b["page"] for b in accum_blocks if b.get("page")]
        loc: Dict[str, Any] = {
            "character_start": start_char,
            "character_end": end_char
        }
        if pages:
            loc["page_start"] = min(pages)
            loc["page_end"] = max(pages)
            loc["page"] = min(pages)

        return ChunkData(
            chunk_index=chunk_index,
            content=content,
            token_count=tokens,
            character_start=start_char,
            character_end=end_char,
            source_location=loc,
            heading_path=heading_path,
            content_hash=compute_text_hash(content),
            split_reason=split_reason,
            token_count_model=TokenizerService.TOKENIZER_NAME
        )

    @classmethod
    def _split_oversized_chunk(
        cls, chunk: ChunkData, full_text: str, max_tokens: int = 510
    ) -> List[ChunkData]:
        """
        Splits an oversized chunk into strictly compliant sub-chunks (<= max_tokens),
        preserving exact character offsets, heading path, source location, and content hashes.
        """
        content = chunk.content
        total_tokens = TokenizerService.count_tokens(content)
        if total_tokens <= max_tokens:
            return [chunk]

        # Break content into smaller segments: sentences first, then lines, clauses, or whitespace
        sentence_splits = re.split(r"(?<=[.!?])\s+", content)
        if len(sentence_splits) <= 1:
            sentence_splits = [l.strip() for l in content.split("\n") if l.strip()]
        if len(sentence_splits) <= 1:
            sentence_splits = re.split(r"(?<=[,;:])\s+", content)
        if len(sentence_splits) <= 1:
            # Unbroken text: split by words
            sentence_splits = content.split()
            if len(sentence_splits) <= 1:
                # Completely unbroken single string: slice by characters
                char_step = max(50, (max_tokens - 10) * 3)
                sentence_splits = [content[i:i + char_step] for i in range(0, len(content), char_step)]

        sub_chunks: List[ChunkData] = []
        current_pieces: List[str] = []
        current_tokens = 0
        search_start = chunk.character_start

        for piece in sentence_splits:
            p = piece.strip()
            if not p:
                continue
            p_toks = TokenizerService.count_tokens(p)

            # If a single piece is still > max_tokens, slice it further by words
            if p_toks > max_tokens:
                if current_pieces:
                    exact_sub_start = full_text.find(current_pieces[0], search_start)
                    if exact_sub_start == -1:
                        exact_sub_start = search_start
                    exact_sub_end = full_text.find(current_pieces[-1], exact_sub_start) + len(current_pieces[-1])
                    sub_content = full_text[exact_sub_start:exact_sub_end].strip()
                    s_loc = dict(chunk.source_location)
                    s_loc["character_start"] = exact_sub_start
                    s_loc["character_end"] = exact_sub_end
                    sub_chunks.append(ChunkData(
                        chunk_index=0,
                        content=sub_content,
                        token_count=TokenizerService.count_tokens(sub_content),
                        character_start=exact_sub_start,
                        character_end=exact_sub_end,
                        source_location=s_loc,
                        heading_path=list(chunk.heading_path),
                        content_hash=compute_text_hash(sub_content),
                        split_reason="enforced_embedding_limit",
                        token_count_model=TokenizerService.TOKENIZER_NAME
                    ))
                    search_start = exact_sub_end
                    current_pieces = []
                    current_tokens = 0

                words = p.split()
                sub_words: List[str] = []
                sub_w_toks = 0
                for w in words:
                    w_t = TokenizerService.count_tokens(w)
                    if sub_w_toks + w_t > max_tokens and sub_words:
                        exact_start = full_text.find(sub_words[0], search_start)
                        if exact_start == -1:
                            exact_start = search_start
                        exact_end = full_text.find(sub_words[-1], exact_start) + len(sub_words[-1])
                        slice_content = full_text[exact_start:exact_end].strip()
                        s_loc = dict(chunk.source_location)
                        s_loc["character_start"] = exact_start
                        s_loc["character_end"] = exact_end
                        sub_chunks.append(ChunkData(
                            chunk_index=0,
                            content=slice_content,
                            token_count=TokenizerService.count_tokens(slice_content),
                            character_start=exact_start,
                            character_end=exact_end,
                            source_location=s_loc,
                            heading_path=list(chunk.heading_path),
                            content_hash=compute_text_hash(slice_content),
                            split_reason="enforced_embedding_limit",
                            token_count_model=TokenizerService.TOKENIZER_NAME
                        ))
                        search_start = exact_end
                        sub_words = [w]
                        sub_w_toks = w_t
                    else:
                        sub_words.append(w)
                        sub_w_toks += w_t
                if sub_words:
                    current_pieces = sub_words
                    current_tokens = sub_w_toks
                continue

            if current_tokens + p_toks > max_tokens and current_pieces:
                exact_sub_start = full_text.find(current_pieces[0], search_start)
                if exact_sub_start == -1:
                    exact_sub_start = search_start
                exact_sub_end = full_text.find(current_pieces[-1], exact_sub_start) + len(current_pieces[-1])
                sub_content = full_text[exact_sub_start:exact_sub_end].strip()
                s_loc = dict(chunk.source_location)
                s_loc["character_start"] = exact_sub_start
                s_loc["character_end"] = exact_sub_end
                sub_chunks.append(ChunkData(
                    chunk_index=0,
                    content=sub_content,
                    token_count=TokenizerService.count_tokens(sub_content),
                    character_start=exact_sub_start,
                    character_end=exact_sub_end,
                    source_location=s_loc,
                    heading_path=list(chunk.heading_path),
                    content_hash=compute_text_hash(sub_content),
                    split_reason="enforced_embedding_limit",
                    token_count_model=TokenizerService.TOKENIZER_NAME
                ))
                search_start = exact_sub_end
                current_pieces = [p]
                current_tokens = p_toks
            else:
                current_pieces.append(p)
                current_tokens += p_toks

        if current_pieces:
            exact_sub_start = full_text.find(current_pieces[0], search_start)
            if exact_sub_start == -1:
                exact_sub_start = search_start
            exact_sub_end = full_text.find(current_pieces[-1], exact_sub_start) + len(current_pieces[-1])
            sub_content = full_text[exact_sub_start:exact_sub_end].strip()
            s_loc = dict(chunk.source_location)
            s_loc["character_start"] = exact_sub_start
            s_loc["character_end"] = exact_sub_end
            sub_chunks.append(ChunkData(
                chunk_index=0,
                content=sub_content,
                token_count=TokenizerService.count_tokens(sub_content),
                character_start=exact_sub_start,
                character_end=exact_sub_end,
                source_location=s_loc,
                heading_path=list(chunk.heading_path),
                content_hash=compute_text_hash(sub_content),
                split_reason="enforced_embedding_limit",
                token_count_model=TokenizerService.TOKENIZER_NAME
            ))

        return sub_chunks

    @classmethod
    def _enforce_embedding_limits(
        cls, chunks: List[ChunkData], full_text: str, max_tokens: int = 510
    ) -> List[ChunkData]:
        final_chunks: List[ChunkData] = []
        for chunk in chunks:
            if chunk.token_count > max_tokens:
                sub_chunks = cls._split_oversized_chunk(chunk, full_text, max_tokens)
                final_chunks.extend(sub_chunks)
            else:
                final_chunks.append(chunk)

        for i, c in enumerate(final_chunks):
            c.chunk_index = i
        return final_chunks

    @classmethod
    def compare_chunk_sizes(
        cls,
        text: Optional[str] = None,
        raw_text: Optional[str] = None,
        file_extension: str = ".txt",
        pages: Optional[List[Dict[str, Any]]] = None,
        headings: Optional[List[Dict[str, Any]]] = None,
        target_sizes: List[int] = [256, 512, 800, 1024]
    ) -> List[Dict[str, Any]]:
        """
        Runs non-destructive comparison of structure-aware chunking on identical source text
        across different target sizes (256, 512, 800, 1024 tokens).
        """
        source_text = text if text is not None else (raw_text or "")
        results = []
        total_source_tokens = TokenizerService.count_tokens(source_text)

        for target in target_sizes:
            overlap = min(100, target // 8)
            chunks = cls.chunk_document(
                raw_text=source_text,
                file_extension=file_extension,
                pages=pages,
                headings=headings,
                target_tokens=target,
                overlap_tokens=overlap,
                enforce_limit=False
            )

            token_counts = [c.token_count for c in chunks] if chunks else [0]
            total_chunk_tokens = sum(token_counts)

            # Measure unique character coverage
            covered_mask = [False] * len(source_text)
            for c in chunks:
                for idx in range(max(0, c.character_start), min(len(source_text), c.character_end)):
                    covered_mask[idx] = True

            uncovered_chars = covered_mask.count(False)
            uncovered_pct = round((uncovered_chars / len(source_text)) * 100, 2) if len(source_text) > 0 else 0.0

            # Find uncovered ranges
            uncovered_ranges = []
            range_start = None
            for i, covered in enumerate(covered_mask):
                if not covered and range_start is None:
                    range_start = i
                elif covered and range_start is not None:
                    uncovered_ranges.append({"start": range_start, "end": i, "length": i - range_start})
                    range_start = None
            if range_start is not None:
                uncovered_ranges.append({"start": range_start, "end": len(source_text), "length": len(source_text) - range_start})

            max_tok = max(token_counts) if token_counts else 0
            has_trunc_risk = target > 512 or max_tok > 512

            candidates = [
                {
                    "chunk_index": c.chunk_index,
                    "token_count": c.token_count,
                    "char_count": len(c.content),
                    "character_start": c.character_start,
                    "character_end": c.character_end,
                    "split_reason": c.split_reason,
                    "content_preview": c.content[:80] + "..." if len(c.content) > 80 else c.content,
                    "heading_path": c.heading_path
                }
                for c in chunks
            ]

            results.append({
                "target_tokens": target,
                "overlap_setting_tokens": overlap,
                "chunk_count": len(chunks),
                "min_tokens": min(token_counts) if token_counts else 0,
                "median_tokens": round(statistics.median(token_counts), 1) if token_counts else 0,
                "mean_tokens": round(total_chunk_tokens / max(1, len(chunks)), 1),
                "max_tokens": max_tok,
                "total_chunk_tokens": total_chunk_tokens,
                "total_source_tokens": total_source_tokens,
                "overlap_token_estimate": max(0, total_chunk_tokens - total_source_tokens),
                "uncovered_chars": uncovered_chars,
                "uncovered_percentage": uncovered_pct,
                "uncovered_ranges": uncovered_ranges,
                "truncation_risk": has_trunc_risk,
                "risk_reason": (
                    f"Target {target} tokens exceeds model limit of 512. Chunks larger than 512 will be truncated by sentence-transformers."
                    if has_trunc_risk else None
                ),
                "tokenizer": TokenizerService.TOKENIZER_NAME,
                "chunks": candidates,
                "chunks_summary": candidates
            })

        return results
