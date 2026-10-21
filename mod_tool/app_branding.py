"""Approved nautical branding shared by source and bundled Windows builds."""
from pathlib import Path
from PIL import Image,ImageTk


class Branding:
    def __init__(self,root):
        self.root=root;self.photos={}
        with Image.open(Path(__file__).resolve().parent/'assets/app-logo.png')as image:
            self.image=image.convert('RGBA')
        # Keep all icon sizes alive for Tk, including inherited dialog icons.
        root.iconphoto(True,*(self.photo(n)for n in (16,32,48,64,256)))

    def photo(self,size):
        if size not in self.photos:
            image=self.image.resize((size,size),Image.Resampling.LANCZOS)
            self.photos[size]=ImageTk.PhotoImage(image,master=self.root)
        return self.photos[size]
