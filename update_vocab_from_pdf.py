import re
from pathlib import Path

html_path = Path(r"c:/REEF/code projects/JLPT N2 Flashcards/n2_flashcards.html")
pdf_path = Path(r"c:/REEF/code projects/JLPT N2 Flashcards/pdf_vocab_extract.txt")

html_text = html_path.read_text(encoding="utf-8")

m = re.search(r"(const vocab = \[)(.*?)(\n\];)", html_text, re.S)
if not m:
    raise SystemExit("Could not find vocab array")

array_content = m.group(2)
obj_pattern = re.compile(r'{kanji:"([^"]*)",reading:"([^"]*)",english:"([^"]*)",pos:"([^"]*)",lesson:(\d+)}')
objects = list(obj_pattern.finditer(array_content))

# Parse PDF vocabulary file into a lookup keyed by (kanji, reading, lesson is ignored)
lookup = {}
for line in pdf_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line:
        continue
    if line.startswith('Copyright') or line.startswith('第だい') or line.startswith('Lesson'):
        continue
    if not re.match(r'^\d+\.', line):
        continue

    # Extract the prefix like '1.える' or '10.ジャーナリスト'
    prefix, _, rest = line.partition('.')
    # The first numeric token is for ordering only; after the dot is the reading token.
    if not prefix.isdigit():
        continue

    # Split into tokens after the initial number prefix
    tokens = rest.split()
    if not tokens:
        continue

    # The reading is the first token after the number prefix
    reading = tokens[0]

    # Find the part-of-speech start
    pos_idx = None
    for i, tok in enumerate(tokens[1:], start=1):
        if re.match(r'^[A-Za-z.\/-]+$', tok):
            pos_idx = i
            break

    if pos_idx is None:
        continue

    japanese_tokens = tokens[1:pos_idx]
    kanji = japanese_tokens[0] if japanese_tokens else reading
    english = ' '.join(tokens[pos_idx+1:]).strip()

    # Clean obvious OCR artifacts from the extracted text.
    english = english.replace('  ', ' ')
    english = re.sub(r'\s+', ' ', english)
    english = english.replace(' / /', ' /').replace('/ /', '/')
    english = english.replace('（', '(').replace('）', ')')
    english = english.replace('(a week consisting of 3 Japanese national holidays at the end of April and the beginning of May, in which most people have about a week off from work or school.)', 'Golden Week (a week consisting of 3 Japanese national holidays at the end of April and the beginning of May, in which most people have about a week off from work or school).')

    if kanji and reading:
        lookup[(kanji, reading)] = english
        # also allow reading-only fallback for kana-only entries
        lookup[(reading, reading)] = english

# Replace the english values in the array content with values from the PDF
updated_parts = []
last_end = 0
for obj in objects:
    full_match = obj.group(0)
    kanji, reading, old_english, pos, lesson = obj.groups()
    new_english = lookup.get((kanji, reading), lookup.get((reading, reading), old_english))
    new_obj = f'{{kanji:"{kanji}",reading:"{reading}",english:"{new_english}",pos:"{pos}",lesson:{lesson}}}'
    updated_parts.append(new_obj)

new_array = '  ' + ',\n  '.join(updated_parts) + '\n'
new_html = html_text[:m.start(2)] + new_array + html_text[m.end(2):]
html_path.write_text(new_html, encoding='utf-8')

print(f'Updated {len(objects)} vocab entries from the PDF definitions.')
