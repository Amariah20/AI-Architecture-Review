"""Private child-process entry point: PDF bytes in, one PNG page out."""

from io import BytesIO
import math
import sys

import pypdfium2 as pdfium


def main() -> int:
    """Keep native rendering outside Streamlit threads; write no document files."""
    try:
        page_number, dpi, pixel_limit = map(int, sys.argv[1:])
        if page_number < 1 or not 72 <= dpi <= 300 or not 1 <= pixel_limit <= 12_000_000:
            return 2
        data = sys.stdin.buffer.read(25 * 1024 * 1024 + 1)
        if len(data) > 25 * 1024 * 1024 or not data.startswith(b"%PDF-"):
            return 2
        with pdfium.PdfDocument(data) as document:
            if page_number > len(document):
                return 2
            page = document[page_number - 1]
            try:
                width, height = page.get_size()
                if not all(math.isfinite(value) and value > 0 for value in (width, height)):
                    return 2
                scale = dpi / 72
                if math.ceil(width * scale) * math.ceil(height * scale) > pixel_limit:
                    return 3
                bitmap = page.render(scale=scale)
                try:
                    image = bitmap.to_pil()
                    try:
                        output = BytesIO()
                        image.save(output, format="PNG", dpi=(dpi, dpi))
                        sys.stdout.buffer.write(output.getvalue())
                    finally:
                        image.close()
                finally:
                    bitmap.close()
            finally:
                page.close()
        return 0
    except Exception:
        # Native parser errors can include source content; return only a code.
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
