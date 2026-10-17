import hashlib, json, math, os, sys, unittest, zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'map_app'))
from world import World, Vessel, WIDTH, HEIGHT, LEFT,TOP,RIGHT,BOTTOM, EXPECTED_HASH

class AtlasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.world=World(ROOT/'map_app/assets')
    def test_original_map_and_port_coordinates(self):
        self.assertEqual(self.world.tiles.shape,(1080,2160))
        self.assertEqual(hashlib.sha256(self.world.tiles.tobytes()).hexdigest(),EXPECTED_HASH)
        self.assertEqual(len(self.world.all_ports),130)
        self.assertEqual(len(self.world.ports),37)
        self.assertEqual(sum(p['supply'] for p in self.world.ports),3)
        self.assertEqual([(p['name'],p['x'],p['y']) for p in self.world.ports[:3]], [('Lisbon',120,358),('Seville',142,372),('Istanbul',352,344)])
    def test_every_port_has_a_seaworthy_start(self):
        ship=Vessel(self.world)
        for p in self.world.ports:
            ship.relocate(p)
            self.assertTrue(self.world.is_water(ship.x,ship.y,.24),p['name'])
            self.assertLess(math.hypot(ship.x-p['x'],ship.y-p['y']),65,p['name'])
    def test_full_sails_moves_and_anchor_stops(self):
        ship=Vessel(self.world); x=ship.x; ship.sails=1
        for _ in range(180): ship.update(1/60)
        self.assertLess(ship.x,x-10)
        ship.sails=0; ship.speed=0; x,y=ship.x,ship.y
        for _ in range(60): ship.update(1/60)
        self.assertEqual((ship.x,ship.y),(x,y))
    def test_collision_cannot_tunnel_into_a_coast(self):
        ship=Vessel(self.world); ship.heading=0; ship.sails=1
        collided=False
        for _ in range(1200):
            ship.update(.1)
            self.assertTrue(self.world.is_water(ship.x,ship.y,.24))
            if ship.grounded: collided=True; break
        self.assertTrue(collided); self.assertEqual(ship.speed,0); self.assertEqual(ship.sails,0)
    def test_europe_boundaries_stop_the_ship(self):
        row=next(y for y in range(TOP+1,BOTTOM-1) if self.world.is_water(LEFT+.5,y+.5,.24))
        ship=Vessel(self.world); ship.x=LEFT+.3; ship.y=row+.5; ship.heading=math.pi; ship.speed=8; ship.sails=1
        ship.update(.1)
        self.assertGreaterEqual(ship.x,LEFT); self.assertTrue(ship.grounded)
        self.assertFalse(self.world.is_water(LEFT-.1,250)); self.assertFalse(self.world.is_water(RIGHT,250))
        self.assertFalse(self.world.is_water(200,TOP-.1)); self.assertFalse(self.world.is_water(200,BOTTOM))
    def test_courses_reject_land(self):
        ship=Vessel(self.world)
        self.assertFalse(ship.set_course(120,358))
        self.assertTrue(ship.set_course(ship.x-20,ship.y))
    def test_art_classifier_matches_runtime_collision(self):
        from build_art import classification
        import numpy as np
        self.assertTrue(np.array_equal(classification(self.world.tiles),self.world.terrain))

if __name__=='__main__': unittest.main()
