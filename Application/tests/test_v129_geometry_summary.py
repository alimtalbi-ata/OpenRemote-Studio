import unittest
from layout_geometry import rectangle_within,inspect_rectangles
from qualification_consolidator import consolidate
class GeometryAndSummaryTests(unittest.TestCase):
 def test_contained(self):self.assertTrue(rectangle_within((10,10,100,100),(0,0,200,200)))
 def test_clipped(self):self.assertFalse(rectangle_within((190,10,20,20),(0,0,200,200)))
 def test_negative_coordinates(self):self.assertFalse(rectangle_within((-2,0,10,10),(0,0,200,200)))
 def test_tolerance(self):self.assertTrue(rectangle_within((-2,0,10,10),(0,0,200,200),2))
 def test_bad_rectangle(self):
  with self.assertRaises(ValueError):rectangle_within((1,2,0,4),(0,0,100,100))
 def test_bad_tolerance(self):
  with self.assertRaises(ValueError):rectangle_within((1,2,3,4),(0,0,100,100),True)
 def test_inspection(self):
  r=inspect_rectangles({'search':(0,0,20,20),'dialog':(100,0,30,30)},(0,0,120,100));self.assertEqual(r['clipped'],['dialog'])
 def test_all_passed(self):self.assertEqual(consolidate({'a':{'status':'passed'}})['overall'],'passed')
 def test_not_executed(self):self.assertEqual(consolidate({'a':{'status':'passed'},'b':{'status':'not_executed'}})['overall'],'incomplete')
 def test_failure_priority(self):self.assertEqual(consolidate({'a':{'status':'failed'},'b':{'status':'not_executed'}})['overall'],'failed')
 def test_invalid_status(self):
  with self.assertRaises(ValueError):consolidate({'a':{'status':'magic'}})
