"""
Refines NAMMA BELE logo assets:
- Removes 'Since 2026' completely.
- Preserves original illustration: Sprout, sack, trowel, fertile soil mound, stars, and halo.
- Improves typography, alignment, contrast, optical centering, and edge antialiasing.
- Generates:
  1. namma_bele_logo.png (Vertical lockup on #FDF9F2 cream)
  2. namma_bele_logo_transparent.png (Vertical lockup with transparent alpha)
  3. namma_bele_logo_horizontal.png (Horizontal lockup for navbar/headers)
  4. namma_bele_emblem.png (Iconic square emblem)
  5. favicon.png & favicon.ico (Multi-size favicons: 16, 32, 48, 64)
  6. logo.svg (Scalable vector graphic)
"""
import os
from PIL import Image, ImageDraw, ImageFilter

def refine_logos():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    img_dir = os.path.join(base_dir, "app", "static", "img")
    raw_path = os.path.join(img_dir, "namma_bele_logo_raw.png")
    if not os.path.exists(raw_path):
        raw_path = "/Users/manojv/.gemini/antigravity/brain/b5d0d17c-8450-4d74-aded-bf3c68079b42/.user_uploaded/media_1794241010009_77a9484b.png"

    raw = Image.open(raw_path).convert("RGBA")
    w, h = raw.size
    bg_cream = (253, 249, 242)

    # 1. Clean extraction of the Emblem: [175, 66, 332, 244]
    emblem_raw = raw.crop((175, 66, 332, 244))
    ew, eh = emblem_raw.size

    emblem_alpha = Image.new("RGBA", (ew, eh), (0, 0, 0, 0))
    for y in range(eh):
        for x in range(ew):
            r, g, b, a = emblem_raw.getpixel((x, y))
            diff = max(abs(r - bg_cream[0]), abs(g - bg_cream[1]), abs(b - bg_cream[2]))
            if diff < 7:
                alpha = 0
            elif diff < 24:
                alpha = int(255 * (diff - 7) / 17)
                emblem_alpha.putpixel((x, y), (r, g, b, alpha))
            else:
                emblem_alpha.putpixel((x, y), (r, g, b, 255))

    # 2. Clean extraction of 'NAMMA BELE' wordmark: [105, 256, 400, 292]
    # Note: 'SINCE 2026' is at y >= 305 and is completely excluded!
    text_raw = raw.crop((105, 256, 400, 292))
    tw, th = text_raw.size

    text_alpha = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    brand_brown = (60, 33, 21) # #3C2115

    for y in range(th):
        for x in range(tw):
            r, g, b, a = text_raw.getpixel((x, y))
            diff = max(abs(r - bg_cream[0]), abs(g - bg_cream[1]), abs(b - bg_cream[2]))
            if diff < 7:
                alpha = 0
            elif diff < 24:
                alpha = int(255 * (diff - 7) / 17)
                text_alpha.putpixel((x, y), (*brand_brown, alpha))
            else:
                text_alpha.putpixel((x, y), (*brand_brown, 255))

    # --- Asset 1: namma_bele_emblem.png ---
    emblem_square_size = max(ew, eh) + 16
    emblem_square = Image.new("RGBA", (emblem_square_size, emblem_square_size), (0, 0, 0, 0))
    ox = (emblem_square_size - ew) // 2
    oy = (emblem_square_size - eh) // 2
    emblem_square.paste(emblem_alpha, (ox, oy), emblem_alpha)
    emblem_square.save(os.path.join(img_dir, "namma_bele_emblem.png"), "PNG")

    # --- Asset 2: namma_bele_logo_transparent.png (Vertical lockup, no 'Since 2026') ---
    # Optical centering and balanced padding
    spacing = 18
    pad_y = 20
    pad_x = 24
    total_w = max(ew, tw) + (pad_x * 2)
    total_h = eh + spacing + th + (pad_y * 2)

    logo_trans = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    # Center emblem
    emblem_x = (total_w - ew) // 2
    logo_trans.paste(emblem_alpha, (emblem_x, pad_y), emblem_alpha)
    # Center text
    text_x = (total_w - tw) // 2
    logo_trans.paste(text_alpha, (text_x, pad_y + eh + spacing), text_alpha)
    logo_trans.save(os.path.join(img_dir, "namma_bele_logo_transparent.png"), "PNG")

    # --- Asset 3: namma_bele_logo.png (Vertical lockup on cream background) ---
    logo_cream = Image.new("RGBA", (total_w, total_h), (*bg_cream, 255))
    logo_cream.paste(logo_trans, (0, 0), logo_trans)
    logo_cream.save(os.path.join(img_dir, "namma_bele_logo.png"), "PNG")

    # --- Asset 4: namma_bele_logo_horizontal.png (Ideal for Navbar & Headers) ---
    # Horizontal lockup: Emblem on left, NAMMA BELE on right
    target_emblem_h = 64
    scale_factor = target_emblem_h / eh
    scaled_ew = int(ew * scale_factor)
    scaled_emblem = emblem_alpha.resize((scaled_ew, target_emblem_h), Image.Resampling.LANCZOS)

    scaled_th = int(th * scale_factor * 1.15)
    scaled_tw = int(tw * scale_factor * 1.15)
    scaled_text = text_alpha.resize((scaled_tw, scaled_th), Image.Resampling.LANCZOS)

    h_gap = 14
    h_pad_x = 10
    h_pad_y = 8
    h_total_w = scaled_ew + h_gap + scaled_tw + (h_pad_x * 2)
    h_total_h = max(target_emblem_h, scaled_th) + (h_pad_y * 2)

    logo_h = Image.new("RGBA", (h_total_w, h_total_h), (0, 0, 0, 0))
    logo_h.paste(scaled_emblem, (h_pad_x, h_pad_y), scaled_emblem)
    text_y = h_pad_y + (target_emblem_h - scaled_th) // 2
    logo_h.paste(scaled_text, (h_pad_x + scaled_ew + h_gap, text_y), scaled_text)
    logo_h.save(os.path.join(img_dir, "namma_bele_logo_horizontal.png"), "PNG")

    # --- Asset 5: Favicons (16, 32, 48, 64) ---
    fav64 = emblem_square.resize((64, 64), Image.Resampling.LANCZOS)
    fav64.save(os.path.join(img_dir, "favicon.png"), "PNG")
    fav64.save(os.path.join(img_dir, "favicon.ico"), format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])

    # --- Asset 6: Crisp Vector SVG (logo.svg) ---
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 230" width="100%" height="100%">
  <defs>
    <radialGradient id="badgeGrad" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#E6E2D9" stop-opacity="0.95"/>
      <stop offset="100%" stop-color="#E6E2D9" stop-opacity="0.6"/>
    </radialGradient>
    <radialGradient id="haloGrad" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#E6E2D9" stop-opacity="0.95"/>
      <stop offset="100%" stop-color="#E6E2D9" stop-opacity="0.6"/>
    </radialGradient>
    <linearGradient id="sackGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#BF7C42"/>
      <stop offset="100%" stop-color="#9C622D"/>
    </linearGradient>
    <linearGradient id="sproutGrad" x1="0%" y1="100%" x2="0%" y2="0%">
      <stop offset="0%" stop-color="#8E9E35"/>
      <stop offset="100%" stop-color="#A5B34A"/>
    </linearGradient>
  </defs>

  <!-- Circular Halo Background -->
  <circle cx="160" cy="95" r="54" fill="url(#badgeGrad)"/>

  <!-- Trowel Tool Wooden Handle & Blade -->
  <path d="M192 110 L204 88 C205 86 208 86 209 88 L212 93 C213 95 212 98 210 99 L198 120 Z" fill="#AF7137" stroke="#3C2115" stroke-width="1.8" stroke-linejoin="round"/>
  <path d="M188 116 L198 120 L191 135 C189 138 184 139 181 136 C179 133 180 128 183 125 Z" fill="#FFFFFF" stroke="#3C2115" stroke-width="1.8" stroke-linejoin="round"/>

  <!-- Planter Sack / Burlap Bag -->
  <path d="M136 100 C138 98 178 98 180 100 C182 103 184 135 180 148 C176 150 140 150 136 148 C132 135 134 103 136 100 Z" fill="url(#sackGrad)" stroke="#3C2115" stroke-width="2.4" stroke-linejoin="round"/>
  <path d="M134 101 C144 104 172 104 182 101" fill="none" stroke="#3C2115" stroke-width="2.2"/>

  <!-- Sprout Stem & Foliage Leaves -->
  <!-- Stem -->
  <path d="M158 104 C158 80 168 62 188 44" fill="none" stroke="#3C2115" stroke-width="2.6" stroke-linecap="round"/>
  <path d="M158 104 C154 86 146 72 138 58" fill="none" stroke="#3C2115" stroke-width="2.4" stroke-linecap="round"/>

  <!-- Leaves (Right branch) -->
  <path d="M188 44 C194 40 204 46 198 52 C192 56 186 48 188 44 Z" fill="url(#sproutGrad)" stroke="#3C2115" stroke-width="1.8" stroke-linejoin="round"/>
  <path d="M178 54 C186 52 194 60 188 66 C182 70 176 60 178 54 Z" fill="url(#sproutGrad)" stroke="#3C2115" stroke-width="1.8" stroke-linejoin="round"/>
  <path d="M168 68 C178 66 184 76 178 82 C172 86 166 74 168 68 Z" fill="url(#sproutGrad)" stroke="#3C2115" stroke-width="1.8" stroke-linejoin="round"/>

  <!-- Leaves (Left branch) -->
  <path d="M138 58 C132 52 124 58 128 66 C134 72 142 64 138 58 Z" fill="url(#sproutGrad)" stroke="#3C2115" stroke-width="1.8" stroke-linejoin="round"/>
  <path d="M144 74 C136 70 130 78 136 86 C142 90 148 80 144 74 Z" fill="url(#sproutGrad)" stroke="#3C2115" stroke-width="1.8" stroke-linejoin="round"/>
  <path d="M152 88 C144 86 140 94 146 100 C150 102 156 94 152 88 Z" fill="url(#sproutGrad)" stroke="#3C2115" stroke-width="1.8" stroke-linejoin="round"/>

  <!-- Sparkle Stars -->
  <path d="M208 72 Q208 78 214 78 Q208 78 208 84 Q208 78 202 78 Q208 78 208 72 Z" fill="#3C2115"/>
  <path d="M202 88 Q202 91 205 91 Q202 91 202 94 Q202 91 199 91 Q202 91 202 88 Z" fill="#3C2115"/>

  <!-- Fertile Loam Soil Mound -->
  <path d="M144 142 C148 136 156 136 162 140 C168 134 178 134 184 140 C192 136 202 142 200 152 C204 156 202 164 194 168 C186 172 172 170 164 168 C154 172 142 168 138 160 C134 156 138 146 144 142 Z" fill="#3C2115"/>

  <!-- NAMMA BELE Wordmark (Polished Typography - Deep Loam Brown) -->
  <text x="160" y="210" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Arial Rounded MT Bold', sans-serif" font-size="28" font-weight="900" fill="#3C2115" letter-spacing="2.5">NAMMA BELE</text>
</svg>'''
    with open(os.path.join(img_dir, "logo.svg"), "w") as f:
        f.write(svg_content)

    print("Refined logo assets successfully generated:")
    print(" - namma_bele_emblem.png")
    print(" - namma_bele_logo_transparent.png")
    print(" - namma_bele_logo.png")
    print(" - namma_bele_logo_horizontal.png")
    print(" - favicon.png & favicon.ico")
    print(" - logo.svg")

if __name__ == "__main__":
    refine_logos()
