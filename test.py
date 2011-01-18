#!/usr/bin/env python
import random
import unittest
import shutil
import os
from cachefs import FileDataCache, CacheMiss

class TestFileDataCache(unittest.TestCase):

    #decorator to give tests a cache object
    def fdc(f):
        return lambda s: f.__call__(s, FileDataCache(s.cache_base, '/'+f.__name__))

    def assertData(self, cache, data, offset = 0):
        self.assertEqual(cache.read(len(data), offset), data)
        
    def setUp(self):
        self.cache_base = ".test_dir"
        try:
            shutil.rmtree(self.cache_base)
        except OSError:
            pass

    @fdc
    def test_simple_update_read(self, cache):
        cache.update("foo", 0)
        self.assertData(cache, "foo", 0)

    @fdc
    def test_multi_update_read(self, cache):
        data = bytes([1, 2, 3, 4, 5])
        cache.update(data, 0)
        cache.update(data, len(data))

        self.assertData(cache, data, 0)
        self.assertData(cache, data, len(data))

    @fdc
    def test_simple_miss(self, cache):
        self.assertRaises(CacheMiss, 
                          cache.read, cache, (1, 0))


    @fdc
    def test_not_enough_data_mss(self, cache):
        data = bytes(range(10))
        cache.update(data, 0)

        self.assertRaises(CacheMiss, 
                          cache.read, cache, (2*len(data), 0))
        
    @fdc
    def test_inner_read(self, cache):
        data = bytes(range(10))
        cache.update(data, 0)
        
        self.assertData(cache, data[1:], 1)

    @fdc
    def test_sparce_file(self, cache):
        data = bytes(b'1234567890')
        seek_to = 1000000000000
        cache.update(data, seek_to)
        cache.cache.flush()
        st = os.stat(cache.cache.name)
        self.assertTrue( seek_to > st.st_blocks * st.st_blksize)


    @fdc
    def test_add_block_1(self, cache):
        data1 =      b'1234567890'
        data2 = b'1234567890'
        result= b'123456789067890'
        
        cache.update(data1, 10)
        cache.update(data2, 5)

        self.assertTrue(len(cache.known_offsets) == 1)
        self.assertTrue(cache.known_offsets[5] == 15)

        self.assertTrue(cache.read(15, 5) == result)

    @fdc
    def test_add_block_2(self, cache):
        data1 =      b'1234567890'
        data2 = b'12345678901234567890'
        result= b'12345678901234567890'
        
        cache.update(data1, 10)
        cache.update(data2, 5)

        self.assertTrue(len(cache.known_offsets) == 1)
        self.assertTrue(cache.known_offsets[5] == len(result))

        self.assertTrue(cache.read(len(result), 5) == result)

    @fdc
    def test_add_block_3(self, cache):
        data1 =      b'1234567890'
        data2 = b'12345'
        result= b'123451234567890'
        
        cache.update(data1, 10)
        cache.update(data2, 5)
        try:
            self.assertTrue(len(cache.known_offsets) == 1)
            self.assertTrue(cache.known_offsets[5] == len(result))
            
            self.assertTrue(cache.read(len(result), 5) == result)
        except:
            cache.report()
            raise

    @fdc
    def test_add_block_4(self, cache):
        data1 =       b'1234567890'
        data2 = b'12345'
        results= ((b'12345', 5),(b'1234567890', 11))
        
        cache.update(data1, 11)
        cache.update(data2, 5)
        try:
            self.assertTrue(len(cache.known_offsets) == 2)
            for result, offset in results: 
                self.assertTrue(cache.known_offsets[offset] == len(result))
                
                self.assertTrue(cache.read(len(result), offset) == result)
        except:
            cache.report()
            raise

    @fdc
    def test_add_block_6(self, cache):
        data1 = b'1234567890'
        data2 = b'54321'
        result= b'5432167890'
        
        cache.update(data1, 0)
        cache.update(data2, 0)
        try:
            self.assertTrue(len(cache.known_offsets) == 1)
            self.assertTrue(cache.known_offsets[0] == len(result))
            
            self.assertTrue(cache.read(len(result), 0) == result)
        except:
            cache.report()
            raise

    @fdc
    def test_add_block_7(self, cache):
        data1 = b'1234567890'
        data2 =    b'54321'
        result= b'1235432190'
        
        cache.update(data1, 0)
        cache.update(data2, 3)
        try:
            self.assertTrue(len(cache.known_offsets) == 1)
            self.assertTrue(cache.known_offsets[0] == len(result))
            
            self.assertTrue(cache.read(len(result), 0) == result)
        except:
            cache.report()
            raise

    @fdc
    def test_add_block_8(self, cache):
        data1 = b'1234567890'
        data2 =      b'54321'
        result= b'1234554321'
        
        cache.update(data1, 0)
        cache.update(data2, 5)
        try:
            self.assertTrue(len(cache.known_offsets) == 1)
            self.assertTrue(cache.known_offsets[0] == len(result))
            
            self.assertTrue(cache.read(len(result), 0) == result)
        except:
            cache.report()
            raise

    @fdc
    def test_add_block_9(self, cache):
        data1 = b'1234567890'
        data2 =                  b'54321'
        data3 =           b'54321'
        
        results= ((b'123456789054321', 0),(b'54321', 17))
        
        
        cache.update(data1, 0)
        cache.update(data2, 17)
        cache.update(data3, 10)
        try:
            self.assertTrue(len(cache.known_offsets) == 2)
            for result, offset in results: 
                self.assertTrue(cache.known_offsets[offset] == len(result))
                
                self.assertTrue(cache.read(len(result), offset) == result)
        except:
            cache.report()
            raise

    def cmp_bufs(self, buf1, buf2):
        if len(buf1) != len(buf2):
            return False

        for i in range(len(buf1)):
            if buf1[i] != buf2[i]:
                return False

        return True

    def verify_add_blocks(self, cache, inputs, results):
        for space, bytes in inputs:
            cache.update(bytes, len(space))

        try:
            self.assertTrue(len(cache.known_offsets) == len(results))
            
            for space, result in results.items():
                try:
                    offset = len(space)
                    self.assertTrue(cache.known_offsets[offset] == len(result))
                    self.assertTrue(self.cmp_bufs(cache.read(len(result), 
                                                             offset), 
                                                  result))
                except:
                    print "\n\nresult: %s, offset: %d, len: %d" % (result,
                                                                   offset, 
                                                                   len(result))
                    print "buffer: %s\n" % cache.read(len(result), offset)
                    print self.cmp_bufs(cache.read(len(result), offset), 
                                        result)
                    raise
        except:
            cache.report()
            raise
        
    @fdc
    def test_add_block_10(self, cache):
        inputs = (('', b'1234567890'),
                  ('          ', b'54321'),
                  ('                 ', b'54321'))
        
        results= {'': b'123456789054321',
                  '                 ': b'54321'}
        
        self.verify_add_blocks(cache, inputs, results)

    @fdc
    def test_add_block_11(self, cache):
        inputs = (('', b'54321'),
                  ('               ', b'54321'),
                  ('     ', b'1234567890'))
        
        results= {'': b'54321123456789054321'}

        self.verify_add_blocks(cache, inputs, results)

    @fdc
    def test_add_block_12(self, cache):
        inputs = (('', b'54321'),
                  ('             ', b'54321'),
                  ('    ', b'1234567890'))
        
        results= {'':  b'543212345678904321'}
        
        self.verify_add_blocks(cache, inputs, results)

    @fdc
    def test_add_block_13(self, cache):
        inputs = (('', b'54321'),
                  ('             ', b'54321'),
                  ('    ', b'12345678901234567890'))
        
        results= {'': b'543212345678901234567890'}
        
        self.verify_add_blocks(cache, inputs, results)

if __name__ == '__main__':
    unittest.main()

