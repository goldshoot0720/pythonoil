from __future__ import annotations

from pathlib import Path

try:
    from .paths import default_creative_vector_art_path
except ImportError:
    from paths import default_creative_vector_art_path


def save_reference_vector_art(path: Path | None = None) -> Path:
    output_path = path or default_creative_vector_art_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_REFERENCE_VECTOR_ART.strip() + "\n", encoding="utf-8")
    return output_path


_REFERENCE_VECTOR_ART = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" fill="none">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#ffd9e5"/>
      <stop offset="100%" stop-color="#ffd0da"/>
    </linearGradient>
    <linearGradient id="hair" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#403849"/>
      <stop offset="100%" stop-color="#25212e"/>
    </linearGradient>
    <linearGradient id="dress" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#ffbad8"/>
      <stop offset="100%" stop-color="#f58fbc"/>
    </linearGradient>
    <linearGradient id="blue" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#79b8ff"/>
      <stop offset="100%" stop-color="#315bd8"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="16" stdDeviation="20" flood-color="#e49aaa" flood-opacity="0.35"/>
    </filter>
  </defs>

  <rect width="1024" height="1024" fill="url(#bg)"/>
  <rect x="54" y="54" width="916" height="916" rx="40" fill="#fff2b4" stroke="#ff6673" stroke-width="26"/>

  <g opacity="0.7">
    <path d="M120 180h220M684 180h220M120 320h784M120 460h784M120 600h784M120 740h784M120 880h784" stroke="#ff9ba5" stroke-width="4"/>
    <path d="M210 120v784M390 120v784M570 120v784M750 120v784" stroke="#ff9ba5" stroke-width="4"/>
  </g>

  <g fill="#ffffff" stroke="#a8beff" stroke-width="3">
    <path d="M98 114c24 4 44 16 58 38 14-22 34-34 58-38-4 18-12 34-26 46 10 2 18 8 24 18-16 2-30-2-42-12-6 10-18 14-34 14 6-10 14-16 24-18-14-12-22-28-24-48z"/>
    <path d="M820 114c24 4 44 16 58 38 14-22 34-34 58-38-4 18-12 34-26 46 10 2 18 8 24 18-16 2-30-2-42-12-6 10-18 14-34 14 6-10 14-16 24-18-14-12-22-28-24-48z"/>
    <path d="M104 790c20 6 34 18 42 36 10-16 22-26 40-30-2 16-8 28-20 40 10 2 16 6 20 12-14 4-26 2-38-6-6 8-16 12-30 12 4-8 10-14 18-18-16-8-26-22-32-46z"/>
    <path d="M812 790c20 6 34 18 42 36 10-16 22-26 40-30-2 16-8 28-20 40 10 2 16 6 20 12-14 4-26 2-38-6-6 8-16 12-30 12 4-8 10-14 18-18-16-8-26-22-32-46z"/>
  </g>

  <circle cx="695" cy="164" r="154" fill="#ffe89a" opacity="0.95" filter="url(#shadow)"/>

  <g filter="url(#shadow)">
    <path d="M222 786c44-108 120-188 230-226 100-34 220-16 306 44 62 44 106 110 132 194H222z" fill="#ffffff" opacity="0.98"/>
    <path d="M354 640c72-48 142-64 226-52 76 12 144 48 202 110l-14 88H294l20-86c12-26 24-46 40-60z" fill="url(#dress)"/>
    <path d="M310 706c38-8 68 14 88 52M724 700c-30 0-58 22-76 56" stroke="#e86898" stroke-width="10" stroke-linecap="round"/>
  </g>

  <g>
    <path d="M292 278c10-74 68-130 136-152 78-24 162-10 230 28 94 54 154 150 148 286-2 72-28 124-76 170-70 68-144 92-236 80-72-10-130-40-182-96-50-54-70-116-62-202 2-44 12-82 42-114z" fill="#ffece7"/>
    <path d="M274 324c22-70 58-118 112-146 66-34 170-42 252-8 72 30 132 104 144 188 14 92-6 174-58 236-20 22-36 32-62 52 12-42 16-82 14-124-2-32 6-70 20-120 10-32 6-72-20-108-22 6-48-2-76-16-28-14-58-26-92-28-60-4-112 16-156 62-26 26-54 72-86 136-6-48-4-84 8-124z" fill="url(#hair)"/>

    <path d="M212 466c10-62 54-100 116-114 8 54 2 102-18 146-18 38-56 62-108 48-16-48-14-68 10-80z" fill="url(#hair)"/>
    <path d="M808 444c20 8 34 30 34 72-14 40-46 56-96 52-20-6-30-18-34-42-8-34-8-72 2-118 48 12 78 24 94 36z" fill="url(#hair)"/>

    <path d="M318 270c-40-18-58-14-74 10 2-34 20-54 54-60 24 6 38 22 44 50z" fill="#f38aba" stroke="#b95d87" stroke-width="4"/>
    <path d="M770 278c34-22 56-24 74-6-2-34-20-56-52-64-26 6-42 22-50 58z" fill="#f38aba" stroke="#b95d87" stroke-width="4"/>

    <path d="M258 784c34-22 82-22 136 2-18 30-34 54-50 70-42-8-74-26-94-72l8 0z" fill="#ffd86c"/>
    <path d="M404 470c32 6 58 22 82 46-34 16-58 44-72 84-34-8-72-40-108-86 30-34 64-48 98-44z" fill="#ffffff"/>
    <path d="M676 482c42 4 76 22 102 58-24 46-56 72-92 86-12-36-38-66-74-84 20-30 42-50 64-60z" fill="#ffffff"/>

    <path d="M428 552c44 10 92 6 138-6 18 20 30 42 36 64-44 28-84 46-122 50-32-12-58-38-80-76 8-14 18-24 28-32z" fill="#f99bc5"/>
    <path d="M392 650c42-20 86-20 130 0-6 24-20 40-40 52-44 2-74-8-90-30v-22z" fill="#f57db1"/>
    <path d="M508 518l34 24-28 30-40-24 34-30z" fill="#f6d99b"/>
    <rect x="496" y="554" width="24" height="144" rx="10" fill="#f8d278" stroke="#b98c39" stroke-width="4"/>
    <path d="M468 460l58-42 18 164h-72l-4-122z" fill="#ffffff" stroke="#d7d7d7" stroke-width="4"/>

    <path d="M442 564c-18 28-28 56-30 92M584 564c20 24 28 56 24 100" stroke="#e46d9e" stroke-width="8" stroke-linecap="round"/>

    <path d="M422 760c34-18 74-16 122 0" stroke="#f27fb4" stroke-width="30" stroke-linecap="round"/>
    <circle cx="454" cy="780" r="12" fill="#5b3f3c"/>
    <circle cx="490" cy="782" r="12" fill="#5b3f3c"/>
    <circle cx="724" cy="370" r="18" fill="url(#blue)"/>
    <circle cx="280" cy="382" r="18" fill="url(#blue)"/>
  </g>

  <g>
    <ellipse cx="438" cy="544" rx="38" ry="18" fill="#f8c8d4" opacity="0.78"/>
    <ellipse cx="640" cy="544" rx="40" ry="18" fill="#f8c8d4" opacity="0.78"/>
    <path d="M466 490c20-22 44-20 60 2" stroke="#3d1a25" stroke-width="10" stroke-linecap="round"/>
    <path d="M608 488c22-24 52-18 72 8" stroke="#3d1a25" stroke-width="10" stroke-linecap="round"/>
    <path d="M460 490c6 12 18 16 30 8" stroke="#6e3342" stroke-width="5" stroke-linecap="round"/>
    <circle cx="634" cy="516" r="54" fill="#8ec7ff" stroke="#2f5dc0" stroke-width="6"/>
    <circle cx="620" cy="504" r="18" fill="#c7ebff"/>
    <circle cx="650" cy="534" r="10" fill="#d6f6ff"/>
    <circle cx="650" cy="494" r="8" fill="#ffffff"/>
    <circle cx="610" cy="536" r="6" fill="#ffffff"/>
    <path d="M486 598c18 16 42 18 72 2" stroke="#ee9baf" stroke-width="8" stroke-linecap="round"/>
    <path d="M534 548c6 8 6 18 0 26" stroke="#efb6aa" stroke-width="6" stroke-linecap="round"/>
  </g>

  <g fill="#ff6b86" opacity="0.9">
    <path d="M26 58c16-18 40-12 48 10 8-24 32-28 48-12 14 16 10 38-10 54-10 8-22 14-38 20-18-4-32-10-42-16-22-14-26-38-6-56z"/>
    <path d="M974 136c12-12 26-10 34 6 6-14 22-16 34-6 10 12 8 26-6 36-10 6-18 10-28 12-12-2-22-6-30-12-14-10-16-24-4-36z" opacity="0.6"/>
    <path d="M34 900c12-12 26-10 34 6 6-14 22-16 34-6 10 12 8 26-6 36-10 6-18 10-28 12-12-2-22-6-30-12-14-10-16-24-4-36z" opacity="0.65"/>
  </g>
</svg>
"""
