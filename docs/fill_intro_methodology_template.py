"""Map PH_GovDocPath_Manuscript content into Introduction_and_Methodology_Template.docx."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.shared import Inches
from docx.text.paragraph import Paragraph

TEMPLATE = Path(r"C:\Users\Mika\Downloads\Introduction_and_Methodology_Template.docx")
MANUSCRIPT = Path(r"C:\Users\Mika\Downloads\PH_GovDocPath_Manuscript.docx")
OUTPUT = Path(r"C:\Users\Mika\Downloads\PH_GovDocPath_Introduction_and_Methodology.docx")
OUTPUT_FALLBACK = Path(
    r"C:\Users\Mika\Downloads\PH_GovDocPath_Introduction_and_Methodology_with_figures.docx"
)
FIGURES_DIR = Path(__file__).resolve().parent / "govdocpath_figures"

FIGURE_INSERTS = (
    # (anchor paragraph index, image file, caption)
    (34, "image1.png", "Fig. 1. CRISP-DM process for PH-GovDocPath."),
    (37, "image2.png", "Fig. 2. System architecture of the study."),
    (53, "image3.png", "Fig. 3. Transaction encoding of requirements."),
    (70, "image4.png", "Fig. 4. Route built from a kept rule."),
)

# Paragraph index -> new text (empty string clears guidance placeholders)
REPLACEMENTS: dict[int, str] = {
    0: (
        "Intelligent Planning and Geospatial Mapping of Document Acquisition "
        "Routes for Philippine Government IDs and Official Documents"
    ),
    1: (
        "Alyssa Nicole Argoncillo, Micaela Ysabel Ganas, and Julliana Louise Onor\n"
        "School of Engineering and Information Technology, Mapúa Malayan Colleges Mindanao\n"
        "Davao City, Philippines\n"
        "myganas@mcm.edu.ph"
    ),
    3: (
        "Philippine government identification documents and certificates are issued by separate "
        "agencies. Each agency publishes its own requirements, fees, processing time, and office "
        "locations, commonly in a Citizen’s Charter required by Republic Act No. 11032. An applicant "
        "who needs a passport, a Philippine Identification System record, a clearance, or a professional "
        "license must discover which documents are jointly required, which documents are alternatives, "
        "and which offices to visit and in what order. This study specifies that task as association rule "
        "mining on the Philippine Government Document Requirements and Acquisition Pathways dataset "
        "(PH-GovDocPath). Official .gov.ph pages and Citizen’s Charters supply services, requirements, "
        "and offices; OpenStreetMap supplies coordinates only when a published address resolves. Each "
        "service is one transaction; each jointly required document is one item. Apriori, FP-Growth, "
        "and Eclat mine the same transaction matrix; support, confidence, and lift evaluate the rules. "
        "A rule is mapped as a route only when lift shows a positive association and the current charter "
        "still states the requirement. Data preparation is implemented as an automated pipeline: five "
        "linked tables, 907 requirement rows across 41 services (34 successfully scraped), 798 dependency "
        "rows, and ten Davao City offices with geocoded coordinates and exterior photos. Full algorithm "
        "comparison and ranked rules will be reported after mining. The study stores no applicant records "
        "and does not estimate approval probability."
    ),
    4: (
        "Index Terms—Association rule mining, Philippine government documents, Apriori algorithm, "
        "FP-Growth, Eclat, CRISP-DM, geospatial mapping, Citizen’s Charter"
    ),
    6: "",  # guidance
    9: (
        "Obtaining a Philippine government identification document is a sequence of documents and office "
        "visits. A birth certificate, a national identification record, a clearance, a license, and a "
        "passport are issued by different authorities. The applicant must learn each authority’s "
        "requirement list and the order in which those requirements can be satisfied. The list and the "
        "office are published, but separately, and each publication covers one agency’s service."
    ),
    10: (
        "Republic Act No. 11032 requires every covered agency and local government unit to post a current "
        "Citizen’s Charter with requirements, procedure, responsible officer, maximum time, fees, and "
        "complaint procedure. Republic Act No. 11055 established PhilSys and directed agencies to honor "
        "the PhilSys number as proof of identity once authenticated. Official pages already show cross-agency "
        "dependencies—for example, PhilSys supporting documents, passport or UMID as alternatives, and NBI "
        "clearance requiring two government-issued IDs. PH-GovDocPath covers civil-registry and passport "
        "services, PhilSys, NBI, LTO, PRC, COMELEC, DTI, SSS, PhilHealth, Pag-IBIG, GSIS, and Davao City "
        "local permits. Primary data are limited to official .gov.ph domains and Citizen’s Charters; "
        "OpenStreetMap geocoding is used only for published addresses. Ready-made repositories and unofficial "
        "blogs are excluded."
    ),
    11: (
        "Prior work describes single services (Citizen’s Charters, public-service models), mines frequent "
        "itemsets in retail-like baskets, or measures spatial access to facilities. What remains is one "
        "Philippine dataset linking services, jointly required documents, alternatives, and office locations; "
        "a fair comparison of Apriori, FP-Growth, and Eclat on that matrix; and routes drawn only after "
        "charter verification."
    ),
    8: "",  # guidance
    13: "",  # guidance
    14: (
        "Applicants cannot read one charter and recover a full acquisition path. Passport requirements do "
        "not include the civil registrar’s charter; requirement pages do not give issuing-office coordinates. "
        "Alternatives cause error if all acceptable IDs are placed in one basket. Office locations are "
        "published apart from requirement lists, and missing coordinates cannot be invented."
    ),
    15: (
        "The study addresses the absence of one official transaction dataset linking services, joint "
        "requirements, alternatives, and offices, and the absence of a checked association-rule procedure "
        "that turns recurring patterns into sequences and routes while preserving charter wording and "
        "comparing the three miners on the same matrix."
    ),
    17: "",  # guidance
    18: (
        "PH-GovDocPath (Philippine Government Document Requirements and Acquisition Pathways) is built from "
        "official .gov.ph sources via automated scraping and manual charter reading when sites block access. "
        "The unit of analysis is the government service. The working release contains five normalized CSV "
        "tables with more than 500 analytical records (907 requirement rows, 798 dependency rows, 41 services). "
        "It differs from prohibited repository datasets because every row retains source_url and last_verified. "
        "The intended contribution is cross-agency document patterns, algorithm comparison on a sparse "
        "requirement matrix, and geospatial routes for rules the charter still supports."
    ),
    20: "",  # guidance
    21: (
        "General Objective: To perform association rule mining on PH-GovDocPath to discover frequent "
        "document-requirement patterns, compare Apriori, FP-Growth, and Eclat using support, confidence, "
        "and lift, and link charter-verified rules to office locations for route planning."
    ),
    23: (
        "1) To describe PH-GovDocPath using descriptive statistics and data-quality indicators "
        "(scrape_status, geocode_status, joint versus alternative encoding) and to document issues that "
        "affect mining."
    ),
    24: (
        "2) To encode each service as one transaction with jointly required documents as items, to compare "
        "primary and sensitivity matrices, and to evaluate Apriori, FP-Growth, and Eclat at the same minimum "
        "support and confidence."
    ),
    25: (
        "3) To assess rules with support, confidence, and lift; to compare algorithms on itemset overlap, "
        "runtime, and Jaccard similarity; and to accept rules for routing only when the current charter "
        "confirms the consequent."
    ),
    26: (
        "4) To identify the strongest rules (lift and confidence thresholds, cross-algorithm agreement) and "
        "to map accepted rules to document sequences and OpenStreetMap routes among offices with retrieved "
        "coordinates."
    ),
    28: "",  # guidance
    29: (
        "The study covers the agencies named above for pages retrievable from official sources during "
        "collection (2025–2026). It does not cover every Philippine document, rank agencies, change fees, "
        "or predict approval. Mining uses association rules only—not classification. Geospatial deployment "
        "is implemented first for Davao City (ten offices); national office enrichment continues. Results "
        "apply only to the published text at the stored retrieval dates."
    ),
    31: "",  # guidance
    34: (
        "The design follows CRISP-DM: business understanding, data understanding, data preparation, "
        "modeling, evaluation, and deployment. The data mining technique is association rule mining "
        "(exploratory and comparative). Each government service is a transaction; jointly required documents "
        "are items. Alternatives are excluded from the primary basket. The design answers how official text "
        "becomes a matrix, which patterns the three algorithms recover, and which patterns become routes."
    ),
    37: (
        "Dataset name: PH-GovDocPath. Unit of analysis: one government service (transaction). Current "
        "record counts: 41 services in government_services.csv; 907 rows in requirements.csv; 798 rows in "
        "document_dependencies.csv; 22 offices in government_offices.csv (10 Davao offices fully geocoded with "
        "exterior images); 27 service–office links in service_locations.csv. Observation period: page "
        "retrieval dates stored in last_verified. Analytical purpose: discover document co-occurrence across "
        "services and connect verified rules to office coordinates. There is no supervised target variable."
    ),
    40: (
        "Sources: Philippine Statistics Authority (psa.gov.ph, philsys.gov.ph); Department of Foreign Affairs "
        "consular pages (consular.dfa.gov.ph); National Bureau of Investigation (nbi.gov.ph); Land "
        "Transportation Office (lto.gov.ph); Professional Regulation Commission (prc.gov.ph); Commission on "
        "Elections (comelec.gov.ph); Department of Trade and Industry BNRS (bnrs.dti.gov.ph); Social Security "
        "System (sss.gov.ph); PhilHealth; Pag-IBIG; GSIS; Davao City LGU (davaocity.gov.ph). Geocoding: "
        "OpenStreetMap Nominatim (https://nominatim.openstreetmap.org)."
    ),
    41: (
        "Collection uses HTTP requests and HTML parsing; Playwright (Chromium) is used when Cloudflare or "
        "JavaScript blocks plain requests. Duplicate requirements are removed in cleaning; document names are "
        "normalized via a synonym list. Failed requests retain scrape_status (success, partial, seed, blocked) "
        "with source_url. Office addresses are geocoded at one request per second; coordinates are stored only "
        "on successful match (geocode_status). Exterior office images prefer official .gov.ph URLs, then "
        "curated web links, then Bing image search with quality filters. The pipeline is reproduced with "
        "python build.py in the project repository ph-gov-document-requirements-dataset."
    ),
    44: (
        "service_id: nominal; identifier; stable key for one government service."
    ),
    45: (
        "requirement_name / requirement_name_normalized: nominal; predictor (item label); original charter "
        "wording and canonical label for mining joins."
    ),
    46: (
        "requirement_role: nominal; encoding control; values include required_document, acceptable_id, "
        "supporting_document, procedure—only document roles enter the primary transaction basket. "
        "relationship_type in document_dependencies.csv: required, conditional, alternative. "
        "latitude, longitude: numeric; location; from Nominatim only. scrape_status: nominal; quality flag. "
        "source_url, last_verified: provenance for charter re-check."
    ),
    49: (
        "1) Data validation and cleaning: type checks on CSV schemas; foreign-key checks between services, "
        "requirements, offices, and dependencies; duplicate detection on requirement rows; exclusion of "
        "procedure and fee lines from the primary mining filter when they are not document items; "
        "scrape_status filtering (success recommended for mining)."
    ),
    50: (
        "2) Missing values: attributes not stated on the official page remain empty—fees, processing times, "
        "and coordinates are never imputed. Mining uses complete-case services for the transaction matrix "
        "(services with parseable requirement lists only)."
    ),
    51: (
        "3) Outliers and anomalies: rare document names are kept when charter-backed; scraped noise (e.g., "
        "payment lines mis-tagged as documents) is removed via requirement_role and manual synonym review."
    ),
    52: (
        "4) Categorical encoding: documents are binary items in each transaction (present/absent); no one-hot "
        "of a single target because ARM is unsupervised at the rule level."
    ),
    53: (
        "5) Feature scaling: not applied; ARM uses binary item presence. A secondary sensitivity matrix "
        "expands alternative ID groups for comparison only."
    ),
    56: (
        "Association rule mining uses the full service population as the transaction set (no random train–test "
        "split for itemsets). Minimum support and minimum confidence are set after inspecting item-frequency "
        "distributions. Algorithm comparison is fair: one input file, one support threshold, one confidence "
        "threshold, three SPMF runs; runtime reported as median of three runs on the same machine. Charter "
        "verification is held out logically: rules are checked against source pages before route deployment."
    ),
    59: (
        "Algorithm 1: Apriori. Justification: classical baseline for frequent itemsets and rule generation. "
        "Parameters: minimum support and minimum confidence (values reported with results)."
    ),
    60: (
        "Algorithm 2: FP-Growth. Justification: FP-tree avoids candidate explosion for larger requirement "
        "catalogues. Parameters: same support and confidence as Apriori."
    ),
    61: (
        "Algorithm 3: Eclat. Justification: vertical tid lists suit sparse service–document matrices. "
        "Parameters: same support and confidence as Apriori and FP-Growth."
    ),
    64: (
        "Metric 1: Support. Proportion of services containing an itemset; higher indicates a more common "
        "pattern across services."
    ),
    65: (
        "Metric 2: Confidence. For rule X → Y, the share of services with X that also include Y; higher "
        "indicates a more reliable directional rule."
    ),
    66: (
        "Metric 3: Lift. Ratio of observed co-occurrence to independence; values greater than 1 indicate "
        "meaningful positive association; rules at or below 1 are excluded from route construction."
    ),
    67: "",  # optional suggestion line
    70: (
        "The best rule set is selected by thresholding support, confidence, and lift, then ranking survivors "
        "by lift and confidence. Primary metric for “strongest rule”: lift (then confidence, then support). "
        "Cross-algorithm agreement (identical frequent itemsets, Jaccard overlap ≈ 1) is required before "
        "deployment. Tie-breaking favors rules confirmed by manual charter reading at the stored source_url."
    ),
    73: (
        "Python 3, pandas, requests, BeautifulSoup, Playwright, OpenStreetMap Nominatim API, SPMF (Apriori, "
        "FP-Growth, Eclat), Git repository with build.py pipeline, random seeds fixed for any stochastic step, "
        "data dictionary in README.md and processing/schemas.py."
    ),
    76: (
        "Only publicly published government pages and OpenStreetMap are used. No applicant personal data are "
        "collected. Scraping respects robots.txt and request delays. Blocked sites are marked seed/blocked rather "
        "than replaced with unofficial copies. Charter quotations are minimal and always linked to source_url "
        "and retrieval date for reproducible verification."
    ),
    78: "",  # guidance
    79: (
        "[1] R. Agrawal, T. Imieliński, and A. Swami, “Mining association rules between sets of items in large "
        "databases,” in Proc. ACM SIGMOD, 1993, pp. 207–216, doi: 10.1145/170035.170072."
    ),
    80: (
        "[2] J. Han, M. Kamber, and J. Pei, Data Mining: Concepts and Techniques, 3rd ed. Burlington, MA, USA: "
        "Morgan Kaufmann, 2012."
    ),
    81: (
        "[3] Republic of the Philippines, “Republic Act No. 11032,” Lawphil.net. Accessed: Aug. 27, 2026. "
        "[Online]. Available: https://lawphil.net/statutes/repacts/ra2018/ra_11032_2018.html"
    ),
    82: (
        "[4] P. Fournier-Viger et al., “The SPMF open-source data mining library,” in Proc. ECML PKDD, 2016, "
        "pp. 36–40, doi: 10.1007/978-3-319-46131-1_8."
    ),
    83: (
        "[5] Philippine Statistics Authority, “Supporting documents,” PhilSys. Accessed: Aug. 27, 2026. "
        "[Online]. Available: https://philsys.gov.ph/supporting-documents/"
    ),
}


def _is_template_boilerplate(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if t.startswith("[Guidance:"):
        return True
    prefixes = (
        "[Specific and Descriptive",
        "[First Author",
        "[Write one self-contained",
        "[Paragraph ",
        "[State the main purpose",
        "[Describe the proposed",
        "[Explain the overall",
        "[Provide the dataset",
        "[Source name and URL",
        "[Collection procedure",
        "Attribute 1:",
        "Attribute 2:",
        "Attribute 3:",
        "[State the split ratio",
        "Algorithm 1: [Name]",
        "Metric 1: [Name]",
        "[Describe the comparison matrix",
        "[Example: Python version",
        "[Describe the ethical",
        "Suggested metric families",
        "[5] Name of Dataset Owner",
    )
    return any(t.startswith(p) for p in prefixes)


def extract_figures_from_manuscript() -> None:
    """Copy embedded PNGs from the full manuscript into docs/govdocpath_figures/."""
    if not MANUSCRIPT.is_file():
        raise SystemExit(f"Manuscript not found (needed for figures): {MANUSCRIPT}")
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(MANUSCRIPT) as zf:
        for name in zf.namelist():
            if not name.startswith("word/media/"):
                continue
            if not name.lower().endswith((".png", ".jpg", ".jpeg", ".emf")):
                continue
            dest = FIGURES_DIR / Path(name).name
            dest.write_bytes(zf.read(name))
    print(f"Extracted figures to {FIGURES_DIR}")


def _insert_paragraph_after(paragraph: Paragraph) -> Paragraph:
    new_p = OxmlElement("w:p")
    paragraph._element.addnext(new_p)
    return Paragraph(new_p, paragraph._parent)


def _add_centered_figure_after(anchor: Paragraph, image_path: Path, caption: str, width_in: float = 6.2) -> Paragraph:
    pic_p = _insert_paragraph_after(anchor)
    pic_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pic_p.add_run().add_picture(str(image_path), width=Inches(width_in))
    cap_p = _insert_paragraph_after(pic_p)
    cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap_p.add_run(caption)
    return cap_p


def insert_figures(doc: Document) -> None:
    """Insert CRISP-DM and architecture figures from the original manuscript."""
    extract_figures_from_manuscript()
    # Insert from bottom to top so paragraph indices stay valid.
    for anchor_idx, image_name, caption in reversed(FIGURE_INSERTS):
        image_path = FIGURES_DIR / image_name
        if not image_path.is_file():
            raise SystemExit(f"Missing figure file: {image_path}")
        if anchor_idx >= len(doc.paragraphs):
            raise SystemExit(f"Anchor paragraph {anchor_idx} out of range")
        _add_centered_figure_after(doc.paragraphs[anchor_idx], image_path, caption)
    print(f"Inserted {len(FIGURE_INSERTS)} figures")


def main() -> None:
    if not TEMPLATE.is_file():
        raise SystemExit(f"Template not found: {TEMPLATE}")

    out_path = OUTPUT
    try:
        shutil.copy2(TEMPLATE, out_path)
    except OSError:
        out_path = OUTPUT_FALLBACK
        shutil.copy2(TEMPLATE, out_path)
        print(f"(Original output locked; writing to {out_path.name})")
    doc = Document(out_path)

    for idx, text in REPLACEMENTS.items():
        if idx >= len(doc.paragraphs):
            continue
        doc.paragraphs[idx].text = text

    for p in doc.paragraphs:
        if _is_template_boilerplate(p.text):
            p.text = ""

    insert_figures(doc)

    doc.save(out_path)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
