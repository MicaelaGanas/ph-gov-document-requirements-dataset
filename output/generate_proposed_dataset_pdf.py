#!/usr/bin/env python3
"""Generate Proposed Dataset PDF for research submission."""

from __future__ import annotations

from pathlib import Path

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Proposed Dataset — PH-GovDocPath</title>
<style>
  @page { size: A4; margin: 20mm 18mm; }
  body {
    font-family: "Segoe UI", Calibri, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.45;
    color: #1a1a1a;
    max-width: 100%;
  }
  h1 {
    font-size: 16pt;
    border-bottom: 2px solid #1e3a5f;
    padding-bottom: 6px;
    margin-top: 0;
    color: #1e3a5f;
  }
  h2 {
    font-size: 12pt;
    margin-top: 18px;
    margin-bottom: 6px;
    color: #1e3a5f;
  }
  h3 { font-size: 11pt; margin-top: 12px; margin-bottom: 4px; }
  p { margin: 6px 0; text-align: justify; }
  ul { margin: 6px 0 10px 20px; }
  li { margin-bottom: 4px; }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 9.5pt;
    margin: 10px 0 14px 0;
  }
  th, td {
    border: 1px solid #bbb;
    padding: 5px 7px;
    text-align: left;
    vertical-align: top;
  }
  th { background: #eef2f7; font-weight: 600; }
  .subtitle {
    font-size: 10.5pt;
    color: #444;
    margin-bottom: 16px;
  }
  .meta { font-size: 9.5pt; color: #555; margin-bottom: 20px; }
  .note {
    background: #f7f9fc;
    border-left: 3px solid #1e3a5f;
    padding: 8px 12px;
    margin: 12px 0;
    font-size: 10pt;
  }
  code { font-size: 9pt; background: #f0f0f0; padding: 1px 4px; }
</style>
</head>
<body>

<h1>A. Proposed Dataset</h1>
<p class="subtitle"><strong>Research Project:</strong> Intelligent Planning and Geospatial Mapping of Document Acquisition Routes for Philippine Government IDs and Official Documents</p>
<p class="meta">Dataset working title: <strong>PH-GovDocPath Dataset</strong> &nbsp;|&nbsp; Generated from official .gov.ph sources</p>

<h2>Proposed Dataset Name</h2>
<p><strong>Philippine Government Document Requirements and Acquisition Pathways Dataset (PH-GovDocPath Dataset)</strong></p>

<h2>Dataset Description</h2>
<p>This dataset represents structured information about <strong>Philippine government services, document requirements, office locations, and document dependencies</strong> needed to obtain official government IDs and certificates (e.g., passport, National ID, NBI clearance, driver's license, professional license, SSS/PhilHealth/Pag-IBIG membership, voter registration, and business permits).</p>

<p>The dataset will contain:</p>
<ul>
  <li><strong>Government services</strong> — agency, service name, target document, transaction type, fees, processing time, and application method</li>
  <li><strong>Requirements</strong> — required documents, acceptable IDs, supporting/conditional documents, and application procedures</li>
  <li><strong>Government offices</strong> — office name, type, address, and contact details (latitude/longitude reserved for future geocoding)</li>
  <li><strong>Service locations</strong> — which services can be applied for at which offices</li>
  <li><strong>Document dependencies</strong> — prerequisite relationships between target documents and required documents (required, conditional, or alternative)</li>
</ul>

<p><strong>Relevance to the study:</strong> The proposed research focuses on intelligent planning and geospatial mapping of document acquisition routes. This dataset supports that goal by: (1) modeling what documents are needed for each government service; (2) modeling dependencies between documents; (3) linking services to application locations; (4) enabling association rule mining to discover common document combinations; and (5) supporting future route/path planning across agencies and offices.</p>

<p>All data is collected from <strong>official Philippine government websites and Citizen's Charters</strong>, not from third-party blogs or ready-made repositories.</p>

<h2>Data Source</h2>
<p>Data will be collected <strong>only from official Philippine government websites</strong> (.gov.ph domains) and official Citizen's Charters. No Kaggle, UCI, Wikipedia, or unofficial commercial sources will be used as primary data.</p>

<table>
  <tr><th>Agency</th><th>Website</th><th>Official URL(s)</th></tr>
  <tr><td>PhilSys / PSA</td><td>philsys.gov.ph</td><td>https://philsys.gov.ph/registration-process/ ; https://philsys.gov.ph/supporting-documents/</td></tr>
  <tr><td>PSA Civil Registration</td><td>psa.gov.ph</td><td>https://psa.gov.ph/civilregistration</td></tr>
  <tr><td>DFA</td><td>consular.dfa.gov.ph</td><td>https://consular.dfa.gov.ph/passport/10-passport/61-passport-requirements-new-adult ; https://consular.dfa.gov.ph/valid-ids-for-passport-application/</td></tr>
  <tr><td>NBI</td><td>nbi.gov.ph</td><td>https://nbi.gov.ph/citizens-charter/nbi-clearance-application/ ; https://nbi.gov.ph/how-to-apply-nbi-clearance/</td></tr>
  <tr><td>LTO</td><td>lto.gov.ph</td><td>https://lto.gov.ph/ ; https://portal.lto.gov.ph/</td></tr>
  <tr><td>PRC</td><td>prc.gov.ph</td><td>https://www.prc.gov.ph/list-of-requirements</td></tr>
  <tr><td>COMELEC</td><td>comelec.gov.ph</td><td>https://www.comelec.gov.ph/?r=VoterRegistration/RegistrationProcedures</td></tr>
  <tr><td>DTI</td><td>bnrs.dti.gov.ph</td><td>https://bnrs.dti.gov.ph/</td></tr>
  <tr><td>SSS</td><td>sss.gov.ph</td><td>https://www.sss.gov.ph/become-an-sss-member/ ; https://www.sss.gov.ph/list-of-valid-ids/</td></tr>
  <tr><td>PhilHealth</td><td>philhealth.gov.ph</td><td>https://www.philhealth.gov.ph/members/formal/registration.php</td></tr>
  <tr><td>Pag-IBIG</td><td>pagibigfund.gov.ph</td><td>https://www.pagibigfund.gov.ph/membership/</td></tr>
  <tr><td>GSIS</td><td>gsis.gov.ph</td><td>https://www.gsis.gov.ph/</td></tr>
  <tr><td>Davao City LGU</td><td>davaocity.gov.ph</td><td>https://davaocity.gov.ph/services/processing-of-business-permits/</td></tr>
</table>

<p>Every record preserves the <strong>original source URL</strong> and <strong>date verified</strong> (<code>last_verified</code>).</p>

<h2>Data Collection Method</h2>
<p><strong>Primary method: Web scraping</strong> using a Python-based data collection pipeline.</p>
<ol>
  <li><strong>HTTP requests</strong> (requests, cloudscraper) to fetch official HTML pages</li>
  <li><strong>HTML parsing</strong> (BeautifulSoup, lxml) to extract services, requirements, fees, procedures, and office information</li>
  <li><strong>Playwright</strong> (headless browser) only when necessary for Cloudflare-protected pages</li>
  <li><strong>Post-processing</strong> — deduplication, normalization, validation, export to five normalized CSV tables</li>
  <li><strong>Manual verification / seeding</strong> only when a site blocks access; labeled <code>scrape_status = seed</code> or <code>blocked</code></li>
</ol>

<p><strong>Ethical constraints:</strong> Respect robots.txt and rate limits; no personal information; no fabricated fees or coordinates; empty values when unavailable.</p>
<p><strong>Not used:</strong> surveys, Kaggle/UCI datasets, or unofficial blogs as primary sources.</p>

<h2>Expected Number of Records</h2>
<p>The final dataset contains <strong>well over 500 records</strong>, organized across five related tables:</p>

<table>
  <tr><th>Table</th><th>Records</th></tr>
  <tr><td>Government services</td><td>36</td></tr>
  <tr><td>Requirements</td><td>757</td></tr>
  <tr><td>Government offices</td><td>13</td></tr>
  <tr><td>Service locations</td><td>13</td></tr>
  <tr><td>Document dependencies</td><td>679</td></tr>
  <tr><td><strong>Total data objects</strong></td><td><strong>~1,498</strong></td></tr>
</table>

<p>For data mining, the primary requirement-level dataset has <strong>757 records</strong>, with <strong>727 live-scraped (success)</strong> and <strong>661 document-focused success records</strong>. This exceeds the minimum of 500 records. Ready-made Kaggle/UCI datasets are <strong>not</strong> used.</p>

<div class="note">
  <strong>Data quality note:</strong> Approximately 96% of requirement records were live-scraped from official sources. Remaining rows are marked <code>seed</code> or <code>blocked</code> due to Cloudflare/WAF restrictions and are excluded from mining analysis unless manually verified.
</div>

<h2>Proposed Features / Attributes</h2>

<h3>1. government_services.csv</h3>
<p><code>service_id</code>, <code>agency</code>, <code>agency_acronym</code>, <code>service_name</code>, <code>target_document</code>, <code>transaction_type</code>, <code>applicant_type</code>, <code>application_method</code>, <code>appointment_required</code>, <code>processing_time</code>, <code>fee</code>, <code>source_url</code>, <code>source_title</code>, <code>last_verified</code>, <code>scrape_status</code></p>

<h3>2. requirements.csv</h3>
<p><code>requirement_id</code>, <code>service_id</code>, <code>requirement_name</code>, <code>requirement_name_normalized</code>, <code>requirement_type</code>, <code>requirement_role</code>, <code>conditional</code>, <code>condition</code>, <code>issuing_agency</code>, <code>document_format</code>, <code>quantity</code>, <code>source_url</code>, <code>source_section</code>, <code>requirement_description</code>, <code>last_verified</code>, <code>scrape_status</code></p>

<h3>3. government_offices.csv</h3>
<p><code>office_id</code>, <code>agency</code>, <code>agency_acronym</code>, <code>office_name</code>, <code>office_type</code>, <code>region</code>, <code>province</code>, <code>city</code>, <code>address</code>, <code>latitude</code>, <code>longitude</code>, <code>contact_number</code>, <code>source_url</code>, <code>last_verified</code></p>

<h3>4. service_locations.csv</h3>
<p><code>service_location_id</code>, <code>service_id</code>, <code>office_id</code>, <code>service_available</code>, <code>application_method</code>, <code>appointment_required</code>, <code>processing_time</code>, <code>fee</code>, <code>source_url</code>, <code>last_verified</code></p>

<h3>5. document_dependencies.csv</h3>
<p><code>dependency_id</code>, <code>service_id</code>, <code>target_document</code>, <code>required_document</code>, <code>required_document_normalized</code>, <code>relationship_type</code>, <code>condition</code>, <code>target_agency</code>, <code>required_document_agency</code>, <code>source_url</code>, <code>last_verified</code></p>

<p><strong>Key derived attributes:</strong> <code>relationship_type</code> (required, conditional, alternative); <code>requirement_role</code> (required_document, acceptable_id, supporting_document, procedure); <code>scrape_status</code> (success, partial, seed, blocked).</p>

<h2>Proposed Data Mining Technique</h2>
<p><strong>Primary technique: Association Rule Mining (ARM)</strong></p>

<p><strong>Justification:</strong> Document acquisition involves discovering which documents frequently appear together across government services (e.g., PSA birth certificate + valid ID for passport). ARM treats each government service as a transaction and documents as items. Rules such as {PSA Birth Certificate, Valid ID} → {Passport Application} reveal common prerequisite patterns and support intelligent planning of document acquisition sequences.</p>

<p><strong>Secondary technique (optional):</strong> Clustering or graph-based path planning for office locations once coordinates are geocoded.</p>

<h2>Proposed Algorithms</h2>
<p>For Association Rule Mining:</p>
<ol>
  <li><strong>Apriori Algorithm</strong> — classic approach to find frequent itemsets and generate association rules</li>
  <li><strong>FP-Growth (Frequent Pattern Growth)</strong> — efficient FP-tree structure for larger requirement sets</li>
  <li><strong>Eclat Algorithm</strong> — vertical data format with depth-first search for sparse matrices</li>
</ol>

<h2>Proposed Performance Metrics</h2>
<p>For Association Rule Mining:</p>
<ol>
  <li><strong>Support</strong> — proportion of services containing a document itemset; measures how common a pattern is</li>
  <li><strong>Confidence</strong> — conditional probability that document B is required given document A; measures rule reliability</li>
  <li><strong>Lift</strong> — ratio of observed co-occurrence to expected; values &gt; 1 indicate meaningful positive association</li>
</ol>

<p style="margin-top:24px; font-size:9pt; color:#666;">Repository: ph-gov-document-requirements-dataset &nbsp;|&nbsp; Output: data/final/ (5 CSV files)</p>

</body>
</html>
"""


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    html_path = out_dir / "Proposed_Dataset.html"
    pdf_path = out_dir / "Proposed_Dataset.pdf"

    html_path.write_text(HTML, encoding="utf-8")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_path.as_uri(), wait_until="networkidle")
        page.pdf(
            path=str(pdf_path),
            format="A4",
            margin={"top": "18mm", "right": "16mm", "bottom": "18mm", "left": "16mm"},
            print_background=True,
        )
        browser.close()

    print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    main()
