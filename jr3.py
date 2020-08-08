
from ctypes import *

jr3 = cdll.LoadLibrary('./jr3/jr3.dll')
fh = jr3.GetHandle(1)

def read_words(offset, length=1):
	return [jr3.ReadWord(fh, 0, offset + i) for i in range(length)]
	
def read_word_list(offsets):
	return [jr3.ReadWord(fh, 0, offset) for offset in offsets]
	
def get_copyright():
	x = read_words(0x40, 18)
	return ''.join([y.to_bytes(2, 'big').decode('utf-8') for y in x])
	
def get_offsets():
	return [c_short(y).value for y in read_words(0x88, 6)]
	
def get_fs_minmax():
	fs_mins = [c_short(y).value for y in read_words(0x70, 6)]
	fs_maxs = [c_short(y).value for y in read_words(0x78, 6)]
	return list(zip(fs_mins, fs_maxs))
	
def get_fs():
	return [c_short(y).value for y in read_words(0x80, 8)]
	
def get_f(filter=0):
	if filter < 0 or filter > 6:
		raise ValueError('filter must be 0-6 inclusive.')
	raw = [c_short(y).value / 2**14 * fs for y, fs in zip(read_words(0x90 + 8 * filter, 8), get_fs())]
	
	return raw
	# return [raw - offset for raw, offset in zip(raw, get_offsets())]
	
def get_raw(offset=False, scaled=False):
	raw = [c_short(x).value for x in read_word_list(range(5, 29, 4))]
	if offset:
		raw = [r + of for r, of in zip(raw, get_offsets())]
	if scaled:
		raw = [r / 2**14 * s for r, s in zip(raw, get_fs())]
	return raw
	
def get_counts():
	return read_words(0xe8, 6)

#  shunts 		0x60, 6
#  def fs 		0x68, 6
#  load env # 	0x6f
#  min fs		0x70, 6
#  xForm#		0x77
#  max fs		0x78, 6
#  fs			0x80, 8
##  ofs			0x88, 6
#  ofs#			0x8e
#  vect axes	0x8f

#  f0			0x90, 8
#  f1			0x98, 8
#  f2			0xa0, 8
#  f3			0xa8, 8
#  f4			0xb0, 8
#  f5			0xb8, 8
#  f6			0xc0, 8

#  rate			0xc8, 8
#  min			0xd0, 8
#  max			0xd8, 8

jr3.ReadWord(fh, 0, 0xf8)
 
format(jr3.ReadWord(fh, 0, 0x98), '016b')
jr3.ReadWord(fh, 0, 0x40).to_bytes(2, 'big')

[c_short(y).value/z for y, z in zip(read_words(0xc0, 8), [50, 50, 100, 40, 40, 40]) ]