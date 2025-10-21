import os
import logging
from PIL import Image, ImageOps

# Compatibility for Pillow resampling constant
try:
    RESAMPLE_LANCZOS = Image.LANCZOS
except Exception:
    try:
        RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
    except Exception:
        RESAMPLE_LANCZOS = None

def resize_and_save_all_images(original_folder, image_folder, img_name, size=(1500, 1500)):
    """
    Resize and pad images from the original folder to the specified size and save them to the image folder.
    Handles both .jpg and .png images. PNG transparency bliver til hvid baggrund.
    """
    found_any = False
    for i in range(10):  # Assume a maximum of 10 images per product
        suffix = f"-{i+1}" if i > 0 else ""
        for ext in [".jpg", ".png"]:
            original_path = os.path.join(original_folder, f"{img_name}{suffix}{ext}")
            if os.path.exists(original_path):
                try:
                    with Image.open(original_path) as img:
                        if RESAMPLE_LANCZOS:
                            resized_img = ImageOps.pad(img, size, color="white", method=RESAMPLE_LANCZOS)
                        else:
                            resized_img = ImageOps.pad(img, size, color="white")
                        # Hvis billedet har alpha (gennemsigtighed), læg det på hvid baggrund
                        if resized_img.mode in ("RGBA", "LA") or (resized_img.mode == "P" and 'transparency' in resized_img.info):
                            background = Image.new("RGB", resized_img.size, (255, 255, 255))
                            background.paste(resized_img, mask=resized_img.split()[-1])
                            resized_img = background
                        else:
                            resized_img = resized_img.convert("RGB")
                        resized_path = os.path.join(image_folder, f"{img_name}{suffix}.jpg")
                        resized_img.save(resized_path, "JPEG", quality=100)
                        logging.info(f"Resized image saved: {resized_path}")
                        found_any = True
                except Exception as e:
                    logging.error(f"Error resizing image {original_path}: {e}")
        # If neither .jpg nor .png found for this index, stop if i==0, else continue
        if not any(os.path.exists(os.path.join(original_folder, f"{img_name}{suffix}{ext}")) for ext in [".jpg", ".png"]):
            if i == 0 and not found_any:
                logging.warning(f"No image found to resize for {img_name}")
            break
