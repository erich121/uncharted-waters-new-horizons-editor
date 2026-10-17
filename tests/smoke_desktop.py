"""Exercise real pygame rendering/events offscreen; write QA screenshots."""
import json, os, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['SDL_VIDEODRIVER']='dummy'; os.environ['SDL_AUDIODRIVER']='dummy'
sys.path.insert(0,str(ROOT/'map_app'))
import pygame
from main import Atlas

app=Atlas(restore=False); app.message_until=0
app.render()
assert app.pitch==1.0
assert app.zoom==app.size[0]/32
for p in app.world.ports:
    x,y=app.to_world(app.to_screen(p['x']+1,p['y']+1))
    assert abs(x-p['x']-1)<1e-6 and abs(y-p['y']-1)<1e-6
# Upright masts and directional hulls must render in each compass direction.
from ship_25d import galleon
for direction in range(32):
    for sails in (0,1,2):
        sprite=galleon(direction,0,sails)
        assert sprite.get_size()==(240,230) and sprite.get_bounding_rect().height>40
app.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_w))
for _ in range(90): app.update(1/60)
assert app.ship.speed>1 and app.world.is_water(app.ship.x,app.ship.y,.24)
app.render(); pygame.image.save(app.screen,ROOT/'output/europe-sailing-preview.png')
app.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE)); assert app.ship.speed==0
app.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_m)); app.render(); assert app.atlas
pygame.image.save(app.screen,ROOT/'output/europe-preview.png')
# Atlas coordinate round-trip and mouse port selection.
for p in app.world.ports:
    x,y=app.to_world(app.to_screen(p['x']+1,p['y']+1))
    assert abs(x-p['x']-1)<1e-6 and abs(y-p['y']-1)<1e-6
port=app.world.ports[0]; point=app.to_screen(port['x']+1,port['y']+1)
app.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point))
assert app.selected and app.selected['id']==0
app.selected=None
point=app.to_screen(370,370)
app.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point))
app.elapsed+=.1
app.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point))
assert not app.atlas and not app.follow
app.center_ship(); app.render()
app.event(pygame.event.Event(pygame.MOUSEWHEEL,y=2,x=0)); assert app.zoom>5
app.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SLASH))
app.event(pygame.event.Event(pygame.TEXTINPUT,text='London')); app.render()
assert len(app.matches())==1
app.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN)); assert not app.search
assert app.world.nearest_port(app.ship.x,app.ship.y)[0]['name']=='London'
app.render(); pygame.image.save(app.screen,ROOT/'output/london-preview.png')
app.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_F1)); app.render()
assert len(app.buttons)==1  # Background controls cannot activate through help.
pygame.image.save(app.screen,ROOT/'output/help-preview.png')
app.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE)); assert not app.help
app.reference=True; app.grid=True; app.render()
app.reference=False; app.grid=False; app.zoom=5; app.ship.relocate(port); app.center_ship()
times=[]
for _ in range(90):
    start=time.perf_counter(); app.render(); times.append(time.perf_counter()-start)
report=dict(renderer='pygame / SDL dummy',region='Europe',view='2.5D / original square-cell scale',harbors=len(app.world.ports),rendered_frames=len(times),mean_render_ms=round(sum(times)/len(times)*1000,2),max_render_ms=round(max(times)*1000,2),checks=['37 sailing coordinate round trips','32 ship directions with three sail states','sail and anchor','37 atlas coordinate round trips','port click','atlas double click','zoom','port search and relocation','modal input isolation','reference and grid rendering'])
(ROOT/'output/desktop-qa.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2)); pygame.quit()
