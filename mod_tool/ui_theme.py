"""Small vector UI icons and stretchable rounded surfaces for the Tk editor."""
from PIL import Image, ImageDraw, ImageTk
from tkinter import ttk

BG='#f5f7fb'
HEADER='#f4f7fb'
BLUE='#0869df'


class SectionCard(ttk.Frame):
    """A consistent header and content surface, without owning layout policy."""
    def __init__(self, parent, title, clean=False):
        super().__init__(parent, style='CleanSurface.TFrame'if clean else 'Surface.TFrame', padding=1)
        header = ttk.Frame(self, style='Card.TFrame'if clean else 'CardHeader.TFrame', padding=(10, 6))
        header.pack(fill='x', padx=8)
        self.title_label = ttk.Label(header, text=title, style='CleanCardTitle.TLabel'if clean else 'CardTitle.TLabel')
        self.title_label.pack(anchor='w')
        if clean:
            ttk.Frame(self,height=1,style='CardRule.TFrame').pack(fill='x',padx=18,pady=(0,4))
        self.body = ttk.Frame(self, style='Card.TFrame', padding=12)
        self.body.pack(fill='both', expand=True, padx=8, pady=(0, 8))

    def set_title(self, title):
        self.title_label.configure(text=title)

class EditorTheme:
    def __init__(self,root,style):
        self.root=root;self.style=style;self.images=[];self.icons={}
        self.button('TButton','Modern', '#fbfcff','#c8d3e3','#eef5ff')
        self.button('Primary.TButton','PrimaryModern',BLUE,'#075bc3','#075bc3')
        self.surface('Surface.TFrame','Surface', 'white','#d5dfed',8,header=True)
        self.surface('CleanSurface.TFrame','CleanSurface','white','#d5dfed',8)
        self.surface('Sidebar.TFrame','Sidebar','#f0f4f9','#d8e2ee',8)
        style.configure('SidebarContent.TFrame',background='#f0f4f9')
        style.configure('Sidebar.TLabel',background='#f0f4f9')
        style.configure('Status.TLabel',background='white')
        style.configure('Card.TCheckbutton',background='white',padding=(0,3))
        style.map('Card.TCheckbutton',background=[('active','white'),('disabled','white')])
        self.entry('TEntry','RoundedEntry')
        self.entry('TSpinbox','RoundedSpinbox')
        style.configure('CardHeader.TFrame',background=HEADER)
        style.configure('CardTitle.TLabel',background=HEADER,foreground='#152c50',font=('Segoe UI',12,'bold'))
        style.configure('CleanCardTitle.TLabel',background='white',foreground='#152c50',font=('Segoe UI',12,'bold'))
        style.configure('CardRule.TFrame',background='#e1e8f2')
        style.configure('Tab.TButton',background=BG,foreground='#26334b',padding=(18,11),borderwidth=0,relief='flat',width=0)
        style.configure('Active.Tab.TButton',background='white',foreground=BLUE)
        for name in ('Tab.TButton','Active.Tab.TButton','Nav.TButton','Selected.Nav.TButton','Disclosure.TButton'):
            style.layout(name,[('Button.padding',{'sticky':'nsew','children':[('Button.label',{'sticky':'nsew'})]})])
        style.configure('Nav.TButton',background='#f0f4f9',foreground='#48586d',anchor='w',padding=(16,10))
        style.map('Nav.TButton',background=[('active','#e5eef9')],foreground=[('disabled','#8b98a9')])
        style.configure('Selected.Nav.TButton',background='#d7e9ff',foreground='#123d73')
        style.configure('Disclosure.TButton',foreground='#335d91',background=BG,padding=(4,8),anchor='w')
        style.configure('Editor.TNotebook',borderwidth=0,background=BG,tabmargins=0)
        style.layout('Editor.TNotebook.Tab',[])

    def photo(self,image):
        p=ImageTk.PhotoImage(image,master=self.root);self.images.append(p);return p

    def patch(self,fill,outline,radius=6,header=False,size=64):
        scale=3
        im=Image.new('RGBA',(size*scale,size*scale));d=ImageDraw.Draw(im)
        box=(scale//2,scale//2,size*scale-scale//2-1,size*scale-scale//2-1)
        d.rounded_rectangle(box,radius=radius*scale,fill=fill,outline=outline,width=scale)
        if header:
            mask=Image.new('L',im.size);md=ImageDraw.Draw(mask)
            md.rounded_rectangle(box,radius=radius*scale,fill=255)
            layer=Image.new('RGBA',im.size,fill);ld=ImageDraw.Draw(layer)
            ld.rectangle((0,0,size*scale,44*scale),fill=HEADER)
            layer.putalpha(mask);im=layer
            ImageDraw.Draw(im).rounded_rectangle(box,radius=radius*scale,outline=outline,width=scale)
        return self.photo(im.resize((size,size),Image.Resampling.LANCZOS))

    def button(self,style_name,element,fill,outline,hover):
        normal=self.patch(fill,outline,size=16);active=self.patch(hover,outline,size=16)
        disabled=self.patch('#e8edf5','#d9e1ec',size=16)
        self.style.element_create(element,'image',normal,('disabled',disabled),('pressed',active),('active',active),border=4,sticky='nsew')
        self.style.layout(style_name,[(element,{'sticky':'nsew','children':[('Button.padding',{'sticky':'nsew','children':[('Button.label',{'sticky':'nsew'})]})]})])

    def surface(self,style_name,element,fill,outline,radius,header=False):
        self.style.element_create(element,'image',self.patch(fill,outline,radius,header),border=(9,44 if header else 9,9,9),sticky='nsew')
        self.style.layout(style_name,[(element,{'sticky':'nsew','children':[('Frame.padding',{'sticky':'nsew'})]})])

    def entry(self,style_name,element):
        normal=self.patch('white','#bac7da',5,size=16)
        focused=self.patch('white','#3888eb',5,size=16)
        disabled=self.patch('#f3f6fa','#dce3ee',5,size=16)
        readonly=self.patch('#f7f9fc','#ccd6e5',5,size=16)
        self.style.element_create(element,'image',normal,('disabled',disabled),('readonly',readonly),('focus',focused),border=5,sticky='nsew')
        old=self.style.layout(style_name)
        self.style.layout(style_name,[(element,old[0][1])])
        self.style.map(style_name, foreground=[('disabled', '#65748a')])

    def icon(self,name,color='#194c85',size=22):
        key=(name,color,size)
        if key in self.icons:return self.icons[key]
        s=4;im=Image.new('RGBA',(24*s,24*s));d=ImageDraw.Draw(im)
        def line(points,fill=color,width=1.8):d.line([(int(x*s),int(y*s))for x,y in points],fill=fill,width=max(1,int(width*s)),joint='curve')
        def ellipse(box,fill=None,outline=color,width=1.8):d.ellipse(tuple(int(v*s)for v in box),fill=fill,outline=outline,width=int(width*s))
        def rect(box,fill=None,outline=color,width=1.8):d.rectangle(tuple(int(v*s)for v in box),fill=fill,outline=outline,width=int(width*s))
        if name=='feather':
            d.polygon([(7*s,19*s),(4*s,15*s),(9*s,5*s),(18*s,2*s),(20*s,6*s),(17*s,15*s),(10*s,19*s)],fill='#95bbd5',outline='#254d69')
            line([(3,23),(16,6)],'#254d69',1.3);line([(9,15),(14,13)],'#426d89',1)
        elif name=='folder':
            d.polygon([(2*s,6*s),(9*s,6*s),(11*s,8*s),(22*s,8*s),(20*s,20*s),(2*s,20*s)],fill='#ffd23d',outline='#e9ad13')
            line([(3,10),(22,10),(19,20),(2,20),(3,10)],'#e9ad13',1)
        elif name=='save':
            rect((3,3,21,21));rect((7,3,16,9));rect((7,14,17,21));line([(14,4),(14,8)])
        elif name=='export':
            line([(3,15),(3,21),(21,21),(21,15)]);line([(12,17),(12,3),(7,8)]);line([(12,3),(17,8)])
        elif name in ('info','help'):
            ellipse((2,2,22,22),fill=color,outline=color)
            if name=='info':
                ellipse((11,6,13,8),fill='white',outline='white',width=.5);line([(12,11),(12,18)],'white',2)
            else:
                line([(8,8),(9,6),(14,6),(16,8),(16,10),(12,13),(12,15)],'white',2);ellipse((11,18,13,20),fill='white',outline='white',width=.5)
        elif name=='ship':
            line([(3,16),(21,16),(18,21),(7,21),(3,16)]);line([(12,3),(12,16)]);line([(10,5),(4,13),(10,13),(10,5)]);line([(14,6),(20,13),(14,13),(14,6)])
        elif name=='person':
            ellipse((8,2,16,10),fill=color);d.rounded_rectangle((4*s,13*s,20*s,22*s),radius=4*s,fill=color)
        elif name=='captain':
            ellipse((5,2,19,15),fill=color);ellipse((8,7,10,9),fill='white',outline='white',width=.5);ellipse((14,7,16,9),fill='white',outline='white',width=.5)
            line([(5,18),(19,22)]);line([(19,18),(5,22)]);rect((9,13,15,16),fill=color)
        elif name=='stats':
            for x,y in ((5,8),(12,15),(19,9)):
                line([(x,3),(x,21)]);ellipse((x-2,y-2,x+2,y+2),fill='white')
        elif name=='calendar':
            rect((3,5,21,21));line([(3,10),(21,10)]);line([(7,2),(7,8)]);line([(17,2),(17,8)])
            for x in (7,12,17):
                for y in (14,18):rect((x-1,y-1,x+1,y+1),fill=color,width=.5)
        elif name=='image':
            rect((2,3,22,21));ellipse((6,6,10,10),fill=color);line([(3,19),(10,12),(14,16),(17,12),(22,18)])
        elif name=='wrench':
            line([(4,21),(15,10)],width=5);line([(15,3),(12,7),(14,11),(18,12),(22,8),(18,8),(16,6),(16,3)],width=2.5)
        elif name=='game':
            d.rounded_rectangle((2*s,6*s,22*s,19*s),radius=4*s,outline=color,width=2*s)
            line([(5,12),(11,12)]);line([(8,9),(8,15)]);ellipse((15,9,17,11),fill=color);ellipse((18,13,20,15),fill=color)
        elif name=='coins':
            for y in (15,10,5):
                ellipse((3,y,21,y+7),fill=color);line([(5,y+5),(10,y+7),(15,y+7),(20,y+5)],'white',.8)
        elif name=='anchor':
            ellipse((9,2,15,8));line([(12,8),(12,21)]);line([(6,12),(18,12)]);line([(3,15),(4,19),(12,22),(20,19),(21,15)],width=2.2)
        elif name=='guns':
            line([(4,3),(20,20)],width=3);line([(20,3),(4,20)],width=3);line([(2,17),(7,22)]);line([(17,22),(22,17)])
        elif name=='restore':
            line([(5,8),(5,2),(1,7),(7,7)]);line([(5,6),(11,3),(18,6),(21,12),(19,18),(13,21),(6,19),(3,14)],width=2)
        elif name=='check':line([(4,12),(10,18),(21,5)],width=3)
        elif name=='add':line([(12,4),(12,20)],width=3);line([(4,12),(20,12)],width=3)
        elif name=='search':ellipse((3,3,15,15));line([(14,14),(21,21)],width=2)
        elif name=='down':line([(5,9),(12,16),(19,9)],width=2)
        elif name=='right':line([(9,5),(16,12),(9,19)],width=2)
        self.icons[key]=self.photo(im.resize((size,size),Image.Resampling.LANCZOS));return self.icons[key]
