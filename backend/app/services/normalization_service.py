import re
import unicodedata
from typing import List, Dict, Any, Tuple, Optional
from app.services.tokenizer_service import TokenizerService


class NormalizationOperationRecord:
    def __init__(
        self,
        name: str,
        version: str,
        applied: bool,
        chars_before: int,
        chars_after: int,
        tokens_before: int,
        tokens_after: int,
        diff_snippet: Optional[str],
        reason: str,
        warning: Optional[str] = None
    ):
        self.name = name
        self.version = version
        self.applied = applied
        self.chars_before = chars_before
        self.chars_after = chars_after
        self.chars_delta = chars_after - chars_before
        self.tokens_before = tokens_before
        self.tokens_after = tokens_after
        self.tokens_delta = tokens_after - tokens_before
        self.diff_snippet = diff_snippet
        self.reason = reason
        self.warning = warning

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "applied": self.applied,
            "chars_before": self.chars_before,
            "chars_after": self.chars_after,
            "chars_delta": self.chars_delta,
            "tokens_before": self.tokens_before,
            "tokens_after": self.tokens_after,
            "tokens_delta": self.tokens_delta,
            "diff_snippet": self.diff_snippet,
            "reason": self.reason,
            "warning": self.warning
        }


class NormalizationResult:
    def __init__(
        self,
        original_text: str,
        normalized_text: str,
        operations: List[NormalizationOperationRecord],
        chars_before: int,
        chars_after: int,
        tokens_before: int,
        tokens_after: int
    ):
        self.original_text = original_text
        self.normalized_text = normalized_text
        self.operations = operations
        self.chars_before = chars_before
        self.chars_after = chars_after
        self.tokens_before = tokens_before
        self.tokens_after = tokens_after

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chars_before": self.chars_before,
            "chars_after": self.chars_after,
            "chars_delta": self.chars_after - self.chars_before,
            "tokens_before": self.tokens_before,
            "tokens_after": self.tokens_after,
            "tokens_delta": self.tokens_after - self.tokens_before,
            "operations": [op.to_dict() for op in self.operations]
        }

    @property
    def summary(self) -> Dict[str, Any]:
        return {
            "initial_chars": self.chars_before,
            "final_chars": self.chars_after,
            "char_delta": self.chars_after - self.chars_before,
            "initial_tokens": self.tokens_before,
            "final_tokens": self.tokens_after,
            "token_delta": self.tokens_after - self.tokens_before
        }


COMPOUND_PREFIXES = {
    "high", "low", "real", "full", "cross", "open", "built", "well", "cost", "time",
    "zero", "single", "dual", "multi", "front", "back", "end", "top", "side",
    "client", "server", "cloud", "data", "load", "state", "user", "co", "first",
    "last", "large", "small", "fine", "near", "long", "short", "off", "on", "in", "out"
}

KNOWN_MERGED_WORDS = {
    "orchestration", "attendance", "software", "hardware", "infrastructure",
    "architecture", "distributed", "environment", "configuration", "initialization",
    "connection", "application", "transaction", "performance", "engineering",
    "development", "production", "scalability", "concurrency", "deployment",
    "repository", "processing", "information", "specification", "implementation",
    "authentication", "authorization", "synchronization", "communication",
    "compatibility", "availability", "reliability", "optimization", "transformation",
    "documentation", "microservices", "kubernetes", "postgresql", "yugabyte",
    "elasticsearch", "middleware", "continuous", "integration", "management",
    "experience", "internship", "university", "technologies", "intelligence",
    "operations", "telemetry", "observability", "foundational", "responsibilities",
    "collaborated", "designing", "optimizing", "deploying", "monitoring",
    "troubleshooting", "automated", "automation", "benchmarking", "instrumentation",
    "validation", "verification", "refactoring", "containerization", "unwrapped"
}

SPLIT_WORD_SUFFIXES = (
    "tion", "tions", "sion", "sions", "ment", "ments", "ance", "ances",
    "ence", "ences", "able", "ible", "ity", "ities", "ness", "less",
    "ful", "fully", "ing", "ings", "ed", "ize", "ized", "izing", "ware"
)


class NormalizationService:
    @classmethod
    def normalize_text(
        cls,
        text: str,
        file_extension: str,
        pages: Optional[List[Dict[str, Any]]] = None
    ) -> NormalizationResult:
        return cls.normalize(text=text, file_extension=file_extension, pages=pages)

    @classmethod
    def normalize(
        cls,
        text: str,
        file_extension: str,
        pages: Optional[List[Dict[str, Any]]] = None
    ) -> NormalizationResult:
        """
        Executes an auditable sequence of deterministic normalizations.
        Preserves Markdown formatting, numbers, technical identifiers, code, and source quotes.
        Distinguishes line-wrapped word fragments from compound words.
        """
        current_text = text
        operations: List[NormalizationOperationRecord] = []
        ext = file_extension.lower().lstrip(".")

        init_tokens = TokenizerService.count_tokens(text)
        current_tokens = init_tokens

        # 1. Unicode NFC Normalization
        op_name = "unicode_nfc_normalization"
        chars_before = len(current_text)
        tokens_before = current_tokens
        nfc_text = unicodedata.normalize("NFC", current_text)
        if nfc_text != current_text:
            diff_sample = f"Replaced {len(current_text) - len(nfc_text)} uncomposed character sequences."
            current_tokens = TokenizerService.count_tokens(nfc_text)
            operations.append(NormalizationOperationRecord(
                name=op_name,
                version="1.0.0",
                applied=True,
                chars_before=chars_before,
                chars_after=len(nfc_text),
                tokens_before=tokens_before,
                tokens_after=current_tokens,
                diff_snippet=diff_sample,
                reason="Canonicalizes Unicode combining sequences into single precomposed codepoints without loss."
            ))
            current_text = nfc_text
        else:
            operations.append(NormalizationOperationRecord(
                name=op_name,
                version="1.0.0",
                applied=False,
                chars_before=chars_before,
                chars_after=chars_before,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                diff_snippet=None,
                reason="Text was already in canonical NFC Unicode representation."
            ))

        # 2. Line Ending Normalization (\r\n and \r -> \n)
        op_name = "crlf_newline_normalization"
        chars_before = len(current_text)
        tokens_before = current_tokens
        if "\r" in current_text:
            crlf_text = current_text.replace("\r\n", "\n").replace("\r", "\n")
            crlf_count = current_text.count("\r")
            current_tokens = TokenizerService.count_tokens(crlf_text)
            operations.append(NormalizationOperationRecord(
                name=op_name,
                version="1.0.0",
                applied=True,
                chars_before=chars_before,
                chars_after=len(crlf_text),
                tokens_before=tokens_before,
                tokens_after=current_tokens,
                diff_snippet=f"Replaced {crlf_count} carriage return characters with standard Unix newlines.",
                reason="Standardizes line breaks across operating systems without affecting paragraph boundaries."
            ))
            current_text = crlf_text
        else:
            operations.append(NormalizationOperationRecord(
                name=op_name,
                version="1.0.0",
                applied=False,
                chars_before=chars_before,
                chars_after=chars_before,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                diff_snippet=None,
                reason="No carriage return (CR) characters detected in input."
            ))

        # 3. Trailing Line Whitespace Removal
        op_name = "trailing_line_whitespace_removal"
        chars_before = len(current_text)
        tokens_before = current_tokens
        lines = current_text.split("\n")
        cleaned_lines = [re.sub(r"[ \t]+$", "", line) for line in lines]
        cleaned_trailing = "\n".join(cleaned_lines)
        if cleaned_trailing != current_text:
            diff_chars = len(current_text) - len(cleaned_trailing)
            current_tokens = TokenizerService.count_tokens(cleaned_trailing)
            operations.append(NormalizationOperationRecord(
                name=op_name,
                version="1.0.0",
                applied=True,
                chars_before=chars_before,
                chars_after=len(cleaned_trailing),
                tokens_before=tokens_before,
                tokens_after=current_tokens,
                diff_snippet=f"Removed {diff_chars} trailing space/tab characters at the ends of lines.",
                reason="Removes non-semantic trailing spaces while preserving indentation and empty line breaks."
            ))
            current_text = cleaned_trailing
        else:
            operations.append(NormalizationOperationRecord(
                name=op_name,
                version="1.0.0",
                applied=False,
                chars_before=chars_before,
                chars_after=chars_before,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                diff_snippet=None,
                reason="No trailing spaces or tabs detected on line ends."
            ))

        # 4. Excessive Blank Line Collapse (3+ consecutive newlines -> 2 newlines)
        op_name = "excessive_blank_line_collapse"
        chars_before = len(current_text)
        tokens_before = current_tokens
        collapsed = re.sub(r"\n{3,}", "\n\n", current_text)
        if collapsed != current_text:
            diff_chars = len(current_text) - len(collapsed)
            current_tokens = TokenizerService.count_tokens(collapsed)
            operations.append(NormalizationOperationRecord(
                name=op_name,
                version="1.0.0",
                applied=True,
                chars_before=chars_before,
                chars_after=len(collapsed),
                tokens_before=tokens_before,
                tokens_after=current_tokens,
                diff_snippet=f"Collapsed {diff_chars} redundant consecutive blank line separators.",
                reason="Preserves double-newline paragraph breaks while removing triple+ blank spacing."
            ))
            current_text = collapsed
        else:
            operations.append(NormalizationOperationRecord(
                name=op_name,
                version="1.0.0",
                applied=False,
                chars_before=chars_before,
                chars_after=chars_before,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                diff_snippet=None,
                reason="No instances of 3 or more consecutive newlines found."
            ))

        # 5. PDF Line-Wrapped Dehyphenation (PDF only)
        op_name = "pdf_line_wrap_dehyphenation"
        if ext == "pdf":
            chars_before = len(current_text)
            tokens_before = current_tokens
            dehyphen_matches = []
            warnings = []

            def dehyphen_sub(match):
                prefix = match.group(1)
                suffix = match.group(2)
                prefix_l = prefix.lower()
                suffix_l = suffix.lower()
                merged_c = f"{prefix_l}{suffix_l}"

                if prefix_l in COMPOUND_PREFIXES and suffix_l not in SPLIT_WORD_SUFFIXES and merged_c not in KNOWN_MERGED_WORDS:
                    resolved = f"{prefix}-{suffix}"
                    dehyphen_matches.append(f"{prefix}- + {suffix} -> {resolved} (compound preserved)")
                    return resolved
                elif merged_c in KNOWN_MERGED_WORDS or any(suffix_l.endswith(sfx) for sfx in SPLIT_WORD_SUFFIXES if len(prefix_l) >= 3):
                    resolved = f"{prefix}{suffix}"
                    dehyphen_matches.append(f"{prefix}- + {suffix} -> {resolved} (word fragment merged)")
                    return resolved
                else:
                    resolved = f"{prefix}-{suffix}"
                    warn_msg = f"Ambiguous hyphenation for '{prefix}-\\n{suffix}'; preserved hyphen."
                    warnings.append(warn_msg)
                    dehyphen_matches.append(f"{prefix}- + {suffix} -> {resolved} (ambiguous preserved)")
                    return resolved

            dehyphen_text = re.sub(r"([a-zA-Z]{2,})-\n\s*([a-zA-Z]{2,})", dehyphen_sub, current_text)
            if dehyphen_matches:
                current_tokens = TokenizerService.count_tokens(dehyphen_text)
                diff_summary = f"Dehyphenated {len(dehyphen_matches)} line-wrapped words: " + "; ".join(dehyphen_matches[:5])
                combined_warning = "; ".join(warnings[:3]) if warnings else None
                operations.append(NormalizationOperationRecord(
                    name=op_name,
                    version="1.1.0",
                    applied=True,
                    chars_before=chars_before,
                    chars_after=len(dehyphen_text),
                    tokens_before=tokens_before,
                    tokens_after=current_tokens,
                    diff_snippet=diff_summary,
                    reason="Repairs line-wrapped word fragments into single words while preserving legitimate compound words.",
                    warning=combined_warning
                ))
                current_text = dehyphen_text
            else:
                operations.append(NormalizationOperationRecord(
                    name=op_name,
                    version="1.1.0",
                    applied=False,
                    chars_before=chars_before,
                    chars_after=chars_before,
                    tokens_before=tokens_before,
                    tokens_after=tokens_before,
                    diff_snippet=None,
                    reason="No line-wrapped hyphenated words detected in PDF text."
                ))
        else:
            operations.append(NormalizationOperationRecord(
                name=op_name,
                version="1.1.0",
                applied=False,
                chars_before=len(current_text),
                chars_after=len(current_text),
                tokens_before=current_tokens,
                tokens_after=current_tokens,
                diff_snippet=None,
                reason="Skipped for non-PDF format (Markdown/TXT line breaks are intentional)."
            ))

        # 6. Repeated Page Header/Footer Detection (PDF with >= 2 pages)
        op_name = "repeated_header_footer_detection"
        if ext == "pdf" and pages and len(pages) >= 2:
            chars_before = len(current_text)
            tokens_before = current_tokens
            first_lines = [p["text"].strip().split("\n")[0] for p in pages if p["text"].strip()]
            repeated_first = None
            if first_lines and len(set(first_lines)) == 1 and len(first_lines[0]) > 3:
                repeated_first = first_lines[0]

            if repeated_first:
                # Detected confident repeating header
                # We log it explicitly as an audit detection
                operations.append(NormalizationOperationRecord(
                    name=op_name,
                    version="1.0.0",
                    applied=False,
                    chars_before=chars_before,
                    chars_after=chars_before,
                    tokens_before=tokens_before,
                    tokens_after=tokens_before,
                    diff_snippet=f"Detected repeating page header on all pages: '{repeated_first}'",
                    reason="Audited repeating header; preserved in text to guarantee complete evidence retention.",
                    warning="Repeating header flagged but preserved for audit integrity."
                ))
            else:
                operations.append(NormalizationOperationRecord(
                    name=op_name,
                    version="1.0.0",
                    applied=False,
                    chars_before=chars_before,
                    chars_after=chars_before,
                    tokens_before=tokens_before,
                    tokens_after=tokens_before,
                    diff_snippet=None,
                    reason="No identical repeating page headers detected across pages."
                ))
        else:
            operations.append(NormalizationOperationRecord(
                name=op_name,
                version="1.0.0",
                applied=False,
                chars_before=len(current_text),
                chars_after=len(current_text),
                tokens_before=current_tokens,
                tokens_after=current_tokens,
                diff_snippet=None,
                reason="Skipped: document has fewer than 2 pages or is non-PDF."
            ))

        return NormalizationResult(
            original_text=text,
            normalized_text=current_text,
            operations=operations,
            chars_before=len(text),
            chars_after=len(current_text),
            tokens_before=init_tokens,
            tokens_after=current_tokens
        )
