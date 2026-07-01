# Cover letter — Resubmission to *SoftwareX*

**Manuscript (previous):** SOFTX-D-26-00687
**Title:** PhysioFlow: an open-source interactive platform for crop ecophysiology and agronomic data analysis with statistical and experimental-design guard-rails
**Corresponding author:** Leandro Rodrigues da Silva Souza (CEAGRE / Instituto Federal Goiano)

---

Dear Dr. Nikolaos Kourkoumelis, Editor-in-Chief,

Thank you for evaluating our submission and for the clear guidance in your decision letter of 24 June 2026. We have revised the manuscript and the software to address each of the points you raised, and we respectfully submit the revised version for consideration. Below we respond point by point.

## 1. Public repository (software accessibility)

You noted that the repository listed in our metadata table was not publicly accessible, and that *SoftwareX* reviews the code itself.

**Addressed.** The repository is now **public** and openly available for review:

- Code / repository (C2): https://github.com/ML-Carbon-Project/physioFlow
- Developer documentation / manual (C7): https://github.com/ML-Carbon-Project/physioFlow/tree/main/docs

Both links in the Metadata Table (Table 1) have been re-verified as publicly reachable. The repository contains the full source, the test suite, the public sample datasets used in the paper, and the trilingual documentation.

## 2. Relationship to ChamberFlux and distinct contribution

You observed that PhysioFlow shares much of its engine with our closely related ChamberFlux work (also under consideration) and asked us to state that relationship openly and to explain what PhysioFlow contributes as separate software.

**Addressed.** We added an explicit paragraph, *"Relationship to ChamberFlux,"* at the end of the *Motivation and significance* section. It states plainly that the two platforms share the same session-state Streamlit architecture and the core cleaning, EDA, guard-rail, modelling and geospatial primitives, and then delimits what is genuinely new in PhysioFlow:

1. an **ecophysiology data schema** and replicate handling for IRGA, chlorophyll-fluorometer and ceptometer exports;
2. **domain-specific guard-rails** for the mutually derived physiological indices (e.g. WUE, A/Ci, Ci/Ca);
3. most importantly, a **formal experimental-design module** (CRD, RCBD, factorial, Latin square, split-plot, strip-plot, nested, ANCOVA and dose-response, cross-validated against R) together with an **automatic data-profile** that makes the tool dataset-agnostic beyond ecophysiology.

To substantiate that these additions make PhysioFlow useful as independent software, we also added a second illustrative example (Section *Datasets beyond ecophysiology*) in which the generic profile analyses two public, non-ecophysiology datasets without any code change: the classical **Yates oats split-plot**, whose ANOVA reproduces R's `nlme::Oats` to the decimal in all three strata (new Table 2), and the **Palmer penguins** biology dataset (EDA and multi-class classification). We believe the experimental-design engine and the domain-agnostic profile give PhysioFlow a scope and audience distinct from ChamberFlux, while the shared lineage is now fully disclosed.

## 3. Compliance with the Guide for Authors

**Word limit (3,000 words).** The main text has been reduced to **under 3,000 words** by tightening the *Software description*, *Motivation*, *Impact* and *Conclusions* sections (condensing method enumerations without removing substance), while still accommodating the new ChamberFlux paragraph and the second example.

**Software documentation and Metadata Table.** The Metadata Table (Table 1) is present and complete (C1–C8). The repository documentation (`/docs`) includes an architecture description, a data dictionary, deployment and contributing guides, and full user manuals in PT/EN/ES.

**Figures and display media.** Figures were reviewed for necessity and legibility; captions were kept concise. The architecture figure was updated to reflect the current nine-page application.

**Formatting and references.** The manuscript follows the `elsarticle` template. All author ORCID identifiers were added. We corrected the reference list (including full author metadata for the cited software papers) and removed internal editorial notes.

---

We are grateful for the opportunity to resubmit and believe the revised manuscript now closely follows the Guide for Authors. We remain at your disposal for any further clarification.

Kind regards,

Leandro Rodrigues da Silva Souza, on behalf of all authors
CEAGRE / Instituto Federal Goiano — leandrorodrigues.s@gmail.com
