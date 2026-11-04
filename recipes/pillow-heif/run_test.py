from io import BytesIO

from PIL import Image

import pillow_heif


info = pillow_heif.libheif_info()
assert info["HEIF"]
assert info["encoders"]
assert info["decoders"]

pillow_heif.register_heif_opener()

output = BytesIO()
Image.new("RGB", (4, 3), (12, 34, 56)).save(output, format="HEIF", quality=90)
assert pillow_heif.get_file_mimetype(output.getvalue()) == "image/heic"

output.seek(0)
image = Image.open(output)
image.load()
assert image.mode == "RGB"
assert image.size == (4, 3)
