import os
from PIL import Image

def optimize_images(directory):
    total_saved = 0
    print(f"Optimizing images in {directory}...")

    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path)
            
            # Skip small files (under 200KB) unless they are huge dimensions
            if file_size < 200 * 1024:
                continue

            ext = os.path.splitext(file)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png']:
                continue

            try:
                with Image.open(file_path) as img:
                    original_size = file_size
                    
                    # Convert RGBA to RGB if possible to save space (unless transparency needed)
                    # We will be careful. If it's PNG > 1MB, we try to optimize.
                    
                    if ext == '.png' and file_size > 1 * 1024 * 1024: # > 1MB PNG
                         # Check transparency
                        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                            # Has transparency, just resize/optimize
                            pass
                        else:
                            # No transparency, convert to JPEG might be better but let's stick to PNG optimization
                            pass
                    
                    # Resize if too huge
                    max_dim = 1920
                    if img.width > max_dim or img.height > max_dim:
                        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
                        print(f"Resized {file}")

                    # Save optimization
                    if ext in ['.jpg', '.jpeg']:
                        img.save(file_path, "JPEG", quality=75, optimize=True)
                    elif ext == '.png':
                        # For PNG, we can't do much with standard PIL without losing quality or transparency.
                        # We will just save with optimize=True. 
                        # If it's huge, we might convert to JPG if user agrees, but for now let's just resize.
                        # Actually, for the 7MB expert.png, resizing is key.
                        img.save(file_path, "PNG", optimize=True)
                    
                    new_size = os.path.getsize(file_path)
                    saved = original_size - new_size
                    total_saved += saved
                    if saved > 0:
                        print(f"Optimized {file}: {original_size/1024:.1f}KB -> {new_size/1024:.1f}KB (Saved {saved/1024:.1f}KB)")
            except Exception as e:
                print(f"Error optimizing {file}: {e}")

    print(f"Total space saved: {total_saved / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    web_dir = os.path.join(current_dir, "web")
    optimize_images(web_dir)
