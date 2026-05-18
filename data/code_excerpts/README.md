# Code-excerpt data — local only, not bundled

The `📖 Code excerpt — p.NNN` expander next to each requirement in the
Streamlit UI (Tier 3 UI #14) optionally pulls a short slice of the cited UAE
FLSC 2018 page so designers can verify the rule against the actual code text
without flipping to the PDF.

**This directory is intentionally empty in the public repo.** UAE Civil
Defence regulatory text is not redistributed via this tool. Populate this
directory **locally** to enable the feature:

1. Place per-chapter extracted text files here:
   ```
   data/code_excerpts/ch03.txt   (Means of Egress)
   data/code_excerpts/ch04.txt   (Fire Extinguishers)
   data/code_excerpts/ch05.txt   (Exit Signs)
   data/code_excerpts/ch06.txt   (Emergency Lighting)
   data/code_excerpts/ch07.txt   (EVC)
   data/code_excerpts/ch08.txt   (Fire Alarm)
   data/code_excerpts/ch09.txt   (Fire Protection)
   data/code_excerpts/ch10.txt   (Smoke Control)
   data/code_excerpts/ch11.txt   (LPG)
   ```

2. Each file must use the page-marker format `===== PAGE NNN =====` between
   page boundaries (this is what `pypdf.PdfReader(...).pages[n].extract_text()`
   produces when you wrap each page in that marker).

3. A starter extraction script is `_extracted/` at the parent of the tool
   folder (left over from the audit campaign). Copy or symlink those files
   here, or use the helper:
   ```bash
   python -c "from pypdf import PdfReader; r = PdfReader('UAEFIRECODE_ENG_SEPTEMBER_2018.pdf'); \
              for chap, (s, e) in {3:(235,350),4:(351,382),5:(383,401),6:(402,425),\
                                   7:(426,443),8:(444,522),9:(523,777),10:(778,876),\
                                   11:(877,939)}.items(): \
                  open(f'ch{chap:02d}.txt','w',encoding='utf-8').write(''.join(\
                      f'\\n===== PAGE {p} =====\\n{r.pages[p-1].extract_text() or \"\"}' \
                      for p in range(s, e+1)))"
   ```

If this directory is empty, the excerpt expander simply doesn't render —
all other UI features keep working.

The app also falls back to `../_extracted/chXX.txt` (relative to the python
tool folder) for convenience during local development.
