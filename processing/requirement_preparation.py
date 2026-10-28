"""Prepare requirement text before it enters the primary transaction matrix.

The page wording stays in required_document. required_document_normalized
is the name used for mining. A written synonym list covers four documents
the charters repeat under different wording: the PSA birth certificate,
the NBI clearance, the transcript of records, and the PSA marriage
certificate. A step, a section label, or a policy note is not a required
document. A cell that lists several documents is split into one row each.
"""

from __future__ import annotations

import re

from scraper.parsers.generic import clean_text

BIRTH = "Certificate of Live Birth (PSA)"
NBI = "NBI Clearance"
TOR = "Transcript of Records (TOR)"
MARRIAGE = "PSA Marriage Certificate"

_QUANTITY = re.compile(
    r"^(?:(?:\d+[.)]\s*)+|(?:one\s*\(1\)\s+)?)?"
    r"(?:(?:"
    r"one\s*\(1\)\s+original and photocopy of|"
    r"one\s*\(1\)\s+original copy of(?: the)?|"
    r"one\s*\(1\)\s+original or certified true copy of(?: the)?|"
    r"one copy each of the original and photocopy of(?: the)?|"
    r"\(1\)\s*original and photocopy of valid|"
    r"original and photocopy of(?: the)?|"
    r"original and certified true copy of|"
    r"photocopy of|original of|valid"
    r")\s+)?",
    re.I,
)
_RA_NOTE = re.compile(
    r"\(?\s*subject to the provisions of\s+r\.?\s*a\.?\s*(?:no\.?\s*)?119(?:09|19)[^.;)]*[.)]?",
    re.I,
)
_VALIDITY = re.compile(
    r"\(?\s*valid(?:\s+at\s+least|\s+for)?[^.;)]{0,90}(?:application|filing)[^.;)]*\)?",
    re.I,
)
_MARRIED_FEMALE = re.compile(
    r"\(?\s*for\s+(?:married\s+)?female(?:\s+married)?\s+applicants?[^.;)]*\)?",
    re.I,
)
_FIRST_TIMER = re.compile(r"\(?\s*first\s+timers\s+and\s+repeaters\s*\)?", re.I)
_ISSUED_BY_PSA = re.compile(
    r"(?:issued by the\s+)?philippine statistics authority\s*\(psa\)\s*[- ]?\s*issued\s+",
    re.I,
)


def is_procedure(text: str) -> bool:
    """A step, a section label, or a note that does not name one document."""
    cleaned = clean_text(text)
    low = cleaned.lower().strip(" .;:")
    if not low:
        return False
    step_starts = (
        "apply for ss number",
        "apply for ",
        "create a my.sss account",
        "choose from the list of supporting documents",
        "how to apply for ss number",
        "how to apply",
        "biometrics capture",
        "at the nbi branch",
        "crucial step",
        "go to the designated",
        "a repeater examinee",
        "in the absence of the birth certificate",
        "basis for computing taxes",
    )
    if low.startswith(step_starts):
        return True
    if "submission of the birth and marriage certificates shall be subject" in low:
        return True
    if "click" in low and "submit" in low:
        return True
    exact_labels = {
        "disability",
        "retirement",
        "with earliest issued ss number",
        "with the greatest number of posted contributions",
    }
    if low.rstrip(".") in exact_labels or low.startswith("with most recent posted contributions"):
        return True
    if low.startswith("repeater examinee"):
        return True
    if low.startswith("pension administration"):
        return True
    if low.startswith("if other beneficiary") and "no required document" in low:
        return True
    return False


def is_conditional_instruction(text: str) -> bool:
    """A member-data case that names what to bring only in that situation."""
    low = clean_text(text).lower()
    return low.startswith((
        "from single to ",
        "from married to ",
        "if child",
        "if legally married",
        "if not legally married",
        "if spouse",
        "if parent",
        "for deletion of ",
        "for reporting of ",
        "for reversion from ",
    ))


def split_checklist(text: str) -> list[str] | None:
    """Split a cell that names several documents. Leave a single document intact."""
    cleaned = clean_text(text)
    if not cleaned or is_procedure(cleaned) or is_conditional_instruction(cleaned):
        return None
    low = cleaned.lower()
    if low.startswith(("for ", "if ", "from ", "in the absence", "a repeater", "repeater examinee")):
        return None

    parts = _semicolon_parts(cleaned)
    if parts is None:
        parts = _diploma_and_tor_and_equivalency(cleaned)
    if parts is None:
        parts = _cav_and_tor(cleaned)
    if parts is None:
        parts = _prefix_plus_diploma(cleaned)
    if parts is None:
        parts = _diploma_and_transcript(cleaned)
    if parts is None:
        parts = _birth_and_marriage(cleaned)
    if parts is None:
        parts = _jammed_documents(cleaned)
    if parts is None:
        return None

    atomic: list[str] = []
    for part in parts:
        nested = _diploma_and_transcript(part)
        atomic.extend(nested or [part])
    atomic = [part for part in atomic if not _is_catchall(part)]
    if len(atomic) < 2:
        return None
    return atomic


def canonicalize_document(text: str) -> str | None:
    """Return the canonical name when this cell is one of the four repeated documents."""
    cleaned = clean_text(text)
    if not cleaned or is_procedure(cleaned) or split_checklist(cleaned):
        return None
    core = _core(cleaned)
    if not core or _mentions_other_document(core):
        return None
    if _is_birth(core):
        return BIRTH
    if _is_nbi(core):
        return NBI
    if _is_tor(core):
        return TOR
    if _is_marriage(core):
        return MARRIAGE
    return None


def prepare_required_row(row: dict[str, str]) -> list[dict[str, str]]:
    """Return the dependency rows that should replace one required row."""
    original = row.get("required_document") or ""
    if is_procedure(original):
        kept = dict(row)
        kept["relationship_type"] = "procedure"
        kept["required_document_normalized"] = clean_text(original).strip(" ;,.")
        if not (kept.get("condition") or "").strip():
            kept["condition"] = "Not a required document. This row is a step, a section label, or a policy note."
        return [kept]

    if is_conditional_instruction(original):
        kept = dict(row)
        kept["relationship_type"] = "conditional"
        canonical = canonicalize_document(original)
        kept["required_document_normalized"] = canonical or clean_text(original).strip(" ;,.")
        if not (kept.get("condition") or "").strip():
            kept["condition"] = "Required only in the situation named in the row, not for every application."
        return [kept]

    parts = split_checklist(original)
    if parts:
        prepared = []
        for part in parts:
            item = dict(row)
            item["required_document"] = part
            item["required_document_normalized"] = canonicalize_document(part) or clean_text(part).strip(" ;,.")
            item["relationship_type"] = "required"
            prepared.append(item)
        return prepared

    updated = dict(row)
    canonical = canonicalize_document(original)
    if canonical:
        updated["required_document_normalized"] = canonical
    return [updated]


def _semicolon_parts(text: str) -> list[str] | None:
    if ";" not in text:
        return None
    parts = [clean_text(part).strip(" ;.") for part in text.split(";")]
    parts = [re.sub(r"^and\s+", "", part, flags=re.I).strip() for part in parts if part]
    parts = [part for part in parts if not part.lower().startswith("or ")]
    document_parts = [part for part in parts if _looks_like_document_part(part) or _is_catchall(part)]
    if len([part for part in document_parts if not _is_catchall(part)]) < 2:
        return None
    return document_parts


def _diploma_and_tor_and_equivalency(text: str) -> list[str] | None:
    match = re.match(
        r"^(?P<diploma>college diploma)\s+and\s+(?P<tor>tor)\b\s*,?\s*and\s+(?P<extra>certificate of equivalency\b.*)$",
        clean_text(text),
        re.I,
    )
    if not match:
        return None
    return [clean_text(match.group("diploma")), "Transcript of Records (TOR)", clean_text(match.group("extra"))]


def _cav_and_tor(text: str) -> list[str] | None:
    cleaned = clean_text(text)
    if not re.search(r"\bcav\b", cleaned, re.I) or not re.search(r"\band\s+tor\b", cleaned, re.I):
        return None
    left, right = re.split(r"\s+and\s+(?=tor\b)", cleaned, maxsplit=1, flags=re.I)
    if not left or not right:
        return None
    return [clean_text(left), clean_text(right)]


def _jammed_documents(text: str) -> list[str] | None:
    """Split a cell that pastes several document titles together without a semicolon."""
    cleaned = clean_text(text)
    if re.search(r"\bor\b", cleaned, re.I):
        return None
    matches = list(_JAMMED.finditer(cleaned))
    if len(matches) < 3:
        return None
    if matches[0].start() > 20:
        return None
    parts = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(cleaned)
        part = clean_text(cleaned[match.start():end]).strip(" ;,.-")
        if part and not _is_catchall(part):
            parts.append(part)
    if len(parts) < 3:
        return None
    return parts


_JAMMED = re.compile(
    r"psa birth certificate|certificate of live birth|psa marriage contract|psa marriage certificate|"
    r"marriage certificate|marriage contract|nbi clearance|college diploma|transcript of records|\btor\b|"
    r"certificates of good moral",
    re.I,
)


def _diploma_and_transcript(text: str) -> list[str] | None:
    match = re.match(
        r"^(?P<diploma>college diploma)\s+and\s+(?P<transcript>transcript of records?\b.*)$",
        clean_text(text),
        re.I,
    )
    if not match:
        return None
    return [clean_text(match.group("diploma")), clean_text(match.group("transcript"))]


def _prefix_plus_diploma(text: str) -> list[str] | None:
    cleaned = clean_text(text)
    match = re.search(r"\bcollege diploma and transcript of records?\b", cleaned, re.I)
    if not match or match.start() < 15:
        return None
    prefix = cleaned[:match.start()].strip(" ;,.")
    nested = _diploma_and_transcript(cleaned[match.start():])
    if not prefix or not nested:
        return None
    return [prefix, *nested]


def _birth_and_marriage(text: str) -> list[str] | None:
    match = re.match(
        r"^(?P<birth>certificate of live birth)\s*,\s*(?P<marriage>marriage contract\b.*)$",
        clean_text(text),
        re.I,
    )
    if not match:
        return None
    return [clean_text(match.group("birth")), clean_text(match.group("marriage"))]


def _is_catchall(text: str) -> bool:
    low = text.lower()
    return low.startswith("other document") or low.startswith("other requirements")


def _looks_like_document_part(text: str) -> bool:
    low = f" {text.lower()} "
    tokens = (
        "certificate",
        "clearance",
        "transcript",
        "diploma",
        "passport",
        " tor ",
        "form",
        "nbi",
    )
    return any(token in low for token in tokens)


def _core(text: str) -> str:
    value = clean_text(text).strip(" ;.")
    previous = None
    while value != previous:
        previous = value
        value = _QUANTITY.sub("", value).strip()
        value = _RA_NOTE.sub("", value)
        value = _VALIDITY.sub("", value)
        value = _MARRIED_FEMALE.sub("", value)
        value = _FIRST_TIMER.sub("", value)
        value = _ISSUED_BY_PSA.sub("", value)
        value = re.sub(r"\s+", " ", value).strip(" ;,.-")
        value = re.sub(r"\s+or equivalent document\b.*$", "", value, flags=re.I)
        value = re.sub(r"^(?:psa|nso)\s*/\s*(?:psa|nso)\s+", "", value, flags=re.I)
    value = re.sub(r"^psa\s+\d+\s+", "PSA ", value, flags=re.I)
    return value.strip()


def _mentions_other_document(core: str) -> bool:
    low = core.lower()
    if _or_names_another_document(low):
        return True
    if re.search(r"\b(?:divorce|annul|deletion|cenomar|baptismal|non-availability|presumptive)\b", low):
        return True
    families = 0
    if _is_birth(core):
        families += 1
    if _is_nbi(core):
        families += 1
    if _is_tor(core):
        families += 1
    if _is_marriage(core):
        families += 1
    return families > 1


def _is_birth(core: str) -> bool:
    low = core.lower()
    if "non-availability" in low or "consent" in low or "court order" in low:
        return False
    return "certificate of live birth" in low or re.search(r"\bbirth certificate\b", low) is not None


def _or_names_another_document(low: str) -> bool:
    """True when 'or' joins two documents, not a phrase such as 'Philippines or abroad'."""
    simplified = re.sub(r"original or (?:authenticated|photocopy|certified)", "original", low)
    if " or " not in simplified:
        return False
    pieces = re.split(r"\s+or\s+", simplified)
    if len(pieces) != 2:
        return True
    right = pieces[1].strip()
    if right.startswith(("abroad", "in case", "equivalent", "the issuance")):
        return False
    return any(token in right for token in ("certificate", "clearance", "transcript", "diploma", "passport", " tor", "cav"))


def _is_nbi(core: str) -> bool:
    low = core.lower()
    if re.search(r"nbi\s+\d*\s*clearance", low) or "nbi clearance" in low:
        return True
    return "national bureau of investigation" in low and "clearance" in low


def _is_tor(core: str) -> bool:
    low = f" {core.lower()} "
    if "title page" in low:
        return False
    if re.search(r"/\s*tor\b|\btor\s*/", low):
        return False
    if "diploma" in low and "transcript" in low:
        return False
    if "transcript of record" in low:
        return True
    return bool(re.search(r"\btor\b", low))


def _is_marriage(core: str) -> bool:
    low = core.lower()
    if any(word in low for word in ("divorce", "annul", "separation", "widowed", "cenomar", "death certificate", "bachelor")):
        return False
    return "marriage certificate" in low or "marriage contract" in low
